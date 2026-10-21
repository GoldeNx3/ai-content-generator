# Rola pliku: Zadania artykułu: `article.brief` (kontekst z researchu + brief LLM), `article.write` (tekst,
# walidacja, sekcje, SEO, liczniki), `article.rebuild` (metadane sekcji po edycji) i `seo.preview`
# (profil SEO wersji). Laravel zapisuje wynik i wersjonuje; tu wyłącznie obliczenia na treści.

from dataclasses import asdict, replace
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel, Field

from ai.context import TaskContext
from app.enums import CandidateCategory, FetchStatus
from app.schemas.article import ArticleBrief, ArticleFormat, GenerateArticleRequest
from app.schemas.wordpress import SEOData
from app.services.article.article_types import guide_for, length_hint, requested_format, resolve_length
from app.services.article.composition import (
    META_DESCRIPTION_MAX, META_TITLE_MAX, compose_content, count_words, sanitize_output, slugify, trim_text,
)
from app.services.article.editorial import describe_structure
from app.services.article.sections import rebuild_sections
from app.services.article.validation import validate_brief, validate_writer_output
from app.services.llm.base import ArticleContext, FactInput, SourceInput
from app.services.research.content_budget import fit_documents
from app.services.wordpress.preparation import plain, seo_profile


class FactPayload(BaseModel):
    id: int
    claim: str
    importance: str
    confidence: int
    source_ids: list[int] = []


class SourcePayload(BaseModel):
    id: int
    url: str
    origin: str
    title: str | None = None
    publisher: str | None = None
    source_type: str = "other"
    source_score: int = 40
    fetch_status: str
    extracted_content: str | None = None


class ResearchPayload(BaseModel):
    id: int
    summary: str | None = None
    why_it_matters: str | None = None
    suggested_angle: str | None = None
    facts: list[FactPayload]
    sources: list[SourcePayload]
    uncertainties: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []


class CandidatePayload(BaseModel):
    id: int
    title: str
    source: str
    published_at: datetime | None = None


class BriefInput(BaseModel):
    candidate: CandidatePayload
    research: ResearchPayload
    article_type: CandidateCategory
    request: GenerateArticleRequest
    recent_articles: list[dict[str, Any]] = []


class WriteInput(BaseModel):
    candidate_id: int
    research_id: int
    article_type: CandidateCategory
    request: GenerateArticleRequest
    context: dict[str, Any]
    brief: dict[str, Any]
    warnings: list[str] = []


class RebuildInput(BaseModel):
    content: str
    lead: str
    sections: list[dict[str, Any]] = []
    lead_fact_ids: list[int] = []
    research_snapshot: dict[str, Any] = Field(default_factory=dict)
    patches: list[dict[str, Any]] = []


class SeoPreviewInput(BaseModel):
    article: dict[str, Any]
    publication_profile: dict[str, Any] | None = None
    profile_version_matches: bool = False


def _context(payload: BriefInput, ctx: TaskContext) -> ArticleContext:
    settings = ctx.settings
    sources = sorted([s for s in payload.research.sources if s.fetch_status == FetchStatus.SUCCESS],
                     key=lambda s: (s.origin != "original", -s.source_score, s.id))
    contents = fit_documents(
        [s.extracted_content or "" for s in sources],
        [settings.research_max_chars_original if s.origin == "original" else settings.research_max_chars_per_source
         for s in sources],
        settings.research_max_total_chars,
    )
    source_contents = {s.id: content for s, content in zip(sources, contents)}
    article_format = requested_format(payload.request)
    return ArticleContext(
        candidate_title=payload.candidate.title,
        candidate_source=payload.candidate.source,
        published_at=payload.candidate.published_at,
        research_summary=payload.research.summary,
        why_it_matters=payload.research.why_it_matters,
        suggested_angle=payload.research.suggested_angle,
        facts=[FactInput(f.id, f.claim, f.importance, f.confidence, f.source_ids) for f in payload.research.facts],
        sources=[SourceInput(s.id, s.publisher, s.title, s.url, s.source_type, s.source_score, source_contents.get(s.id, ""))
                 for s in sources],
        uncertainties=list(payload.research.uncertainties),
        conflicts=list(payload.research.conflicts),
        article_type=payload.article_type.value,
        type_guide=guide_for(article_format).describe(),
        length_hint=length_hint(article_format, payload.request.length, len(payload.research.facts)),
        angle=(payload.request.angle or "").strip() or None,
        instructions=(payload.request.instructions or "").strip() or None,
        article_format=article_format,
        recent_structures=[describe_structure(a.get("sections") or [], a.get("content") or "")
                           for a in payload.recent_articles],
    )


