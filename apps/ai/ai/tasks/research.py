# Rola pliku: Zadania researchu: `research.extract` (pobranie i ekstrakcja źródeł), `research.discover`
# (zapytania LLM, wyszukiwarka i pobranie nowych źródeł) oraz `research.analyse` (analiza LLM, fakty
# z odwołaniami do przekazanych źródeł). Stan i zapis należą do Laravela; tu tylko obliczenia.

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from ai.context import TaskContext
from ai.tasks.classify import CandidatePayload
from app.enums import ResearchSourceOrigin
from app.services.llm.base import CandidateInput, ResearchDocument
from app.services.research.content_budget import fit_documents
from app.services.research.content_extractor import ExtractedDocument, ExtractionError
from app.services.research.errors import NoSourceContentError
from app.services.research.fact_validation import validate_research_output
from app.services.research.link_discovery import compact_source_html, discover_article_links
from app.services.research.search import ManualSearchProvider, SearchResult
from app.services.research.publisher import clean_publisher
from app.services.research.source_scoring import (
    SourceAssessment, apply_llm_suggestion, assess_source, official_domains_for,
)
from app.services.research.urls import normalize_url

logger = logging.getLogger(__name__)
RESULTS_PER_QUERY = 5
MAX_QUERIES = 3
PREFERRED_TERMS = ("docs", "documentation", "migration", "pricing", "changelog", "guide", "release")


class ExtractInput(BaseModel):
    original_url: str
    urls: list[str]


class DiscoverInput(BaseModel):
    candidate: CandidatePayload
    original_url: str
    original_raw_content: str | None = None
    known_urls: list[str] = []


class SourcePayload(BaseModel):
    id: int
    url: str
    origin: ResearchSourceOrigin
    title: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    extracted_content: str | None = None
    fetch_status: str
    source_type: str = "other"
    source_score: int = 40


class AnalyseInput(BaseModel):
    candidate: CandidatePayload
    original_url: str
    sources: list[SourcePayload]


@dataclass(slots=True)
class SourceView:
    """Minimalne źródło dla walidacji faktów (id, url, ocena)."""

    id: int
    url: str
    source_score: int


async def _extract(ctx: TaskContext, url: str) -> ExtractedDocument | ExtractionError:
    try:
        return await ctx.extractor.extract(url)
    except ExtractionError as exc:
        return exc
    except Exception as exc:  # Błąd parsera jednej strony nie przerywa researchu.
        logger.exception("Unexpected extraction error url=%s", url)
        return ExtractionError(f"Extraction failed: {exc.__class__.__name__}")


def _source_result(ctx: TaskContext, url: str, extraction, official: set[str]) -> dict:
    assessment = assess_source(url, official)
    base = {"url": url, "source_type": assessment.source_type.value, "source_score": assessment.score}
    if isinstance(extraction, ExtractionError):
        return {**base, "fetch_status": "failed", "http_status": extraction.http_status, "error": str(extraction),
                "title": None, "publisher": None, "published_at": None, "extracted_content": None, "raw_content": None}
    raw = compact_source_html(extraction.raw_html or "", ctx.settings.raw_content_max_chars, base_url=extraction.url)
    return {**base, "fetch_status": "success", "http_status": extraction.http_status, "error": None,
            "title": (extraction.title or "")[:1000] or None, "publisher": clean_publisher(extraction.publisher),
            "published_at": extraction.published_at.isoformat() if extraction.published_at else None,
            "extracted_content": extraction.content, "raw_content": raw or None}


async def extract(data: dict, ctx: TaskContext) -> dict:
    payload = ExtractInput.model_validate(data)
    official = official_domains_for(payload.original_url)
    extractions = await asyncio.gather(*(_extract(ctx, url) for url in payload.urls))
    return {"sources": [_source_result(ctx, url, extraction, official)
                        for url, extraction in zip(payload.urls, extractions, strict=True)]}


