# Rola pliku: Koordynuje research: pobranie źródła, wyszukiwanie dodatkowych materiałów, analiza LLM i
# zapis faktów powiązanych ze źródłami.

import asyncio
import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import Settings
from app.models import (
    Candidate,
    FetchStatus,
    Research,
    ResearchFact,
    ResearchSource,
    ResearchSourceOrigin,
    ResearchStatus,
)
from app.services.llm.base import CandidateInput, LLMUsage, ResearchDocument, ResearchLLMProvider
from app.services.llm.cost import LLMCostCalculator
from app.services.research.content_budget import fit_documents
from app.services.research.content_extractor import ContentExtractor, ExtractedDocument, ExtractionError
from app.services.research.fact_validation import validate_research_output
from app.services.research.search import SearchProvider, SearchResult
from app.services.research.source_scoring import (
    SourceAssessment,
    apply_llm_suggestion,
    assess_source,
    official_domains_for,
)
from app.services.research.urls import normalize_url

logger = logging.getLogger(__name__)

RESULTS_PER_QUERY = 5
MAX_QUERIES = 3


class ResearchError(Exception):
    """Base error for research operations (mapped to HTTP errors by the API layer)."""


class CandidateNotFoundError(ResearchError):
    pass


class ResearchNotFoundError(ResearchError):
    pass


class ResearchInProgressError(ResearchError):
    pass


class DuplicateSourceError(ResearchError):
    pass


