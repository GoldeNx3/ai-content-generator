# Rola pliku: Kolejne operacje analizy researchu: źródła → dokumenty → LLM → fakty.
# ResearchService zarządza statusem i błędami całego zadania; ta klasa wykonuje
# analizę. Kompozycja oznacza tu zwykłe wywoływanie osobnego obiektu loader.

import asyncio
import logging
import time
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Candidate, FetchStatus, Research, ResearchFact, ResearchSource, ResearchSourceOrigin
from app.services.llm.base import CandidateInput, LLMUsage, ResearchDocument, ResearchLLMProvider
from app.services.llm.cost import LLMCostCalculator
from app.services.jobs.errors import LeaseLostError
from app.services.jobs.transactions import save, stage
from app.services.research.content_budget import fit_documents
from app.services.research.errors import NoSourceContentError
from app.services.research.fact_validation import validate_research_output
from app.services.research.search import ManualSearchProvider, SearchProvider, SearchResult
from app.services.research.link_discovery import discover_article_links
from app.services.research.source_loader import ResearchSourceLoader, clean_publisher
from app.services.research.source_scoring import (
    SourceAssessment, apply_llm_suggestion, assess_source, official_domains_for,
)
from app.services.research.urls import normalize_url

logger = logging.getLogger(__name__)
RESULTS_PER_QUERY = 5
MAX_QUERIES = 3


class ResearchPipeline:
    """Wykonuje research; wyjątek obsługuje serwis i zapisuje końcowy status."""

    def __init__(
        self, session: AsyncSession, loader: ResearchSourceLoader, search: SearchProvider,
        llm: ResearchLLMProvider, costs: LLMCostCalculator, settings: Settings, execution=None,
    ) -> None:
        self.session = session
        self.loader = loader
        self.search = search
        self.llm = llm
        self.costs = costs
        self.settings = settings
        self.execution = execution
        self.candidate_input = None

    async def run(self, research: Research, candidate: Candidate, discover: bool) -> None:
        # 1. Przygotuj kontekst wpisu i źródło oryginalne.
        official = official_domains_for(candidate.external_url)
        candidate_input = self.candidate_input or CandidateInput(
            title=candidate.title,
            summary=candidate.summary,
            source=candidate.source.name,
            published_at=candidate.original_published_at,
        )
        usages: list[LLMUsage] = []
        known_sources = list(research.sources)
        await stage(self.execution, "fetching_original")

        if not any(s.origin == ResearchSourceOrigin.ORIGINAL for s in research.sources):
            original = ResearchSource(url=candidate.external_url, origin=ResearchSourceOrigin.ORIGINAL)
            research.sources.append(original)
            await self.loader.fetch_into(original, official, candidate.id, research.id)
            await save(self.session, self.execution)

        # Ponawiamy nieudane pobrania zachowanych źródeł, np. niedostępnego ręcznego URL-a.
        for source in known_sources:
            if source.fetch_status != FetchStatus.SUCCESS:
                await self.loader.fetch_into(source, official, candidate.id, research.id)
        await save(self.session, self.execution)

        # 2. Opcjonalnie znajdź i pobierz dodatkowe materiały.
        await stage(self.execution, "discovering_sources")
        if discover:
            await self._discover_sources(research, candidate, candidate_input, official, usages)

        # Oceniamy także zachowane źródła według aktualnych reguł wiarygodności.
        for source in research.sources:
            assessment = assess_source(source.url, official)
            source.source_type, source.source_score = assessment.source_type, assessment.score
            source.publisher = clean_publisher(source.publisher)

        fetched = self._ordered_fetched_sources(research.sources)
        if not fetched:
            raise NoSourceContentError("No source content could be fetched - add a source manually and retry")

        # 3. Zmieść teksty w budżecie i przekaż je do analizy LLM.
        documents, used_sources = self._build_documents(fetched)
        llm_started = time.perf_counter()
        await stage(self.execution, "analysing")
        result = await self.llm.research(candidate_input, documents)
        usages.append(result.usage)
        self._record_usage(research, usages)
        logger.info(
            "Research LLM research_id=%s model=%s documents=%d prompt_chars=%d duration=%.1fs",
            research.id, result.usage.model, len(documents),
            sum(len(d.content) for d in documents), time.perf_counter() - llm_started,
        )

        # 4. Sprawdź referencje modelu, a dopiero potem utwórz fakty ORM.
        # Końcowy commit raportu wykona ResearchService po sukcesie pipeline’u.
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
                current = SourceAssessment(source.source_type, source.source_score, recognized=assess_source(source.url, official).recognized)
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
        if self.execution and self.execution.checkpoints.get('discovery_done'):
            # Zapytania są już ukończone; nie wykonujemy ich ponownie, lecz ich
            # zapisane zużycie nadal należy do kosztu końcowego raportu.
            cached = self.execution.checkpoints.get('discovering_sources')
            if cached and cached.get('usage'):
                usages.append(LLMUsage(**cached['usage']))
            return
        results: list[SearchResult] = []
        for source in research.sources:
            if source.origin == ResearchSourceOrigin.ORIGINAL and source.fetch_status == FetchStatus.SUCCESS:
                if "raw_content" in inspect(source).unloaded:
                    await self.session.refresh(source, ["raw_content"])
                results.extend(discover_article_links(source.raw_content or "", source.url))
        queries = []
        if not isinstance(self.search, ManualSearchProvider):
            try:
                queries_result = await self.llm.generate_search_queries(candidate_input)
                usages.append(queries_result.usage)
                queries = [q.strip() for q in queries_result.queries.queries if q.strip()][:MAX_QUERIES]
            except LeaseLostError:
                raise
            except Exception as exc:  # Linked evidence is still usable if search fails.
                logger.warning("Query generation failed research_id=%s error=%s", research.id, exc)
        research.search_queries = queries
        self._record_usage(research, usages)
        await save(self.session, self.execution)

        if isinstance(self.search, ManualSearchProvider):
            results.extend(await self.search.search("", limit=self.settings.research_max_extra_sources))
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
        # Prefer complementary documentation over repeated announcements at equal credibility.
        picked.sort(key=lambda pair: (pair[1].score, any(
            term in (pair[0].url + " " + pair[0].title).lower()
            for term in ("docs", "documentation", "migration", "pricing", "changelog", "guide", "release")
        )), reverse=True)
        picked = picked[: self.settings.research_max_extra_sources]

        new_sources = [
            ResearchSource(url=item.url, title=item.title[:1000] or None, origin=ResearchSourceOrigin.SEARCH)
            for item, _ in picked
        ]
        await stage(self.execution, "fetching_sources")
        # gather wykonuje korutyny współbieżnie i zbiera wyniki w kolejności przekazanych argumentów.
        extractions = await asyncio.gather(*(self.loader.extract_safely(source.url) for source in new_sources))
        for source, extraction in zip(new_sources, extractions, strict=True):
            research.sources.append(source)
            self.loader.apply_extraction(source, extraction, official, candidate.id, research.id)
        await save(self.session, self.execution, checkpoint={'discovery_done': True})

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
