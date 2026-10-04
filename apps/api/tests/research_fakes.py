# Rola pliku: Kontrolowane strony HTML, wyszukiwarka i dostawca LLM do testów researchu bez zewnętrznych
# usług.

"""Test doubles for the research engine: HTTP pages, search provider and LLM (no network, no cost)."""

from collections.abc import Callable

import httpx

from app.models import FactBasis, FactImportance
from app.schemas.research import (
    LLMConflict,
    LLMConflictSource,
    LLMFact,
    LLMUncertainty,
    ResearchOutput,
    SearchQueries,
)
from app.services.llm.base import (
    CandidateInput,
    LLMError,
    LLMUsage,
    QueriesResult,
    ResearchDocument,
    ResearchResult,
)
from app.services.research.content_extractor import ContentExtractor
from app.services.research.search import SearchResult

PARAGRAPH = (
    "OpenAI today released the GPT-6 API to all developers. The model supports a context window "
    "of one million tokens and is priced at two dollars per million input tokens. "
)


def article_html(title: str, body: str = PARAGRAPH * 4) -> str:
    return f"""<!doctype html><html><head><title>{title}</title>
<meta property="og:site_name" content="Example Site"></head>
<body>
  <nav class="main-nav"><a href="/">Home</a> <a href="/pricing">Pricing</a> <a href="/careers">Careers menu link</a></nav>
  <div id="cookie-banner">We use cookies to improve your experience. Accept all cookies</div>
  <main><article>
    <h1>{title}</h1>
    <p>{body}</p>
    <p>{body}</p>
  </article></main>
  <aside class="sidebar">Trending now: unrelated sidebar story</aside>
  <footer class="site-footer">Copyright 2026 Example footer text. Privacy policy.</footer>
</body></html>"""


# MockTransport przechwytuje HTTP i zwraca odpowiedź z lokalnej funkcji; to wywołanie nie trafia do Internetu.
def page_transport(pages: dict[str, httpx.Response | Callable[[httpx.Request], httpx.Response]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        page = pages.get(str(request.url))
        if page is None:
            return httpx.Response(404, text="not found")
        return page(request) if callable(page) else page

    return httpx.MockTransport(handler)


def html_response(title: str, body: str = PARAGRAPH * 4) -> httpx.Response:
    return httpx.Response(200, text=article_html(title, body), headers={"content-type": "text/html; charset=utf-8"})


def extractor_for(pages: dict[str, httpx.Response | Callable[[httpx.Request], httpx.Response]]) -> ContentExtractor:
    return ContentExtractor(client=httpx.AsyncClient(transport=page_transport(pages)), timeout=1, resolve_dns=False)


class FakeSearch:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, results: list[SearchResult] | None = None, fail: bool = False) -> None:
        self.results = results or []
        self.fail = fail
        self.queries: list[str] = []

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("search engine down")
        return self.results[:limit]


def default_output(documents: list[ResearchDocument]) -> ResearchOutput:
    first = documents[0].url
    all_urls = [doc.url for doc in documents]
    return ResearchOutput(
        summary="OpenAI udostępniło API GPT-6.",
        why_it_matters="Nowy model dla deweloperów.",
        suggested_angle="Co zmienia GPT-6 API dla polskich firm.",
        facts=[
            LLMFact(claim="API GPT-6 jest dostępne.", importance=FactImportance.CRITICAL, basis=FactBasis.VERIFIABLE, confidence=95, source_urls=all_urls),
            LLMFact(claim="Okno kontekstu to 1M tokenów.", importance=FactImportance.IMPORTANT, basis=FactBasis.VERIFIABLE, confidence=90, source_urls=[first]),
            LLMFact(
                claim="Wymyślony fakt.",
                importance=FactImportance.SUPPORTING, basis=FactBasis.VERIFIABLE,
                confidence=40,
                source_urls=["https://invented.example/made-up"],
            ),
        ],
        uncertainties=[LLMUncertainty(claim="Data premiery w UE", reason="Brak informacji w źródłach")],
        conflicts=[
            LLMConflict(
                topic="Cena",
                sources=[
                    LLMConflictSource(url=first, claim="2 USD"),
                    LLMConflictSource(url="https://invented.example/price", claim="3 USD"),
                ],
            )
        ],
        source_types=[],
    )


class FakeResearchLLM:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(
        self,
        queries: list[str] | None = None,
        output: Callable[[list[ResearchDocument]], ResearchOutput] = default_output,
        fail_research: bool = False,
    ) -> None:
        self.queries = queries if queries is not None else ["gpt-6 api official", "gpt-6 pricing"]
        self.output = output
        self.fail_research = fail_research
        self.documents: list[ResearchDocument] = []

    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult:
        return QueriesResult(SearchQueries(queries=self.queries), LLMUsage("gpt-4.1-mini", 100, 20))

    async def research(self, candidate: CandidateInput, documents: list[ResearchDocument]) -> ResearchResult:
        self.documents = documents
        if self.fail_research:
            raise LLMError("OpenAI request failed: 500")
        return ResearchResult(self.output(documents), LLMUsage("gpt-4.1-mini", 1_000_000, 100_000))
