# Rola pliku: Etap research — publiczne operacje i cykl życia raportu.
# start zapisuje running, run uruchamia pipeline, a błędy zmieniają status na failed.
# Pobieranie stron jest w source_loader.py, sama analiza w pipeline.py.

import logging
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import Settings
from app.models import Candidate, Research, ResearchSource, ResearchSourceOrigin, ResearchStatus
from app.services.llm.base import ResearchLLMProvider
from app.services.llm.cost import LLMCostCalculator
from app.services.research.content_extractor import ContentExtractor
from app.services.research.errors import (
    CandidateNotFoundError, DuplicateSourceError, ResearchError,
    ResearchInProgressError, ResearchNotFoundError,
)
from app.services.jobs.transactions import save
from app.services.research.pipeline import ResearchPipeline
from app.services.research.search import SearchProvider
from app.services.research.source_loader import ResearchSourceLoader
from app.services.research.source_scoring import official_domains_for
from app.services.research.urls import normalize_url

logger = logging.getLogger(__name__)


class ResearchService:
    """Zarządza raportem i zleca pracę mniejszym klasom, zamiast robić wszystko sam."""

    def __init__(
        self, session: AsyncSession, extractor: ContentExtractor, search: SearchProvider,
        llm: ResearchLLMProvider, cost_calculator: LLMCostCalculator, settings: Settings, execution=None,
    ) -> None:
        self.session = session
        self.execution = execution
        # Wszystkie części używają tej samej sesji, więc commity mają te same
        # granice co przed podziałem. Nie tworzymy tutaj nowych połączeń.
        self.loader = ResearchSourceLoader(extractor, settings)
        self.pipeline = ResearchPipeline(session, self.loader, search, llm, cost_calculator, settings, execution=execution)

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def research_candidate(self, candidate_id: int) -> Research:
        """Uruchamia pełny research: oryginał, dodatkowe źródła i analizę LLM."""
        research = await self.start(candidate_id, discover=True)
        return await self.run(research.id, discover=True)

    async def get_for_candidate(self, candidate_id: int) -> Research | None:
        return await self.session.scalar(select(Research).where(Research.candidate_id == candidate_id))

    # Zapisuje status running przed uruchomieniem analizy; discover decyduje, czy zachować dotychczasowe
    # źródła.
    async def start(self, candidate_id: int, discover: bool) -> Research:
        """Tworzy/resetuje raport jako running; analiza zostanie uruchomiona osobno.

        discover=True: nowy research; zostają tylko ręcznie dodane źródła.
        discover=False: ponowna analiza istniejących źródeł; zastępuje fakty i raport.
        """
        await self._get_candidate(candidate_id)
        research = await self.get_for_candidate(candidate_id)
        if research is None:
            if not discover:
                raise ResearchNotFoundError("Research not found - start a research first")
            research = Research(candidate_id=candidate_id, search_queries=[], uncertainties=[], conflicts=[], sources=[], facts=[])
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
        if self.execution:
            research.job_id = self.execution.job_id
            await self.session.flush()
        await save(self.session, self.execution,
                   checkpoint={"research_id": research.id} if self.execution else None)
        # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
        await self.session.refresh(research)  # odczytaj wartości domyślne i relacje do odpowiedzi API
        return research

    async def run(self, research_id: int, discover: bool) -> Research:
        """Uruchamia analizę; jej błędy zapisuje w raporcie ze statusem failed."""
        research = await self.session.get(Research, research_id)
        if research is None:
            raise ResearchNotFoundError(f"Research {research_id} not found")
        candidate = await self._get_candidate(research.candidate_id)
        if research.status != ResearchStatus.RUNNING:
            research.status = ResearchStatus.RUNNING
            research.started_at = datetime.now(UTC)
            await save(self.session, self.execution)
        started = time.perf_counter()
        logger.info("Research started candidate_id=%s research_id=%s discover=%s", candidate.id, research.id, discover)

        try:
            await self.pipeline.run(research, candidate, discover)
            research.status = ResearchStatus.COMPLETED
            logger.info(
                "Research completed candidate_id=%s research_id=%s facts=%d sources=%d duration=%.1fs cost=%s",
                candidate.id, research.id, len(research.facts), len(research.sources),
                time.perf_counter() - started, research.estimated_cost_usd,
            )
        except Exception as exc:
            if self.execution is not None:
                raise
            logger.exception("Research failed candidate_id=%s research_id=%s", candidate.id, research.id)
            # rollback wycofuje niezakończoną transakcję po błędzie; wcześniejsze commity pozostają zapisane.
            await self.session.rollback()  # wycofaj niedokończony raport; zapisane źródła zostają
            research = await self.session.get(Research, research_id, populate_existing=True)
            assert research is not None
            research.status = ResearchStatus.FAILED
            research.error = str(exc) or exc.__class__.__name__
        research.completed_at = datetime.now(UTC)
        await save(self.session, self.execution, result=research)
        await self.session.refresh(research)
        return research

    async def add_manual_source(self, candidate_id: int, url: str) -> ResearchSource:
        candidate = await self._get_candidate(candidate_id)
        research = await self.get_for_candidate(candidate_id)
        if research is None:
            research = Research(candidate_id=candidate_id, search_queries=[], uncertainties=[], conflicts=[], sources=[], facts=[])
            self.session.add(research)
            # flush wysyła zmiany do bazy (np. nadaje ID), ale nie zatwierdza jeszcze transakcji jak commit.
            await self.session.flush()
        elif research.status == ResearchStatus.RUNNING:
            raise ResearchInProgressError("Research is running - add sources after it finishes")
        if normalize_url(url) in {normalize_url(s.url) for s in research.sources}:
            raise DuplicateSourceError("This URL is already a source of this research")

        source = ResearchSource(url=url, origin=ResearchSourceOrigin.MANUAL)
        research.sources.append(source)
        await self.loader.fetch_into(source, official_domains_for(candidate.external_url), candidate.id, research.id)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def _get_candidate(self, candidate_id: int) -> Candidate:
        candidate = await self.session.get(
            Candidate, candidate_id, options=[joinedload(Candidate.source)], populate_existing=True
        )
        if candidate is None:
            raise CandidateNotFoundError("Candidate not found")
        return candidate


# Zgodność ze starszymi integracjami: sprzątanie raportów bez trwałego zadania.
# Raporty z job_id odzyskuje worker; restart API nie zmienia ich stanu.
async def mark_interrupted_researches(session: AsyncSession) -> int:
    """Oznacza jako failed raporty, których zadania utracono po restarcie API."""
    stale = (
        await session.scalars(select(Research).where(Research.status == ResearchStatus.RUNNING, Research.job_id.is_(None)))
    ).all()
    for research in stale:
        research.status = ResearchStatus.FAILED
        research.error = "Interrupted by API restart"
        research.completed_at = datetime.now(UTC)
    await session.commit()
    return len(stale)