async def discover(data: dict, ctx: TaskContext) -> dict:
    payload = DiscoverInput.model_validate(data)
    official = official_domains_for(payload.original_url)
    candidate = CandidateInput(payload.candidate.title, payload.candidate.summary, payload.candidate.source,
                               payload.candidate.published_at)
    results: list[SearchResult] = discover_article_links(payload.original_raw_content or "", payload.original_url)
    search = ctx.search
    queries: list[str] = []
    if not isinstance(search, ManualSearchProvider):
        researcher = ctx.providers["research"]
        try:
            generated = await ctx.call("discovering_sources", lambda: researcher.generate_search_queries(candidate))
            queries = [q.strip() for q in generated.queries.queries if q.strip()][:MAX_QUERIES]
        except Exception as exc:  # Odnośniki z oryginału wystarczą, gdy wyszukiwanie zawiedzie.
            logger.warning("Query generation failed error=%s", exc)
    if isinstance(search, ManualSearchProvider):
        results.extend(await search.search("", limit=ctx.settings.research_max_extra_sources))
    for query in queries:
        try:
            credits = getattr(search, "credits_per_query", 0)
            if credits:
                found = await ctx.call_search("searching_sources", credits,
                                              lambda q=query: search.search(q, limit=RESULTS_PER_QUERY))
            else:
                found = await search.search(query, limit=RESULTS_PER_QUERY)
            results.extend(found)
        except Exception as exc:
            logger.warning("Search failed query=%r error=%s", query, exc)

    known = {normalize_url(url) for url in payload.known_urls} | {normalize_url(payload.original_url)}
    picked: list[tuple[SearchResult, SourceAssessment]] = []
    for item in results:
        key = normalize_url(item.url)
        if key in known or not item.url.startswith(("http://", "https://")):
            continue
        known.add(key)
        picked.append((item, assess_source(item.url, official)))
    picked.sort(key=lambda pair: (pair[1].score, any(
        term in (pair[0].url + " " + pair[0].title).lower() for term in PREFERRED_TERMS)), reverse=True)
    picked = picked[: ctx.settings.research_max_extra_sources]
    extractions = await asyncio.gather(*(_extract(ctx, item.url) for item, _ in picked))
    sources = []
    for (item, _), extraction in zip(picked, extractions, strict=True):
        source = _source_result(ctx, item.url, extraction, official)
        source["title"] = source["title"] or (item.title[:1000] or None)
        sources.append(source)
    return {"queries": queries, "sources": sources}


def _documents(ctx: TaskContext, sources: list[SourcePayload]) -> tuple[list[ResearchDocument], list[SourcePayload]]:
    limits = [ctx.settings.research_max_chars_original if s.origin == ResearchSourceOrigin.ORIGINAL
              else ctx.settings.research_max_chars_per_source for s in sources]
    contents = fit_documents([s.extracted_content or "" for s in sources], limits, ctx.settings.research_max_total_chars)
    used = sources[: len(contents)]
    return [ResearchDocument(url=s.url, title=s.title, publisher=s.publisher, source_type=s.source_type,
                             source_score=s.source_score, published_at=s.published_at, content=content)
            for s, content in zip(used, contents, strict=True)], used


async def analyse(data: dict, ctx: TaskContext) -> dict:
    payload = AnalyseInput.model_validate(data)
    official = official_domains_for(payload.original_url)
    updates = {}
    for source in payload.sources:
        assessment = assess_source(source.url, official)
        source.source_type, source.source_score = assessment.source_type.value, assessment.score
        source.publisher = clean_publisher(source.publisher)
        updates[source.id] = {"id": source.id, "source_type": source.source_type, "source_score": source.source_score,
                              "publisher": source.publisher}
    fetched = sorted((s for s in payload.sources if s.fetch_status == "success" and s.extracted_content),
                     key=lambda s: (s.origin != ResearchSourceOrigin.ORIGINAL, -s.source_score, s.id))
    if not fetched:
        raise NoSourceContentError("No source content could be fetched - add a source manually and retry")

    documents, used = _documents(ctx, fetched)
    candidate = CandidateInput(payload.candidate.title, payload.candidate.summary, payload.candidate.source,
                               payload.candidate.published_at)
    researcher = ctx.providers["research"]
    result = await ctx.call("analysing", lambda: researcher.research(candidate, documents))
    views = [SourceView(s.id, s.url, s.source_score) for s in used]
    validated = validate_research_output(result.output, views, ctx.settings.research_max_facts)
    for source_id, suggestion in validated.suggested_types.items():
        source = updates[source_id]
        current = SourceAssessment(source["source_type"], source["source_score"],
                                   recognized=assess_source(next(s.url for s in payload.sources if s.id == source_id), official).recognized)
        refined = apply_llm_suggestion(current, suggestion)
        source["source_type"] = refined.source_type.value if hasattr(refined.source_type, "value") else refined.source_type
        source["source_score"] = refined.score
    return {
        "summary": result.output.summary,
        "why_it_matters": result.output.why_it_matters,
        "suggested_angle": result.output.suggested_angle,
        "uncertainties": validated.uncertainties,
        "conflicts": validated.conflicts,
        "facts": [{"claim": f.claim, "importance": f.importance.value if hasattr(f.importance, "value") else f.importance,
                   "confidence": f.confidence, "basis": str(f.basis), "source_ids": [s.id for s in f.sources]}
                  for f in validated.facts],
        "source_updates": list(updates.values()),
    }
