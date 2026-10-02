import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]: ...


class SearchError(Exception):
    pass


class ManualSearchProvider:
    """No external search engine: returns only URLs supplied up front (may be none).

    Additional sources can also be added per research via
    POST /api/candidates/{id}/research/sources.
    """

    def __init__(self, urls: list[str] | None = None) -> None:
        self._results = [SearchResult(title="", url=url, snippet="") for url in urls or []]

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        return self._results[:limit]


class TavilySearchProvider:
    """https://docs.tavily.com - enabled with SEARCH_PROVIDER=tavily and TAVILY_API_KEY."""

    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._client = client
        self._timeout = timeout

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        payload = {"query": query, "max_results": limit, "search_depth": "basic"}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            if self._client is not None:
                response = await self._client.post(self.ENDPOINT, json=payload, headers=headers, timeout=self._timeout)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self.ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SearchError(f"Tavily HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise SearchError(f"Tavily request failed: {exc.__class__.__name__}") from exc

        results = response.json().get("results", [])
        return [
            SearchResult(title=item.get("title") or "", url=item["url"], snippet=item.get("content") or "")
            for item in results
            if item.get("url")
        ][:limit]


def get_search_provider(settings: Settings) -> SearchProvider:
    if settings.search_provider == "tavily":
        if settings.tavily_api_key:
            return TavilySearchProvider(settings.tavily_api_key)
        logger.warning("SEARCH_PROVIDER=tavily but TAVILY_API_KEY is empty - using ManualSearchProvider")
    return ManualSearchProvider()
