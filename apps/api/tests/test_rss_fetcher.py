# Rola pliku: Testy modułu rss_fetcher: scenariusze poprawnego działania i błędów. Funkcje test_* odkrywa
# i uruchamia pytest.

from datetime import UTC, datetime

import httpx
import pytest

from app.models import Source
from app.services.rss_fetcher import FeedFetchError, RssFetcher
from tests.feeds import ATOM_FEED, BROKEN_FEED, RSS_FEED

SOURCE = Source(workspace_id=1, name="Example", url="https://example.com/feed.xml")


# MockTransport przechwytuje HTTP i zwraca odpowiedź z lokalnej funkcji; to wywołanie nie trafia do Internetu.
def fetcher_for(handler: httpx.MockTransport) -> RssFetcher:
    return RssFetcher(client=httpx.AsyncClient(transport=handler), timeout=1)


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_parses_rss_feed() -> None:
    fetcher = fetcher_for(httpx.MockTransport(lambda request: httpx.Response(200, content=RSS_FEED)))

    entries = await fetcher.fetch(SOURCE)

    assert len(entries) == 3
    first = entries[0]
    assert first.title == "OpenAI releases a new model"
    assert first.url == "https://example.com/posts/1"
    assert first.summary == "Big release today."
    assert first.published_at == datetime(2025, 10, 1, 10, 0, tzinfo=UTC)


async def test_handles_missing_date_and_summary() -> None:
    fetcher = fetcher_for(httpx.MockTransport(lambda request: httpx.Response(200, content=RSS_FEED)))

    entry = (await fetcher.fetch(SOURCE))[1]

    assert entry.summary is None
    assert entry.published_at is None


async def test_parses_atom_feed() -> None:
    fetcher = fetcher_for(httpx.MockTransport(lambda request: httpx.Response(200, content=ATOM_FEED)))

    entries = await fetcher.fetch(SOURCE)

    assert len(entries) == 1
    assert entries[0].url == "https://example.com/atom/1"
    assert entries[0].summary == "Short atom summary"
    assert entries[0].published_at == datetime(2025, 10, 1, 12, 0, tzinfo=UTC)


async def test_broken_feed_raises_fetch_error() -> None:
    fetcher = fetcher_for(httpx.MockTransport(lambda request: httpx.Response(200, content=BROKEN_FEED)))

    with pytest.raises(FeedFetchError):
        await fetcher.fetch(SOURCE)


async def test_timeout_raises_fetch_error() -> None:
    def raise_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    fetcher = fetcher_for(httpx.MockTransport(raise_timeout))

    with pytest.raises(FeedFetchError, match="Timeout"):
        await fetcher.fetch(SOURCE)


async def test_http_error_raises_fetch_error() -> None:
    fetcher = fetcher_for(httpx.MockTransport(lambda request: httpx.Response(500)))

    with pytest.raises(FeedFetchError, match="HTTP 500"):
        await fetcher.fetch(SOURCE)
