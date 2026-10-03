# Rola pliku: Pobiera RSS/Atom przez HTTP i normalizuje różne formaty feedów do wspólnego obiektu FeedEntry.

import calendar
import html
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from app.models import Source
from app.services.http import USER_AGENT

logger = logging.getLogger(__name__)

SUMMARY_MAX_LENGTH = 2000
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class FeedFetchError(Exception):
    """Raised when a feed cannot be downloaded or parsed."""


# dataclass generuje m.in. konstruktor z zadeklarowanych pól; frozen blokuje przypisania do pól, slots
# ogranicza atrybuty.
@dataclass(frozen=True, slots=True)
class FeedEntry:
    title: str
    url: str
    summary: str | None
    published_at: datetime | None


class RssFetcher:
    """Downloads an RSS 2.0 / Atom feed and returns unified entries."""

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 15.0) -> None:
        self._client = client
        self._timeout = timeout

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def fetch(self, source: Source) -> list[FeedEntry]:
        content = await self._download(source.url)
        return self.parse(content, source.url)

    async def _download(self, url: str) -> bytes:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"}
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers, timeout=self._timeout, follow_redirects=True)
            else:
                async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FeedFetchError(f"Timeout while fetching {url}") from exc
        except httpx.HTTPStatusError as exc:
            raise FeedFetchError(f"HTTP {exc.response.status_code} for {url}") from exc
        except httpx.HTTPError as exc:
            raise FeedFetchError(f"Request failed for {url}: {exc}") from exc
        return response.content

    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def parse(content: bytes, feed_url: str = "") -> list[FeedEntry]:
        parsed = feedparser.parse(content)
        if parsed.bozo and not parsed.entries:
            raise FeedFetchError(f"Invalid feed {feed_url}: {parsed.get('bozo_exception')}")
        if not parsed.get("version") and not parsed.entries:
            raise FeedFetchError(f"Not a RSS/Atom feed: {feed_url}")

        entries: list[FeedEntry] = []
        for raw in parsed.entries:
            entry = _to_entry(raw)
            if entry is None:
                logger.debug("Skipping feed entry without title/link in %s", feed_url)
                continue
            entries.append(entry)
        return entries


def _to_entry(raw: Any) -> FeedEntry | None:
    url = (raw.get("link") or "").strip()
    title = _clean_text(raw.get("title"))
    if not url or not title:
        return None
    summary = _clean_text(raw.get("summary") or raw.get("description"))
    if summary and len(summary) > SUMMARY_MAX_LENGTH:
        summary = summary[: SUMMARY_MAX_LENGTH - 1].rstrip() + "…"
    return FeedEntry(title=title[:1000], url=url, summary=summary or None, published_at=_published_at(raw))


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", value))).strip()


def _published_at(raw: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed_time = raw.get(key)
        if parsed_time:
            return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=UTC)
    return None
