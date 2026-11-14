# Rola pliku: Sprawdza referencje do faktów i źródeł oraz tworzy ostrzeżenia dla redaktora. Heurystyki
# nie zastępują weryfikacji prawdziwości tekstu.

"""Hallucination safeguards for writer output.

- used_fact_ids / lead / conclusion fact ids must exist in the research -> unknown ids are removed;
- source_ids must belong to the research -> unknown ids are removed;
- each section's sources are completed with the sources of its facts;
- numbers in the text that appear in no research fact are reported as warnings for the human reviewer.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.schemas.article import ArticleBrief, WriterOutput
from app.services.llm.base import FactInput
from app.services.markdown import fences, without_fenced_code

logger = logging.getLogger(__name__)

# Phrases that usually introduce goals/effects/opinions the research doesn't state, or AI-style filler.
SUSPICIOUS_PHRASES = (
    "ma na celu", "mają na celu", "celem jest", "przełożyć się na", "takie podejście", "te działania",
    "co pokazuje", "co świadczy", "zgodność z regulacjami", "zgodności z regulacjami", "transformacj",
    "warto zauważyć", "nie ulega wątpliwości", "w dzisiejszym", "dynamicznie zmieniającym",
    "podsumowując", "rewolucj", "przełomow", "co ma ", "co mają ", "co obejmuje",
    # meta-commentary about the facts instead of writing for the reader
    "nie należy", "warto odróżnić", "należy odróżnić", "nie został więc", "ta informacja dotyczy",
)
TITLE_MAX_RECOMMENDED = 90
_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*")


# dataclass generuje m.in. konstruktor z zadeklarowanych pól; frozen blokuje przypisania do pól, slots
# ogranicza atrybuty.
@dataclass(slots=True)
class ValidatedArticle:
    sections: list[dict[str, Any]]
    lead_fact_ids: list[int]
    conclusion_fact_ids: list[int]
    used_fact_ids: set[int]
    referenced_source_ids: set[int]
    warnings: list[str] = field(default_factory=list)
    rejected_fact_ids: list[int] = field(default_factory=list)
    rejected_source_ids: list[int] = field(default_factory=list)


# Referencje briefu muszą należeć do przekazanych faktów; nieznane ID są odfiltrowywane i raportowane.
def validate_brief(brief: ArticleBrief, facts: list[FactInput]) -> tuple[ArticleBrief, list[str]]:
    known = {fact.id for fact in facts}
    warnings = []
    invalid = sorted({i for i in brief.required_facts + brief.optional_facts if i not in known})
    if invalid:
        warnings.append(f"Brief: usunięto nieistniejące ID faktów {invalid}")
    required = _unique([i for i in brief.required_facts if i in known])
    optional = _unique([i for i in brief.optional_facts if i in known and i not in required])
    plan = []
    for section in brief.section_plan:
        unknown = sorted(set(section.fact_ids) - known)
        if unknown:
            warnings.append(f"Brief: sekcja „{section.heading}” zawiera nieistniejące ID faktów {unknown}")
        plan.append(section.model_copy(update={"fact_ids": _unique([i for i in section.fact_ids if i in known])}))
    return brief.model_copy(update={"required_facts": required, "optional_facts": optional,
                                   "section_plan": plan}), warnings


# Sprawdzamy ID względem researchu i zbieramy ostrzeżenia; poprawny kształt JSON nie gwarantuje pokrycia
# twierdzeń w faktach.
def validate_writer_output(
    output: WriterOutput,
    facts: list[FactInput],
    source_ids: set[int],
    required_fact_ids: list[int],
    reference_texts: list[str],
) -> ValidatedArticle:
    facts_by_id = {fact.id: fact for fact in facts}
    rejected_facts: list[int] = []
    rejected_sources: list[int] = []

    def keep_facts(ids: list[int]) -> list[int]:
        valid = []
        for fact_id in _unique(ids):
            if fact_id in facts_by_id:
                valid.append(fact_id)
            else:
                rejected_facts.append(fact_id)
        return valid

    sections: list[dict[str, Any]] = []
    warnings: list[str] = []
    for section in output.sections:
        fact_ids = keep_facts(section.used_fact_ids)
        valid_sources = []
        for source_id in _unique(section.source_ids):
            if source_id in source_ids:
                valid_sources.append(source_id)
            else:
                rejected_sources.append(source_id)
        for fact_id in fact_ids:  # a section is backed by the sources of its facts
            for source_id in facts_by_id[fact_id].source_ids:
                if source_id in source_ids and source_id not in valid_sources:
                    valid_sources.append(source_id)
        if not fact_ids and not valid_sources:
            warnings.append(f"Sekcja „{section.heading.strip()}” nie wskazuje żadnego faktu ani źródła z researchu.")
        sections.append(
            {
                "heading": section.heading.strip().lstrip("#").strip(),
                "used_fact_ids": fact_ids,
                "source_ids": valid_sources,
            }
        )

    lead_ids = keep_facts(output.lead_fact_ids)
    conclusion_ids = keep_facts(output.conclusion_fact_ids)
    used = set(lead_ids) | set(conclusion_ids) | {i for s in sections for i in s["used_fact_ids"]}
    referenced_sources = {i for s in sections for i in s["source_ids"]} | {
        source_id for fact_id in used for source_id in facts_by_id[fact_id].source_ids if source_id in source_ids
    }

    if rejected_facts:
        warnings.append(f"Odrzucono ID faktów spoza researchu: {sorted(set(rejected_facts))}")
    if rejected_sources:
        warnings.append(f"Odrzucono ID źródeł spoza researchu: {sorted(set(rejected_sources))}")
    missing_required = [i for i in required_fact_ids if i not in used]
    if missing_required:
        warnings.append(f"Nie wykorzystano wymaganych faktów z briefu: {missing_required}")

    from app.services.article.readability import readability_issues
    from app.services.article.composition import compose_content
    warnings.extend(issue.reason for issue in readability_issues(output.lead, compose_content(output)))

    text = " ".join([output.title, output.lead, *(s.content for s in output.sections), output.conclusion])
    unsupported = unsupported_numbers(text, reference_texts)
    if unsupported:
        warnings.append(
            "Liczby bez pokrycia w faktach researchu (sprawdź ręcznie): " + ", ".join(unsupported)
        )
    if len(output.title) > TITLE_MAX_RECOMMENDED:
        warnings.append(f"Tytuł ma {len(output.title)} znaków (zalecane do {TITLE_MAX_RECOMMENDED}).")
    prose = "\n\n".join(without_fenced_code(t) for t in [output.lead, *(s.content for s in output.sections), output.conclusion])
    warnings.extend(editorial_warnings(output, prose))
    phrases = suspicious_phrases(output.title + "\n" + prose, reference_texts)
    if phrases:
        warnings.append(
            "Możliwe dopiski bez pokrycia w faktach (sprawdź ręcznie): " + ", ".join(f"„{p}”" for p in phrases)
        )
    if rejected_facts or rejected_sources:
        logger.warning("Writer referenced unknown facts=%s sources=%s", rejected_facts, rejected_sources)

    return ValidatedArticle(
        sections=sections,
        lead_fact_ids=lead_ids,
        conclusion_fact_ids=conclusion_ids,
        used_fact_ids=used,
        referenced_source_ids=referenced_sources,
        warnings=warnings,
        rejected_fact_ids=sorted(set(rejected_facts)),
        rejected_source_ids=sorted(set(rejected_sources)),
    )


def suspicious_phrases(text: str, reference_texts: list[str]) -> list[str]:
    lowered = text.lower()
    references = " ".join(reference_texts).lower()
    return [p for p in SUSPICIOUS_PHRASES if p in lowered and p not in references]


def unsupported_numbers(text: str, reference_texts: list[str]) -> list[str]:
    """Numbers present in the article but in none of the reference texts (facts, titles...)."""
    allowed = {_normalize_number(n) for ref in reference_texts for n in _NUMBER.findall(ref)}
    found = []
    for number in _NUMBER.findall(text):
        key = _normalize_number(number)
        if key not in allowed and key not in found and not _trivial(key):
            found.append(key)
    return found


def _normalize_number(number: str) -> str:
    # "3,5" == "3.5"; "20 000"/"20,000" thousands separators are rare in facts, keep simple.
    return number.replace(",", ".").rstrip(".")


def _trivial(number: str) -> bool:
    # Small integers are usually counting words in prose ("2 modele", "3 kroki"), not facts.
    return number.isdigit() and int(number) <= 3


def _unique(ids: list[int]) -> list[int]:
    return list(dict.fromkeys(ids))


_GENERIC_HEADINGS = {"wprowadzenie", "podsumowanie", "co się wydarzyło", "dlaczego to ważne",
                     "co to oznacza", "co dalej", "wnioski", "kontekst"}


def editorial_warnings(output: WriterOutput, prose: str) -> list[str]:
    warnings = []
    seen = set()
    for paragraph in re.split(r"\n\s*\n", prose):
        normalized = " ".join(paragraph.lower().split())
        if len(normalized) < 100:
            continue
        if normalized in seen:
            warnings.append("Powtórzony akapit: „" + paragraph.strip()[:90] + "…”.")
        seen.add(normalized)
    generic = [s.heading for s in output.sections if s.heading.strip().lower().lstrip('#').strip() in _GENERIC_HEADINGS]
    if len(generic) >= 2:
        warnings.append("Szablonowe nagłówki: " + ", ".join(generic) + ". Zastąp je konkretnymi pytaniami tego tematu.")
    for label, content in [("lead", output.lead), *((s.heading, s.content) for s in output.sections), ("zakończenie", output.conclusion)]:
        for block in fences(content):
            if not block.closed:
                warnings.append(f"Niezamknięty blok kodu w sekcji „{label}”.")
            if not block.language:
                warnings.append(f"Blok kodu bez języka w sekcji „{label}”; określ język lub użyj text.")
    return warnings


def banned_phrases_found(text: str, phrases: list[str]) -> list[str]:
    """Zakazane zwroty z profilu redakcji obecne w tekście (bez rozróżniania wielkości liter)."""
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase.strip() and phrase.lower() in lowered]


def enforce_internal_links(text: str, allowed: list[dict[str, str]] | None) -> tuple[str, list[str]]:
    """Linki do bloga spoza listy dozwolonych wpisów zamienia na sam tekst; linki zewnętrzne zostawia."""
    import re
    from urllib.parse import urlsplit
    allowed = allowed or []
    hosts = {urlsplit(link["url"]).netloc.lower() for link in allowed}
    urls = {link["url"] for link in allowed}
    removed: list[str] = []

    def replace(match: "re.Match[str]") -> str:
        label, url = match.group(1), match.group(2)
        if urlsplit(url).netloc.lower() in hosts and url not in urls:
            removed.append(url)
            return label
        return match.group(0)

    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", replace, text), removed

