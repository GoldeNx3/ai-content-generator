# Rola pliku: Pobiera HTML i wydobywa treść artykułu przez trafilatura lub BeautifulSoup; usuwa elementy
# nawigacji i inne dodatki strony.

import asyncio
import ipaddress
import logging
import re
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura
from bs4 import BeautifulSoup, Tag

from app.services.http import USER_AGENT
from app.services.research.public_http import PublicHTTPTransport
from app.services.research.source_markdown import protect_examples, restore_examples

logger = logging.getLogger(__name__)

MIN_CONTENT_CHARS = 200
_ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
_BOILERPLATE_TAGS = (
    "script", "style", "noscript", "template", "svg", "canvas", "iframe", "form", "button",
    "nav", "header", "footer", "aside", "menu", "dialog", "figure",
)
_BOILERPLATE_PATTERN = re.compile(
    r"(^|[\s_-])(nav|navbar|menu|footer|header|sidebar|side-bar|cookie|consent|gdpr|banner|"
    r"advert|ads?|ad-slot|sponsor|promo|newsletter|subscribe|social|share|sharing|comments?|"
    r"related|recommend|breadcrumbs?|popup|modal)([\s_-]|$)",
    re.IGNORECASE,
)
_TEXT_TAGS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote", "pre", "td")
_BLANK_LINES = re.compile(r"\n{3,}")
# Short trailing lines that start "more content" sections (related posts, tags, author box...).
_TAIL_MARKERS = re.compile(
    r"^(related( content| posts| articles| stories| reading)?|read more|more from .{0,30}|"
    r"you (may|might) also like|recommended( for you)?|tags:?|written by|share( this)?( post| article)?:?|"
    r"comments?|leave a (reply|comment)|subscribe.{0,30}|sign up.{0,30}|"
    r"podobne artykuły|zobacz (też|także)|czytaj (też|także|więcej)|komentarze)$",
    re.IGNORECASE,
)


class ExtractionError(Exception):
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


# dataclass generuje m.in. konstruktor z zadeklarowanych pól; frozen blokuje przypisania do pól, slots
# ogranicza atrybuty.
@dataclass(slots=True)
class ExtractedDocument:
    url: str
    title: str | None
    author: str | None
    published_at: datetime | None
    content: str
    publisher: str | None = None
    http_status: int | None = None
    raw_html: str | None = None
    method: str = "trafilatura"


