# Rola pliku: Etap write — koordynuje generację briefu i artykułu, walidację, koszty, wersjonowanie oraz ręczną edycję
# zapisanych draftów.

import logging
import time
from dataclasses import replace
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    Article,
    ArticleStatus,
    Candidate,
    CandidateCategory,
    FetchStatus,
    Research,
    ResearchStatus,
)
from app.schemas.article import ArticleFormat, ArticleUpdate, GenerateArticleRequest, WriterOutput
from app.services.article.article_types import guide_for, requested_format, resolve_length
from app.services.article.composition import (
    META_DESCRIPTION_MAX,
    META_TITLE_MAX,
    compose_content,
    sanitize_output,
    count_words,
    slugify,
    trim_text,
)
from app.services.article.context import build_article_context
from app.services.article.editorial import recent_structures
from app.services.jobs.transactions import save, stage
from app.services.article.validation import validate_brief, validate_writer_output
from app.services.llm.base import ArticleContext, ArticleLLMProvider, FactInput, LLMUsage, SourceInput
from app.services.llm.cost import LLMCostCalculator

logger = logging.getLogger(__name__)

RESEARCH_REQUIRED_MESSAGE = "Complete research before generating an article."


class ArticleError(Exception):
    """Base error for article operations (mapped to HTTP errors by the API layer)."""


class CandidateNotFoundError(ArticleError):
    pass


class ArticleNotFoundError(ArticleError):
    pass


class ResearchNotReadyError(ArticleError):
    pass