def _restore_context(data: dict[str, Any]) -> ArticleContext:
    facts = [FactInput(**f) for f in data.pop("facts")]
    sources = [SourceInput(**s) for s in data.pop("sources")]
    published = data.pop("published_at")
    return ArticleContext(**data, facts=facts, sources=sources,
                          published_at=datetime.fromisoformat(published) if published else None)


async def brief(data: dict, ctx: TaskContext) -> dict:
    payload = BriefInput.model_validate(data)
    if not payload.research.facts:
        raise ValueError("Research has no verified facts - re-run research before writing.")
    context = _context(payload, ctx)
    writer = ctx.providers["write"]
    result = await ctx.call("building_brief", lambda: writer.generate_brief(context))
    validated, warnings = validate_brief(result.brief, context.facts)
    article_format = validated.article_format if context.article_format == "auto" else ArticleFormat(context.article_format)
    validated = validated.model_copy(update={
        "article_type": payload.article_type,
        "article_format": article_format,
        "primary_angle": context.angle or validated.primary_angle,
        "desired_length_words": resolve_length(article_format, payload.request.length, validated.desired_length_words,
                                               len(validated.required_facts)),
    })
    if validated.section_plan:
        plan_total = sum(section.target_words for section in validated.section_plan)
        budget = max(1, validated.desired_length_words - min(100, validated.desired_length_words // 10))
        validated = validated.model_copy(update={"section_plan": [
            section.model_copy(update={"target_words": max(1, round(section.target_words * budget / plan_total))})
            for section in validated.section_plan]})
    warnings.extend(f"Brak materiału w researchu: {gap}" for gap in validated.research_gaps)
    context_data = asdict(context)
    context_data["published_at"] = context.published_at.isoformat() if context.published_at else None
    return {"context": context_data, "brief": validated.model_dump(mode="json"), "warnings": warnings}


def _reference_texts(context: ArticleContext) -> list[str]:
    texts = [fact.claim for fact in context.facts]
    texts += [f"{s.title or ''} {s.publisher or ''} {s.content}" for s in context.sources]
    texts += [context.candidate_title]
    texts += [f"{u.get('claim', '')} {u.get('reason', '')}" for u in context.uncertainties]
    texts += [str(c) for c in context.conflicts]
    return texts


def _snapshot(context: ArticleContext) -> dict[str, Any]:
    return {
        "facts": [{"id": f.id, "claim": f.claim, "importance": f.importance, "confidence": f.confidence,
                   "source_ids": f.source_ids} for f in context.facts],
        "sources": [{"id": s.id, "url": s.url, "title": s.title, "publisher": s.publisher, "source_type": s.source_type,
                     "source_score": s.source_score, "content": s.content} for s in context.sources],
        "uncertainties": context.uncertainties,
        "conflicts": context.conflicts,
    }


async def write(data: dict, ctx: TaskContext) -> dict:
    payload = WriteInput.model_validate(data)
    context = _restore_context(dict(payload.context))
    brief_model = ArticleBrief.model_validate(payload.brief)
    article_format = brief_model.article_format
    writer_context = replace(context, article_format=article_format, type_guide=guide_for(article_format).describe())
    writer = ctx.providers["write"]
    result = await ctx.call("writing", lambda: writer.write_article(writer_context, brief_model))
    output = sanitize_output(result.output)
    validated = validate_writer_output(output, context.facts, {s.id for s in context.sources},
                                       brief_model.required_facts, reference_texts=_reference_texts(context))
    warnings = [*payload.warnings, *validated.warnings]
    content = compose_content(output)
    lead = output.lead.strip()
    words = count_words(lead, content)
    if brief_model.desired_length_words >= 500 and words < brief_model.desired_length_words * 0.7:
        warnings.append(f"Tekst za krótki: {words} słów przy celu {brief_model.desired_length_words}. "
                        "Sprawdź realizację planu sekcji i uzupełnij research o mechanizmy, przykłady lub instrukcje.")
    if payload.request.length == "long" and len([s for s in context.sources if s.content]) < 2:
        warnings.append("Pogłębiony tekst korzysta z mniej niż dwóch źródeł z treścią. "
                        "Dodaj dokumentację lub inne materiały pierwotne i ponów research.")
    seo_data = output.seo_data.model_dump(mode="json")
    if "schema_type" not in output.seo_data.model_fields_set:
        seo_data["schema_type"] = "NewsArticle" if payload.article_type.value in ("news", "release") else "Article"
    sections = [{**meta, "content": section.content.strip()}
                for meta, section in zip(validated.sections, output.sections, strict=True)]
    if output.conclusion.strip():
        sections.append({"heading": None, "content": output.conclusion.strip(),
                         "used_fact_ids": validated.conclusion_fact_ids, "source_ids": [], "is_conclusion": True})
    article = {
        "title": trim_text(output.title, 300),
        "slug": slugify(output.slug or output.title),
        "lead": lead,
        "content": content,
        "generated_content": content,
        "seo_data": seo_data,
        "meta_title": trim_text(output.meta_title, META_TITLE_MAX),
        "meta_description": trim_text(output.meta_description, META_DESCRIPTION_MAX),
        "article_type": payload.article_type.value,
        "angle": brief_model.primary_angle,
        "brief": brief_model.model_dump(mode="json"),
        "sections": sections,
        "lead_fact_ids": validated.lead_fact_ids,
        "generation_options": payload.request.model_dump(mode="json"),
        "research_snapshot": {**_snapshot(context), "candidate_id": payload.candidate_id, "research_id": payload.research_id,
                              "summary": context.research_summary, "why_it_matters": context.why_it_matters,
                              "suggested_angle": context.suggested_angle},
        "validation_warnings": warnings,
        "word_count": words,
        "sections_count": len(output.sections),
        "facts_used_count": len(validated.used_fact_ids),
        "facts_available_count": len(context.facts),
        "source_count": len(validated.referenced_source_ids),
    }
    article["seo_preview"] = _preview(article, None, False)[0]
    article["seo_origin"] = "article"
    return article


async def rebuild(data: dict, ctx: TaskContext) -> dict:
    payload = RebuildInput.model_validate(data)
    patches = [SimpleNamespace(field=p.get("field"), before=p.get("before", ""), after=p.get("after", ""),
                               fact_ids=p.get("fact_ids", []), source_ids=p.get("source_ids", [])) for p in payload.patches]
    sections = rebuild_sections(payload.content, payload.sections, payload.research_snapshot, patches)
    used = set(payload.lead_fact_ids) | {i for section in sections for i in section["used_fact_ids"]}
    return {
        "sections": sections,
        "sections_count": len(sections),
        "facts_used_count": len(used),
        "source_count": len({i for section in sections for i in section["source_ids"]}),
        "word_count": count_words(payload.lead, payload.content),
    }


def _preview(article: dict[str, Any], profile: dict[str, Any] | None, version_matches: bool) -> tuple[dict, str]:
    view = SimpleNamespace(**{**article, "seo_data": article.get("seo_data") or {}})
    raw = view.seo_data
    missing = not all(raw.get(k) for k in ("excerpt", "focus_keyword", "secondary_keywords", "tags", "category", "schema_type"))
    overrides = {k: v for k, v in (profile or {}).items() if k in SEOData.model_fields} if missing else {}
    if profile and not version_matches:
        overrides.update(excerpt=plain(view.lead), canonical_url=None, og_title=view.meta_title,
                         og_description=view.meta_description, twitter_title=view.meta_title,
                         twitter_description=view.meta_description)
    for key, value in raw.items():
        if value is not None and value != "" and value != []:
            overrides[key] = value
    resolved = seo_profile(view, overrides)
    origin = "publication_profile" if missing and profile else "article" if raw else "fallback"
    return {k: resolved[k] for k in SEOData.model_fields}, origin


async def seo_preview(data: dict, ctx: TaskContext) -> dict:
    payload = SeoPreviewInput.model_validate(data)
    preview, origin = _preview(payload.article, payload.publication_profile, payload.profile_version_matches)
    return {"seo_preview": preview, "seo_origin": origin}
