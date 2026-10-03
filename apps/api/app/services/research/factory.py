# Rola pliku: Składa serwis researchu i zadanie w tle z własną sesją bazy; placeholder obsługuje brak
# konfiguracji LLM.

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.services.llm.base import (
    CandidateInput,
    LLMNotConfiguredError,
    QueriesResult,
    ResearchDocument,
    ResearchLLMProvider,
    ResearchResult,
)
from app.services.llm.cost import LLMCostCalculator
from app.services.llm.factory import get_research_llm_provider
from app.services.research.content_extractor import ContentExtractor
from app.services.research.research_service import ResearchService
from app.services.research.search import SearchProvider, get_search_provider

ResearchRunner = Callable[[int, bool], Awaitable[None]]


class UnconfiguredResearchLLM:
    """Used when no API key is set: sources are still fetched and saved, analysis fails clearly."""

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, reason: str) -> None:
        self.reason = reason

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult:
        raise LLMNotConfiguredError(self.reason)

    async def research(self, candidate: CandidateInput, documents: list[ResearchDocument]) -> ResearchResult:
        raise LLMNotConfiguredError(self.reason)


def research_llm_or_placeholder() -> ResearchLLMProvider:
    try:
        return get_research_llm_provider()
    except LLMNotConfiguredError as exc:
        return UnconfiguredResearchLLM(str(exc))


def build_content_extractor(settings: Settings) -> ContentExtractor:
    return ContentExtractor(timeout=settings.page_fetch_timeout_seconds, max_bytes=settings.page_max_bytes)


def build_research_service(
    session: AsyncSession,
    settings: Settings,
    extractor: ContentExtractor,
    search: SearchProvider | None = None,
    llm: ResearchLLMProvider | None = None,
) -> ResearchService:
    return ResearchService(
        session=session,
        extractor=extractor,
        search=search or get_search_provider(settings),
        llm=llm or research_llm_or_placeholder(),
        cost_calculator=LLMCostCalculator(settings.llm_pricing),
        settings=settings,
    )


# Zwracamy funkcję run, która pamięta zależności z otoczenia (closure), a nie wynik jej wykonania.
def make_research_runner(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    extractor: ContentExtractor,
    search: SearchProvider,
    llm: ResearchLLMProvider,
) -> ResearchRunner:
    """Background job body: runs the pipeline in its own DB session (request session is closed by then)."""

    async def run(research_id: int, discover: bool) -> None:
        async with session_factory() as session:
            service = build_research_service(session, settings, extractor, search, llm)
            await service.run(research_id, discover=discover)

    return run
