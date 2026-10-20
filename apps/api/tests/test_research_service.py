# Rola pliku: Testy modułu research_service: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    Candidate,
    FactImportance,
    FetchStatus,
    ResearchFact,
    ResearchSourceOrigin,
    ResearchSourceType,
    ResearchStatus,
    Source,
)
from app.services.llm.cost import LLMCostCalculator
from app.services.research.research_service import (
    DuplicateSourceError,
    ResearchInProgressError,
    ResearchService,
)
from app.services.research.search import SearchResult
from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for, html_response

ORIGINAL = "https://openai.com/index/gpt-6-api"
DOCS = "https://platform.openai.com/docs/models/gpt-6"
NEWS = "https://techcrunch.com/2026/10/02/gpt-6-api"
BROKEN = "https://broken.example.com/article"

PAGES = {
    ORIGINAL: html_response("Introducing GPT-6 API"),
    DOCS: html_response("GPT-6 model documentation"),
    NEWS: html_response("OpenAI launches GPT-6 API"),
}


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
# Fixture przygotowuje zależność testu; pytest przekazuje ją według nazwy argumentu funkcji testowej.
@pytest.fixture
async def candidate(session: AsyncSession) -> Candidate:
    source = Source(workspace_id=1, name="OpenAI", url="https://openai.com/news/rss.xml")
    session.add(source)
    # flush wysyła zmiany do bazy (np. nadaje ID), ale nie zatwierdza jeszcze transakcji jak commit.
    await session.flush()
    item = Candidate(workspace_id=1, source_id=source.id, external_url=ORIGINAL, title="OpenAI releases GPT-6 API")
    session.add(item)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    return item


def make_service(
    session: AsyncSession,
    search: FakeSearch | None = None,
    llm: FakeResearchLLM | None = None,
    pages: dict | None = None,
    max_extra_sources: int | None = None,
) -> ResearchService:
    settings = get_settings()
    if max_extra_sources is not None:
        settings = settings.model_copy(update={"research_max_extra_sources": max_extra_sources})
    return ResearchService(
        session=session,
        extractor=extractor_for(pages if pages is not None else PAGES),
        search=search or FakeSearch(),
        llm=llm or FakeResearchLLM(),
        cost_calculator=LLMCostCalculator({"gpt-4.1-mini": {"input": 0.40, "output": 1.60}}),
        settings=settings,
    )


def results(*urls: str) -> list[SearchResult]:
    return [SearchResult(title=f"Result {i}", url=url, snippet="") for i, url in enumerate(urls)]


async def test_full_research(session: AsyncSession, candidate: Candidate) -> None:
    search = FakeSearch(results(NEWS, DOCS))
    llm = FakeResearchLLM()

    research = await make_service(session, search, llm).research_candidate(candidate.id)

    assert research.status == ResearchStatus.COMPLETED
    assert research.summary == "OpenAI udostępniło API GPT-6."
    assert research.search_queries == ["gpt-6 api official", "gpt-6 pricing"]
    assert search.queries == research.search_queries
    assert research.started_at is not None and research.completed_at is not None

    by_url = {source.url: source for source in research.sources}
    assert set(by_url) == {ORIGINAL, DOCS, NEWS}
    assert by_url[ORIGINAL].origin == ResearchSourceOrigin.ORIGINAL
    assert by_url[ORIGINAL].source_type == ResearchSourceType.OFFICIAL
    assert by_url[ORIGINAL].source_score == 100
    assert by_url[DOCS].source_type == ResearchSourceType.DOCUMENTATION
    assert by_url[NEWS].source_type == ResearchSourceType.NEWS
    assert by_url[NEWS].source_score == 80
    assert all(s.fetch_status == FetchStatus.SUCCESS for s in research.sources)
    assert "GPT-6 API to all developers" in (by_url[ORIGINAL].extracted_content or "")

    # Documents go to the LLM original-first, then by credibility.
    assert [doc.url for doc in llm.documents] == [ORIGINAL, DOCS, NEWS]

    # Tokens: queries (100/20) + research (1M/100k); cost from configured pricing.
    assert research.llm_input_tokens == 1_000_100
    assert research.llm_output_tokens == 100_020
    assert research.llm_model == "gpt-4.1-mini"
    assert research.estimated_cost_usd == Decimal("0.400040") + Decimal("0.160032")


async def test_facts_are_linked_to_existing_sources_only(session: AsyncSession, candidate: Candidate) -> None:
    research = await make_service(session, FakeSearch(results(NEWS))).research_candidate(candidate.id)

    facts = {fact.claim: fact for fact in research.facts}
    assert set(facts) == {"API GPT-6 jest dostępne.", "Okno kontekstu to 1M tokenów."}
    assert {s.url for s in facts["API GPT-6 jest dostępne."].sources} == {ORIGINAL, NEWS}
    assert [s.url for s in facts["Okno kontekstu to 1M tokenów."].sources] == [ORIGINAL]
    assert facts["API GPT-6 jest dostępne."].importance == FactImportance.CRITICAL
    assert facts["API GPT-6 jest dostępne."].confidence == 95

    # The fact citing an invented URL is not stored as a fact, but kept visible as an uncertainty.
    assert any(u["claim"] == "Wymyślony fakt." for u in research.uncertainties)
    assert {"claim": "Data premiery w UE", "reason": "Brak informacji w źródłach"} in research.uncertainties
    # Invented URL removed from the conflict as well.
    assert research.conflicts == [{"topic": "Cena", "sources": [{"url": ORIGINAL, "claim": "2 USD"}]}]

    # Relations persisted in the association table.
    fact_count = await session.scalar(select(func.count(ResearchFact.id)))
    assert fact_count == 2