class ContentExtractor:
    """Downloads a page and extracts the main article text (trafilatura, BeautifulSoup fallback)."""

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 20.0,
        max_bytes: int = 5_000_000,
        resolve_dns: bool = True,
    ) -> None:
        self._client = client
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._resolve_dns = resolve_dns

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def extract(self, url: str) -> ExtractedDocument:
        started = time.perf_counter()
        html, final_url, status = await self._download(url)
        document = self.extract_from_html(html, final_url)
        document.http_status = status
        logger.info(
            "Extracted url=%s status=%s method=%s chars=%d duration=%.2fs",
            url, status, document.method, len(document.content), time.perf_counter() - started,
        )
        return document

    async def _download(self, url: str) -> tuple[str, str, int]:
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"}
        started = time.perf_counter()
        client = self._client or httpx.AsyncClient(transport=PublicHTTPTransport(), trust_env=False)
        try:
            for _ in range(6):
                await self._validate_destination(url)
                async with client.stream("GET", url, headers=headers, timeout=self._timeout, follow_redirects=False) as response:
                    logger.info(
                        "Fetched url=%s status=%d duration=%.2fs",
                        url, response.status_code, time.perf_counter() - started,
                    )
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise ExtractionError("Redirect without location", http_status=response.status_code)
                        try:
                            url = urljoin(str(response.url), location)
                        except ValueError as exc:
                            raise ExtractionError("Invalid redirect URL") from exc
                        continue
                    if response.status_code >= 400:
                        raise ExtractionError(f"HTTP {response.status_code}", http_status=response.status_code)
                    content_type = response.headers.get("content-type", "text/html").lower()
                    if not content_type.startswith(_ALLOWED_CONTENT_TYPES):
                        raise ExtractionError(
                            f"Unsupported content type: {content_type.split(';')[0]}",
                            http_status=response.status_code,
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_bytes:
                            raise ExtractionError("Page too large", http_status=response.status_code)
                    encoding = response.encoding or "utf-8"
                    return body.decode(encoding, errors="replace"), str(response.url), response.status_code
            raise ExtractionError("Too many redirects")
        except httpx.TimeoutException as exc:
            raise ExtractionError("Timeout") from exc
        except httpx.HTTPError as exc:
            raise ExtractionError(f"Request failed: {exc.__class__.__name__}") from exc
        finally:
            if self._client is None:
                await client.aclose()

    async def _validate_destination(self, url: str) -> None:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise ExtractionError("Invalid source URL") from exc
        if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
            raise ExtractionError("Source must have a public HTTP(S) URL")
        if host.lower().rstrip('.').endswith(("localhost", ".local", ".internal")):
            raise ExtractionError("Source must have a public address")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            if not literal.is_global:
                raise ExtractionError("Source must have a public address")
            return
        if self._resolve_dns:
            try:
                addresses = await asyncio.wait_for(
                    asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
                    timeout=self._timeout,
                )
            except (OSError, TimeoutError) as exc:
                raise ExtractionError("Source DNS resolution failed") from exc
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ExtractionError("Source must resolve to public addresses")

    # Najpierw dedykowany ekstraktor artykułu, potem fallback HTML; brak użytecznej treści daje błąd
    # ekstrakcji.
    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def extract_from_html(html: str, url: str) -> ExtractedDocument:
        if not html or not html.strip():
            raise ExtractionError("Empty page")

        metadata = _metadata(html, url)
        prepared_html, examples = protect_examples(html)
        content = trafilatura.extract(
            prepared_html,
            url=url,
            output_format="markdown",
            include_formatting=True,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            favor_precision=True,
            deduplicate=True,
        )
        method = "trafilatura"
        if not content or len(content.strip()) < MIN_CONTENT_CHARS:
            content = _extract_with_bs4(prepared_html)
            method = "beautifulsoup"
        content = _strip_trailing_boilerplate(_BLANK_LINES.sub("\n\n", (content or "").strip()))
        content = restore_examples(content, examples)
        if len(content) < MIN_CONTENT_CHARS:
            raise ExtractionError("No meaningful article content found")

        return ExtractedDocument(
            url=url,
            title=metadata.get("title"),
            author=metadata.get("author"),
            published_at=metadata.get("published_at"),
            publisher=metadata.get("publisher"),
            content=content,
            raw_html=html,
            method=method,
        )


def _metadata(html: str, url: str) -> dict:
    try:
        meta = trafilatura.extract_metadata(html, default_url=url)
    except Exception:  # metadata is best effort
        logger.debug("Metadata extraction failed for %s", url, exc_info=True)
        meta = None
    if meta is None:
        return {}
    return {
        "title": (meta.title or None) and meta.title[:1000],
        "author": meta.author or None,
        "publisher": meta.sitename or None,
        "published_at": _parse_date(meta.date),
    }


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _strip_trailing_boilerplate(text: str) -> str:
    """Cuts the text at the first tail marker located in the second half of the article."""
    lines = text.split("\n")
    position = 0
    for index, line in enumerate(lines):
        if position > len(text) * 0.5 and _TAIL_MARKERS.match(line.strip()):
            return "\n".join(lines[:index]).rstrip()
        position += len(line) + 1
    return text


def _extract_with_bs4(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_BOILERPLATE_TAGS):
        tag.decompose()
    for tag in soup.find_all(_is_boilerplate):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    blocks: list[str] = []
    for element in root.find_all(_TEXT_TAGS):
        if element.find_parent(_TEXT_TAGS):  # avoid duplicates for nested blocks
            continue
        text = " ".join(element.get_text(" ", strip=True).split())
        if len(text) >= 3:
            blocks.append(text)
    if not blocks:
        blocks = [line.strip() for line in root.get_text("\n").splitlines() if len(line.strip()) > 40]
    return "\n\n".join(blocks)


def _is_boilerplate(tag: Tag) -> bool:
    if tag.name in ("html", "body", "article", "main") or tag.attrs is None:
        return False
    marker = " ".join([tag.get("id") or "", *(tag.get("class") or []), tag.get("role") or ""])
    if tag.get("role") in ("navigation", "banner", "contentinfo", "complementary"):
        return True
    return bool(marker.strip()) and bool(_BOILERPLATE_PATTERN.search(marker))