class ArticleService:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(
        self, session: AsyncSession, llm: ArticleLLMProvider, cost_calculator: LLMCostCalculator, execution=None
    ) -> None:
        self.session = session
        self.llm = llm
        self.costs = cost_calculator
        self.execution = execution

    # ---------- queries ----------

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def list_versions(self, candidate_id: int) -> Sequence[Article]:
        await self._get_candidate(candidate_id)
        query = select(Article).where(Article.candidate_id == candidate_id).order_by(Article.version.desc())
        articles = (await self.session.scalars(query)).all()
        from app.models import ArticleQA
        reports = (await self.session.scalars(select(ArticleQA).where(ArticleQA.article_id.in_([a.id for a in articles]))
            .order_by(ArticleQA.article_id, ArticleQA.created_at.desc(), ArticleQA.id.desc()).distinct(ArticleQA.article_id))).all()
        by_id = {q.article_id: q for q in reports}
        from app.services.qa.context import matches_article
        for article in articles:
            qa = by_id.get(article.id)
            article.qa_score = qa.overall_score if qa and qa.status == 'completed' and matches_article(qa, article) else None
            article.qa_status = ('stale' if not matches_article(qa, article) else qa.status) if qa else 'required'
        from app.models import ArticleFix
        from app.core.config import get_settings
        fixes = (await self.session.execute(select(ArticleFix.source_article_version_id, ArticleFix.iteration)
            .join(Article, Article.id == ArticleFix.source_article_version_id)
            .where(Article.candidate_id == candidate_id, ArticleFix.status == 'completed'))).all()
        by_article = {a.id: a for a in articles}
        for article in articles:
            ancestor = article
            ancestors = set()
            while ancestor and ancestor.id not in ancestors:
                ancestors.add(ancestor.id)
                if ancestor.created_by in ('generated','regenerated','legacy'): break
                ancestor = by_article.get(ancestor.parent_version_id)
            used = max([article.auto_fix_iteration or 0] + [iteration for source_id, iteration in fixes if source_id in ancestors])
            article.auto_fix_iterations_remaining = max(0, get_settings().auto_fix_max_iterations - used)
        return articles

    async def get(self, article_id: int) -> Article:
        article = await self.session.get(Article, article_id)
        if article is None:
            raise ArticleNotFoundError("Article not found")
        from app.services.auto_fix.context import iterations_used
        from app.services.article.versions import latest_qa
        from app.services.qa.context import matches_article
        qa = await latest_qa(self.session, article)
        article.qa_score = qa.overall_score if qa and qa.status == 'completed' and matches_article(qa, article) else None
        article.qa_status = ('stale' if not matches_article(qa, article) else qa.status) if qa else 'required'
        from app.core.config import get_settings
        article.auto_fix_iterations_remaining = max(0, get_settings().auto_fix_max_iterations - await iterations_used(self.session, article))
        return article

    # ---------- generation ----------

    # Najpierw ukończony research i fakty, potem brief i writer; zapis nowej wersji następuje po
    # otrzymaniu i walidacji wyników.
    async def generate(self, candidate_id: int, request: GenerateArticleRequest, context: ArticleContext | None = None) -> Article:
        candidate = await self._get_candidate(candidate_id)
        research = await self.session.scalar(select(Research).where(Research.candidate_id == candidate_id))
        if research is None or research.status != ResearchStatus.COMPLETED:
            raise ResearchNotReadyError(RESEARCH_REQUIRED_MESSAGE)
        if not research.facts:
            raise ResearchNotReadyError("Research has no verified facts - re-run research before writing.")

        article_type = request.article_type or candidate.category or CandidateCategory.NEWS
        if context is None:
            context = self._build_context(candidate, research, article_type, request)
            context = replace(context, recent_structures=await recent_structures(self.session))
        if context.article_format is None:
            context = replace(context, article_format=requested_format(request))
        started = time.perf_counter()
        logger.info(
            "Article generation started candidate_id=%s research_id=%s type=%s facts=%d",
            candidate.id, research.id, article_type, len(context.facts),
        )

        brief_result = await self.llm.generate_brief(context)
        brief, warnings = validate_brief(brief_result.brief, context.facts)
        article_format = brief.article_format if context.article_format == "auto" else ArticleFormat(context.article_format)
        brief = brief.model_copy(
            update={
                "article_type": article_type,  # the editor's choice wins over the LLM
                "article_format": article_format,
                "primary_angle": context.angle or brief.primary_angle,
                "desired_length_words": resolve_length(
                    article_format, request.length, brief.desired_length_words, len(brief.required_facts)
                ),
            }
        )
        if brief.section_plan:
            # Reserve the lead's share; keep section allocations aligned with the final target.
            plan_total = sum(section.target_words for section in brief.section_plan)
            section_budget = max(1, brief.desired_length_words - min(100, brief.desired_length_words // 10))
            brief = brief.model_copy(update={"section_plan": [
                section.model_copy(update={"target_words": max(1, round(section.target_words * section_budget / plan_total))})
                for section in brief.section_plan
            ]})
        warnings.extend(f"Brak materiału w researchu: {gap}" for gap in brief.research_gaps)

        writer_context = replace(context, article_format=article_format,
                                 type_guide=guide_for(article_format).describe())
        writer_result = await self.llm.write_article(writer_context, brief)
        await stage(self.execution, "validating")
        output = sanitize_output(writer_result.output)
        source_ids = {source.id for source in context.sources}
        validated = validate_writer_output(
            output,
            context.facts,
            source_ids,
            brief.required_facts,
            reference_texts=self._reference_texts(context),
        )
        warnings.extend(validated.warnings)

        content = compose_content(output)
        lead = output.lead.strip()
        word_count = count_words(lead, content)
        if brief.desired_length_words >= 500 and word_count < brief.desired_length_words * 0.7:
            warnings.append(
                f"Tekst za krótki: {word_count} słów przy celu {brief.desired_length_words}. "
                "Sprawdź realizację planu sekcji i uzupełnij research o mechanizmy, przykłady lub instrukcje."
            )
        if request.length == "long" and len([s for s in context.sources if s.content]) < 2:
            warnings.append("Pogłębiony tekst korzysta z mniej niż dwóch źródeł z treścią. "
                            "Dodaj dokumentację lub inne materiały pierwotne i ponów research.")
        brief_cost = self._cost(brief_result.usage)
        writer_cost = self._cost(writer_result.usage)
        # model_dump zamienia model Pydantic na słownik; exclude_unset pomija pola, których użytkownik
        # nie przesłał.
        article = Article(
            candidate_id=candidate.id,
            research_id=research.id,
            version=await self._next_version(candidate.id),
            is_current=True,
            status=ArticleStatus.DRAFT,
            title=trim_text(output.title, 300),
            slug=slugify(output.slug or output.title),
            lead=lead,
            content=content,
            generated_content=content,
            meta_title=trim_text(output.meta_title, META_TITLE_MAX),
            meta_description=trim_text(output.meta_description, META_DESCRIPTION_MAX),
            article_type=article_type,
            angle=brief.primary_angle,
            brief=brief.model_dump(mode="json"),
            sections=_section_records(validated.sections, output, validated.conclusion_fact_ids),
            lead_fact_ids=validated.lead_fact_ids,
            generation_options=request.model_dump(mode="json"),
            research_snapshot={**self._snapshot(context), "candidate_id": candidate.id,
                "research_id": research.id, "summary": context.research_summary,
                "why_it_matters": context.why_it_matters, "suggested_angle": context.suggested_angle},
            validation_warnings=warnings,
            word_count=word_count,
            sections_count=len(output.sections),
            facts_used_count=len(validated.used_fact_ids),
            facts_available_count=len(context.facts),
            source_count=len(validated.referenced_source_ids),
            llm_model=writer_result.usage.model,
            llm_input_tokens=brief_result.usage.input_tokens + writer_result.usage.input_tokens,
            llm_output_tokens=brief_result.usage.output_tokens + writer_result.usage.output_tokens,
            estimated_cost_usd=_sum_costs(brief_cost, writer_cost),
            brief_llm_model=brief_result.usage.model,
            brief_input_tokens=brief_result.usage.input_tokens,
            brief_output_tokens=brief_result.usage.output_tokens,
            brief_cost_usd=brief_cost,
            writer_input_tokens=writer_result.usage.input_tokens,
            writer_output_tokens=writer_result.usage.output_tokens,
            writer_cost_usd=writer_cost,
        )
        # Przydział wersji i publikacja mają wspólną krótką blokadę kandydata.
        # HTTP/LLM już się zakończyły; nie blokujemy wiersza podczas generacji.
        await self.session.scalar(select(Candidate.id).where(Candidate.id == candidate.id).with_for_update())
        article.version = await self._next_version(candidate.id)
        # Keep previous versions; only the "current" flag moves.
        await self.session.execute(
            update(Article)
            .where(Article.candidate_id == candidate.id, Article.is_current.is_(True))
            .values(is_current=False)
        )
        from app.services.article.versions import content_hash
        article.content_hash = content_hash(article)
        if self.execution and self.execution.job_id:
            from app.models.job import Job
            generation_job = await self.session.get(Job, self.execution.job_id)
            article.parent_version_id = generation_job.payload['options'].get('parent_version_id')
            article.created_by = 'regenerated' if article.parent_version_id else 'generated'
        self.session.add(article)
        # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
        # trwałego zapisu.
        await save(self.session, self.execution, result=article)
        # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
        await self.session.refresh(article)
        logger.info(
            "Article generated candidate_id=%s article_id=%s version=%s words=%d facts=%d/%d "
            "warnings=%d cost=%s duration=%.1fs",
            candidate.id, article.id, article.version, article.word_count, article.facts_used_count,
            article.facts_available_count, len(warnings), article.estimated_cost_usd,
            time.perf_counter() - started,
        )
        return article

    async def regenerate(self, article_id: int, request: GenerateArticleRequest | None) -> Article:
        """New version for the same candidate. Options default to the ones of the given version."""
        base = await self.get(article_id)
        options = GenerateArticleRequest.model_validate(base.generation_options)
        if request is not None:
            options = options.model_copy(update=request.model_dump(exclude_unset=True))
        return await self.generate(base.candidate_id, options)

    # ---------- editing ----------

    async def update(self, article_id: int, payload: ArticleUpdate) -> Article:
        # Candidate first: matches all version allocation and approval operations.
        original = await self.get(article_id)
        await self.session.scalar(select(Candidate.id).where(Candidate.id == original.candidate_id).with_for_update())
        article = await self.session.scalar(select(Article).where(Article.id == article_id)
            .with_for_update().execution_options(populate_existing=True))
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        changes = {field: value if field == 'content' else value.strip() for field, value in changes.items()}
        if not any(getattr(article, field) != value for field, value in changes.items()):
            await self.session.commit()
            return article
        from app.services.article.versions import child_version
        child = await child_version(self.session, article, changes, 'manual_edit')
        await self.session.commit()
        await self.session.refresh(child)
        return child

    async def set_status(self, article_id: int, status: ArticleStatus) -> Article:
        from app.services.article.versions import approve_version, reject_version
        from app.services.jobs.errors import JobInputError
        if status == ArticleStatus.APPROVED:
            from app.core.config import get_settings
            return await approve_version(self.session, article_id, get_settings())
        if status == ArticleStatus.REJECTED:
            return await reject_version(self.session, article_id, None)
        raise JobInputError('Użyj QA i zatwierdzenia konkretnej wersji; ręczna zmiana tego statusu jest niedozwolona.')

    # ---------- helpers ----------

    async def _get_candidate(self, candidate_id: int) -> Candidate:
        candidate = await self.session.get(
            Candidate, candidate_id, options=[joinedload(Candidate.source)], populate_existing=True
        )
        if candidate is None:
            raise CandidateNotFoundError("Candidate not found")
        return candidate

    async def _next_version(self, candidate_id: int) -> int:
        current = await self.session.scalar(
            select(func.max(Article.version)).where(Article.candidate_id == candidate_id)
        )
        return (current or 0) + 1

    def _build_context(self, candidate, research, article_type, request) -> ArticleContext:
        return build_article_context(candidate, research, article_type, request)

    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def _reference_texts(context: ArticleContext) -> list[str]:
        texts = [fact.claim for fact in context.facts]
        texts += [f"{s.title or ''} {s.publisher or ''} {s.content}" for s in context.sources]
        texts += [context.candidate_title]
        texts += [f"{u.get('claim', '')} {u.get('reason', '')}" for u in context.uncertainties]
        texts += [str(c) for c in context.conflicts]
        return texts

    # Kopia faktów i źródeł z chwili generacji pozwala odczytać historię artykułu po zmianie researchu.
    @staticmethod
    def _snapshot(context: ArticleContext) -> dict[str, object]:
        return {
            "facts": [
                {
                    "id": f.id,
                    "claim": f.claim,
                    "importance": f.importance,
                    "confidence": f.confidence,
                    "source_ids": f.source_ids,
                }
                for f in context.facts
            ],
            "sources": [
                {
                    "id": s.id,
                    "url": s.url,
                    "title": s.title,
                    "publisher": s.publisher,
                    "source_type": s.source_type,
                    "source_score": s.source_score,
                    "content": s.content,
                }
                for s in context.sources
            ],
            "uncertainties": context.uncertainties,
            "conflicts": context.conflicts,
        }

    def _cost(self, usage: LLMUsage) -> Decimal | None:
        return self.costs.estimate(usage.model, usage.input_tokens, usage.output_tokens)


def _section_records(
    validated_sections: list[dict[str, Any]], output: WriterOutput, conclusion_fact_ids: list[int]
) -> list[dict[str, Any]]:
    """Generation metadata per section (fact/source references). The editable text lives in content."""
    records = [
        {**meta, "content": section.content.strip()}
        for meta, section in zip(validated_sections, output.sections, strict=True)
    ]
    if output.conclusion.strip():
        records.append(
            {
                "heading": None,
                "content": output.conclusion.strip(),
                "used_fact_ids": conclusion_fact_ids,
                "source_ids": [],
                "is_conclusion": True,
            }
        )
    return records


def _sum_costs(*costs: Decimal | None) -> Decimal | None:
    return None if any(cost is None for cost in costs) else sum(costs, Decimal(0))  # type: ignore[arg-type]