async def test_one_broken_source_does_not_fail_research(session: AsyncSession, candidate: Candidate) -> None:
    research = await make_service(session, FakeSearch(results(BROKEN, NEWS))).research_candidate(candidate.id)

    assert research.status == ResearchStatus.COMPLETED
    broken = next(s for s in research.sources if s.url == BROKEN)
    assert broken.fetch_status == FetchStatus.FAILED
    assert broken.http_status == 404
    assert broken.error == "HTTP 404"


async def test_duplicate_urls_are_skipped(session: AsyncSession, candidate: Candidate) -> None:
    search = FakeSearch(
        results(NEWS, NEWS + "/", NEWS + "?utm_source=x", ORIGINAL, "https://www.openai.com/index/gpt-6-api#top")
    )

    research = await make_service(session, search).research_candidate(candidate.id)

    assert sorted(s.url for s in research.sources) == sorted([ORIGINAL, NEWS])


async def test_extra_sources_are_limited_and_prefer_primary(session: AsyncSession, candidate: Candidate) -> None:
    unknown = [f"https://blog{i}.example.net/post" for i in range(4)]
    search = FakeSearch(results(*unknown, DOCS))
    pages = {**PAGES, **{url: html_response("Blog") for url in unknown}}

    research = await make_service(session, search, pages=pages, max_extra_sources=3).research_candidate(candidate.id)

    extra = [s for s in research.sources if s.origin == ResearchSourceOrigin.SEARCH]
    assert len(extra) == 3
    assert DOCS in {s.url for s in extra}  # highest score wins a slot despite being listed last


async def test_llm_failure_marks_failed_and_keeps_sources(session: AsyncSession, candidate: Candidate) -> None:
    research = await make_service(
        session, FakeSearch(results(NEWS)), FakeResearchLLM(fail_research=True)
    ).research_candidate(candidate.id)

    assert research.status == ResearchStatus.FAILED
    assert "OpenAI request failed" in (research.error or "")
    assert {s.url for s in research.sources} == {ORIGINAL, NEWS}
    assert research.facts == []
    assert research.llm_input_tokens == 100  # query generation usage is still recorded


async def test_search_failure_still_completes(session: AsyncSession, candidate: Candidate) -> None:
    research = await make_service(session, FakeSearch(fail=True)).research_candidate(candidate.id)

    assert research.status == ResearchStatus.COMPLETED
    assert [s.url for s in research.sources] == [ORIGINAL]


async def test_no_fetchable_source_fails(session: AsyncSession, candidate: Candidate) -> None:
    research = await make_service(session, pages={}).research_candidate(candidate.id)

    assert research.status == ResearchStatus.FAILED
    assert "No source content" in (research.error or "")
    assert research.sources[0].fetch_status == FetchStatus.FAILED


async def test_manual_source_and_reanalysis(session: AsyncSession, candidate: Candidate) -> None:
    service = make_service(session)
    await service.research_candidate(candidate.id)

    manual = await service.add_manual_source(candidate.id, NEWS)
    assert manual.origin == ResearchSourceOrigin.MANUAL
    assert manual.fetch_status == FetchStatus.SUCCESS
    with pytest.raises(DuplicateSourceError):
        await service.add_manual_source(candidate.id, NEWS + "/")

    research = await service.start(candidate.id, discover=False)
    research = await service.run(research.id, discover=False)

    assert research.status == ResearchStatus.COMPLETED
    assert {s.url for s in research.sources} == {ORIGINAL, NEWS}

    # A fresh research keeps manual sources but replaces the rest.
    research = await service.research_candidate(candidate.id)
    assert NEWS in {s.url for s in research.sources if s.origin == ResearchSourceOrigin.MANUAL}


async def test_cannot_start_twice(session: AsyncSession, candidate: Candidate) -> None:
    service = make_service(session)
    await service.start(candidate.id, discover=True)

    with pytest.raises(ResearchInProgressError):
        await service.start(candidate.id, discover=True)


async def test_failed_original_page(session: AsyncSession, candidate: Candidate) -> None:
    pages = {ORIGINAL: httpx.Response(403), NEWS: html_response("News")}

    research = await make_service(session, FakeSearch(results(NEWS)), pages=pages).research_candidate(candidate.id)

    assert research.status == ResearchStatus.COMPLETED
    original = next(s for s in research.sources if s.origin == ResearchSourceOrigin.ORIGINAL)
    assert original.http_status == 403
