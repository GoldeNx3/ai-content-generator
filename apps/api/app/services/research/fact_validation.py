"""Validates LLM research output against the sources that were actually sent to the LLM.

The LLM must never introduce URLs: every reference is matched (after normalisation) to an
existing ResearchSource; unknown references are dropped.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.models import FactBasis, FactImportance, ResearchSource, ResearchSourceType
from app.schemas.research import ResearchOutput
from app.services.research.urls import normalize_url

logger = logging.getLogger(__name__)

# Backend-enforced confidence ceilings: the LLM classifies the basis, the backend sets the limit.
BASIS_MAX_CONFIDENCE = {
    FactBasis.VERIFIABLE: 100,
    FactBasis.VENDOR_CLAIM: 85,
    FactBasis.SECONDARY: 70,
}

UNSOURCED_REASON = "Brak potwierdzenia w przekazanych źródłach (LLM nie wskazał poprawnego źródła)."


@dataclass(slots=True)
class ValidatedFact:
    claim: str
    importance: FactImportance
    confidence: int
    sources: list[ResearchSource]


@dataclass(slots=True)
class ValidatedResearch:
    facts: list[ValidatedFact] = field(default_factory=list)
    uncertainties: list[dict[str, str]] = field(default_factory=list)
    conflicts: list[dict[str, object]] = field(default_factory=list)
    suggested_types: dict[int, ResearchSourceType] = field(default_factory=dict)
    dropped_references: int = 0


def cap_confidence(confidence: int, basis: FactBasis, sources: Iterable[ResearchSource]) -> int:
    """A fact can't be more credible than its basis allows, nor than its best source."""
    best_source = max((source.source_score or 0 for source in sources), default=0)
    return min(confidence, BASIS_MAX_CONFIDENCE[basis], best_source)


IMPORTANCE_ORDER = {FactImportance.CRITICAL: 0, FactImportance.IMPORTANT: 1, FactImportance.SUPPORTING: 2}


def validate_research_output(
    output: ResearchOutput, sources: list[ResearchSource], max_facts: int | None = None
) -> ValidatedResearch:
    by_url = {normalize_url(source.url): source for source in sources}
    result = ValidatedResearch(
        uncertainties=[{"claim": u.claim, "reason": u.reason} for u in output.uncertainties]
    )

    def resolve(url: str) -> ResearchSource | None:
        source = by_url.get(normalize_url(url)) if url.startswith(("http://", "https://")) else None
        if source is None:
            result.dropped_references += 1
        return source

    for fact in output.facts:
        matched: dict[int, ResearchSource] = {}
        for url in fact.source_urls:
            source = resolve(url)
            if source is not None:
                matched[source.id] = source
        if not matched:
            # A fact without a verifiable source is not a fact - keep it visible as an uncertainty.
            result.uncertainties.append({"claim": fact.claim, "reason": UNSOURCED_REASON})
            continue
        result.facts.append(
            ValidatedFact(
                fact.claim,
                fact.importance,
                cap_confidence(fact.confidence, fact.basis, matched.values()),
                list(matched.values()),
            )
        )

    if max_facts is not None and len(result.facts) > max_facts:
        logger.warning("LLM returned %d facts, keeping the %d most important", len(result.facts), max_facts)
        ranked = sorted(enumerate(result.facts), key=lambda item: (IMPORTANCE_ORDER[item[1].importance], item[0]))
        keep = {index for index, _ in ranked[:max_facts]}
        result.facts = [fact for index, fact in enumerate(result.facts) if index in keep]

    for conflict in output.conflicts:
        conflict_sources = []
        for item in conflict.sources:
            source = resolve(item.url)
            if source is not None:
                conflict_sources.append({"url": source.url, "claim": item.claim})
        if conflict_sources:
            result.conflicts.append({"topic": conflict.topic, "sources": conflict_sources})

    for assessment in output.source_types:
        source = by_url.get(normalize_url(assessment.url))
        if source is not None:
            result.suggested_types[source.id] = assessment.source_type

    if result.dropped_references:
        logger.warning("Dropped %d source references not present in research sources", result.dropped_references)
    return result