class ResearchService:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(
        self,
        session: AsyncSession,
        extractor: ContentExtractor,
        search: SearchProvider,
        llm: ResearchLLMProvider,
        cost_calculator: LLMCostCalculator,
        settings: Settings,
    ) -> None:
        self.session = session
        self.extractor = extractor
        self.search = search
        self.llm = llm
        self.costs = cost_calculator
        self.settings = settings

    # ---------- public API ----------

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def research_candidate(self, candidate_id: int) -> Research:
        """Full pipeline: fetch original, discover sources, analyse with the LLM."""
        research = await self.start(candidate_id, discover=True)
        return await self.run(research.id, discover=True)

    async def get_for_candidate(self, candidate_id: int) -> Research | None:
        return await self.session.scalar(select(Research).where(Research.candidate_id == candidate_id))

    # Zapisuje status running przed uruchomieniem analizy; discover decyduje, czy zachować dotychczasowe
    # źródła.
    async def start(self, candidate_id: int, discover: bool) -> Research:
        """Creates or resets the candidate's research with status running. Does not execute it.

        discover=True: fresh research - drops previous facts and all non-manual sources.
        discover=False: re-analysis - keeps sources, only facts/report are replaced.
        """
        await self._get_candidate(candidate_id)
        research = await self.get_for_candidate(candidate_id)
        if research is None:
            if not discover:
                raise ResearchNotFoundError("Research not found - start a research first")
            research = Research(candidate_id=candidate_id, search_queries=[], uncertainties=[], conflicts=[])
            self.session.add(research)
        elif research.status == ResearchStatus.RUNNING:
            raise ResearchInProgressError("Research is already running")

        if discover:
            research.sources = [s for s in research.sources if s.origin == ResearchSourceOrigin.MANUAL]
            research.search_queries = []
        research.facts.clear()
        research.status = ResearchStatus.RUNNING
        research.summary = research.why_it_matters = research.suggested_angle = None
        research.uncertainties = []
        research.conflicts = []
        research.error = None
        research.started_at = datetime.now(UTC)
        research.completed_at = None
        research.llm_model = None
        research.llm_input_tokens = research.llm_output_tokens = 0
        research.estimated_cost_usd = None
        # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
        # trwałego zapisu.
        await self.session.commit()
        # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
        await self.session.refresh(research)  # load server defaults + relationships for the response
        return research

    async def run(self, research_id: int, discover: bool) -> Research:
        """Executes the pipeline. Never raises for pipeline errors: the research ends as failed."""
        research = await self.session.get(Research, research_id)
        if research is None:
            raise ResearchNotFoundError(f"Research {research_id} not found")
        candidate = await self._get_candidate(research.candidate_id)
        if research.status != ResearchStatus.RUNNING:
            research.status = ResearchStatus.RUNNING
            research.started_at = datetime.now(UTC)
            await self.session.commit()
        started = time.perf_counter()
        logger.info("Research started candidate_id=%s research_id=%s discover=%s", candidate.id, research.id, discover)

        try:
            await self._pipeline(research, candidate, discover)
            research.status = ResearchStatus.COMPLETED
            logger.info(
                "Research completed candidate_id=%s research_id=%s facts=%d sources=%d duration=%.1fs cost=%s",
                candidate.id, research.id, len(research.facts), len(research.sources),
                time.perf_counter() - started, research.estimated_cost_usd,
            )
        except Exception as exc:
            logger.exception("Research failed candidate_id=%s research_id=%s", candidate.id, research.id)
            # rollback wycofuje niezakończoną transakcję po błędzie; wcześniejsze commity pozostają zapisane.
            await self.session.rollback()  # discard half-applied report; committed sources stay
            research = await self.session.get(Research, research_id, populate_existing=True)
            assert research is not None
            research.status = ResearchStatus.FAILED
            research.error = str(exc) or exc.__class__.__name__
        research.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(research)
        return research

    async def add_manual_source(self, candidate_id: int, url: str) -> ResearchSource:
        candidate = await self._get_candidate(candidate_id)
        research = await self.get_for_candidate(candidate_id)
        if research is None:
            research = Research(candidate_id=candidate_id, search_queries=[], uncertainties=[], conflicts=[])
            self.session.add(research)
            # flush wysyła zmiany do bazy (np. nadaje ID), ale nie zatwierdza jeszcze transakcji jak commit.
            await self.session.flush()
        elif research.status == ResearchStatus.RUNNING:
            raise ResearchInProgressError("Research is running - add sources after it finishes")
        if normalize_url(url) in {normalize_url(s.url) for s in research.sources}:
            raise DuplicateSourceError("This URL is already a source of this research")

        source = ResearchSource(url=url, origin=ResearchSourceOrigin.MANUAL)
        research.sources.append(source)
        await self._fetch_into(source, official_domains_for(candidate.external_url), candidate.id, research.id)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    # ---------- pipeline ----------

    async def _pipeline(self, research: Research, candidate: Candidate, discover: bool) -> None:
        official = official_domains_for(candidate.external_url)
        candidate_input = CandidateInput(
            title=candidate.title,
            summary=candidate.summary,
            source=candidate.source.name,
            published_at=candidate.original_published_at,
        )
        usages: list[LLMUsage] = []
        known_sources = list(research.sources)

        if not any(s.origin == ResearchSourceOrigin.ORIGINAL for s in research.sources):
            original = ResearchSource(url=candidate.external_url, origin=ResearchSourceOrigin.ORIGINAL)
            research.sources.append(original)
            await self._fetch_into(original, official, candidate.id, research.id)
            await self.session.commit()

        # Retry sources from earlier runs that could not be fetched (e.g. a manual URL that was down).
        for source in known_sources:
            if source.fetch_status != FetchStatus.SUCCESS:
                await self._fetch_into(source, official, candidate.id, research.id)
        await self.session.commit()

        if discover:
            await self._discover_sources(research, candidate, candidate_input, official, usages)

        # Re-score every source with the current heuristic (kept sources may come from older runs).
        for source in research.sources:
            assessment = assess_source(source.url, official)
            source.source_type, source.source_score = assessment.source_type, assessment.score
            source.publisher = clean_publisher(source.publisher)

        fetched = self._ordered_fetched_sources(research.sources)
        if not fetched:
            raise ResearchError("No source content could be fetched - add a source manually and retry")

        documents, used_sources = self._build_documents(fetched)
        llm_started = time.perf_counter()
        result = await self.llm.research(candidate_input, documents)
        usages.append(result.usage)
        self._record_usage(research, usages)
        logger.info(
            "Research LLM research_id=%s model=%s documents=%d prompt_chars=%d duration=%.1fs",
            research.id, result.usage.model, len(documents),
            sum(len(d.content) for d in documents), time.perf_counter() - llm_started,
        )

        validated = validate_research_output(result.output, used_sources, self.settings.research_max_facts)
        research.summary = result.output.summary
        research.why_it_matters = result.output.why_it_matters
        research.suggested_angle = result.output.suggested_angle
        research.uncertainties = validated.uncertainties
        research.conflicts = validated.conflicts
        for fact in validated.facts:
            research.facts.append(
                ResearchFact(
                    claim=fact.claim, importance=fact.importance, confidence=fact.confidence, sources=fact.sources
                )
            )
        for source in research.sources:
            suggestion = validated.suggested_types.get(source.id)
            if suggestion is not None:
                current = SourceAssessment(source.source_type, source.source_score, recognized=_recognized(source, official))
                refined = apply_llm_suggestion(current, suggestion)
                source.source_type, source.source_score = refined.source_type, refined.score

    async def _discover_sources(
        self,
        research: Research,
        candidate: Candidate,
        candidate_input: CandidateInput,
        official: set[str],
        usages: list[LLMUsage],
    ) -> None:
        try:
            queries_result = await self.llm.generate_search_queries(candidate_input)
        except Exception as exc:  # discovery is best effort - analysis can still use the original
            logger.warning("Query generation failed research_id=%s error=%s", research.id, exc)
            return
        usages.append(queries_result.usage)
        queries = [q.strip() for q in queries_result.queries.queries if q.strip()][:MAX_QUERIES]
        research.search_queries = queries
        self._record_usage(research, usages)
        await self.session.commit()

        results: list[SearchResult] = []
        for query in queries:
            try:
                found = await self.search.search(query, limit=RESULTS_PER_QUERY)
            except Exception as exc:
                logger.warning("Search failed research_id=%s query=%r error=%s", research.id, query, exc)
                continue
            logger.info("Search research_id=%s query=%r results=%d", research.id, query, len(found))
            results.extend(found)

        known = {normalize_url(s.url) for s in research.sources} | {normalize_url(candidate.external_url)}
        picked: list[tuple[SearchResult, SourceAssessment]] = []
        for item in results:
            key = normalize_url(item.url)
            if key in known or not item.url.startswith(("http://", "https://")):
                continue
            known.add(key)
            picked.append((item, assess_source(item.url, official)))
        # Prefer primary sources: highest heuristic score first (stable for equal scores).
        picked.sort(key=lambda pair: pair[1].score, reverse=True)
        picked = picked[: self.settings.research_max_extra_sources]

        new_sources = [
            ResearchSource(url=item.url, title=item.title[:1000] or None, origin=ResearchSourceOrigin.SEARCH)
            for item, _ in picked
        ]
        # gather wykonuje korutyny współbieżnie i zbiera wyniki w kolejności przekazanych argumentów.
        extractions = await asyncio.gather(*(self._safe_extract(source.url) for source in new_sources))
        for source, extraction in zip(new_sources, extractions, strict=True):
            research.sources.append(source)
            self._apply_extraction(source, extraction, official, candidate.id, research.id)
        await self.session.commit()

    # ---------- helpers ----------

    async def _get_candidate(self, candidate_id: int) -> Candidate:
        candidate = await self.session.get(
            Candidate, candidate_id, options=[joinedload(Candidate.source)], populate_existing=True
        )
        if candidate is None:
            raise CandidateNotFoundError("Candidate not found")
        return candidate

    # Błąd jednego URL-a zamieniamy na wynik ExtractionError, aby dało się zapisać nieudane źródło i
    # kontynuować.
    async def _safe_extract(self, url: str) -> ExtractedDocument | ExtractionError:
        try:
            return await self.extractor.extract(url)
        except ExtractionError as exc:
            return exc
        except Exception as exc:  # unexpected parser errors must not break the research
            logger.exception("Unexpected extraction error url=%s", url)
            return ExtractionError(f"Extraction failed: {exc.__class__.__name__}")

    async def _fetch_into(self, source: ResearchSource, official: set[str], candidate_id: int, research_id: int) -> None:
        self._apply_extraction(source, await self._safe_extract(source.url), official, candidate_id, research_id)

    def _apply_extraction(
        self,
        source: ResearchSource,
        extraction: ExtractedDocument | ExtractionError,
        official: set[str],
        candidate_id: int,
        research_id: int,
    ) -> None:
        assessment = assess_source(source.url, official)
        source.source_type, source.source_score = assessment.source_type, assessment.score
        if isinstance(extraction, ExtractionError):
            source.fetch_status = FetchStatus.FAILED
            source.http_status = extraction.http_status
            source.error = str(extraction)
            logger.warning(
                "Source fetch failed candidate_id=%s research_id=%s url=%s status=%s error=%s",
                candidate_id, research_id, source.url, extraction.http_status, extraction,
            )
            return
        source.fetch_status = FetchStatus.SUCCESS
        source.http_status = extraction.http_status
        source.error = None
        source.title = (extraction.title or source.title or "")[:1000] or None
        source.publisher = clean_publisher(extraction.publisher)
        source.published_at = extraction.published_at
        source.extracted_content = extraction.content
        source.raw_content = (extraction.raw_html or "")[: self.settings.raw_content_max_chars] or None
        logger.info(
            "Source saved candidate_id=%s research_id=%s url=%s chars=%d type=%s score=%d",
            candidate_id, research_id, source.url, len(extraction.content),
            source.source_type, source.source_score,
        )

    # Oryginał idzie pierwszy, potem źródła z wyższym score; nieudane lub puste pobrania są pomijane.
    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def _ordered_fetched_sources(sources: Sequence[ResearchSource]) -> list[ResearchSource]:
        fetched = [s for s in sources if s.fetch_status == FetchStatus.SUCCESS and s.extracted_content]
        return sorted(
            fetched,
            key=lambda s: (s.origin != ResearchSourceOrigin.ORIGINAL, -s.source_score, s.id or 0),
        )

    # Oddziela treść do analizy od pełnych rekordów źródeł i nakłada limity znaków przed wysłaniem do LLM.
    def _build_documents(self, sources: list[ResearchSource]) -> tuple[list[ResearchDocument], list[ResearchSource]]:
        limits = [
            self.settings.research_max_chars_original
            if s.origin == ResearchSourceOrigin.ORIGINAL
            else self.settings.research_max_chars_per_source
            for s in sources
        ]
        contents = fit_documents(
            [s.extracted_content or "" for s in sources], limits, self.settings.research_max_total_chars
        )
        used = sources[: len(contents)]
        documents = [
            ResearchDocument(
                url=s.url,
                title=s.title,
                publisher=s.publisher,
                source_type=s.source_type.value,
                source_score=s.source_score,
                published_at=s.published_at,
                content=content,
            )
            for s, content in zip(used, contents, strict=True)
        ]
        return documents, used

    # Sumuje tokeny wszystkich wywołań; koszt pozostaje nieznany, jeśli brakuje ceny choć jednego użytego
    # modelu.
    def _record_usage(self, research: Research, usages: list[LLMUsage]) -> None:
        if not usages:
            return
        research.llm_model = usages[-1].model
        research.llm_input_tokens = sum(u.input_tokens for u in usages)
        research.llm_output_tokens = sum(u.output_tokens for u in usages)
        costs = [self.costs.estimate(u.model, u.input_tokens, u.output_tokens) for u in usages]
        research.estimated_cost_usd = (
            sum(costs, Decimal(0)) if all(c is not None for c in costs) else None  # type: ignore[arg-type]
        )


def clean_publisher(name: str | None) -> str | None:
    """Metadata site names are often slugs ("Allen_Ai", "huggingface"); make them readable."""
    if not name:
        return None
    name = " ".join(name.replace("_", " ").split())[:300]
    return name[0].upper() + name[1:] if name.islower() else name


def _recognized(source: ResearchSource, official: set[str]) -> bool:
    return assess_source(source.url, official).recognized


# Po restarcie procesu zadania w tle już nie istnieją; pozostawione running zmieniamy na failed.
async def mark_interrupted_researches(session: AsyncSession) -> int:
    """Researches left running by a restarted process can never finish - mark them failed."""
    stale = (
        await session.scalars(select(Research).where(Research.status == ResearchStatus.RUNNING))
    ).all()
    for research in stale:
        research.status = ResearchStatus.FAILED
        research.error = "Interrupted by API restart"
        research.completed_at = datetime.now(UTC)
    await session.commit()
    return len(stale)
