# Rola pliku: Deterministyczny test oryginalności QA: udział 8-gramów słów artykułu wspólnych z treścią źródła.
# Pomija bloki kodu i cytaty (> ...), bo dosłowne przytoczenie jest tam zamierzone. Darmowy, bez wywołań AI.
import re

from app.schemas.qa import QAIssueOutput

N = 8
WORD = re.compile(r"\w+", re.UNICODE)
FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.S | re.M)


def _grams(text: str) -> set[tuple[str, ...]]:
    words = WORD.findall(text.lower())
    return {tuple(words[i:i + N]) for i in range(len(words) - N + 1)}


def _paragraphs(content: str) -> list[tuple[str | None, str]]:
    """Akapity prozy z nagłówkiem sekcji; kod i cytaty pominięte."""
    heading: str | None = None
    found: list[tuple[str | None, str]] = []
    prose = FENCE.sub("\n\n", content)
    for block in re.split(r"\n\s*\n", prose):
        stripped = block.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            continue
        found.append((heading, stripped))
    return found


def source_overlap_issues(snapshot: dict, max_ratio: float) -> list[QAIssueOutput]:
    article = snapshot["article"]
    paragraphs = [(None, article.get("lead") or ""), *_paragraphs(article.get("content") or "")]
    article_grams = set().union(*(_grams(text) for _, text in paragraphs))
    if not article_grams:
        return []
    issues: list[QAIssueOutput] = []
    for source in snapshot.get("research", {}).get("sources", []):
        source_grams = _grams(source.get("content") or "")
        shared = article_grams & source_grams
        ratio = len(shared) / len(article_grams)
        if ratio <= max_ratio:
            continue
        heading, excerpt = max(paragraphs, key=lambda item: len(_grams(item[1]) & source_grams))
        issues.append(QAIssueOutput(type="too_close_to_source", severity="warning", excerpt=excerpt,
            reason=f"Oryginalność: {round(ratio * 100)}% fraz artykułu (8 słów z rzędu) pochodzi dosłownie ze SOURCE #{source['id']} "
                   f"(dopuszczalne {round(max_ratio * 100)}%).",
            suggestion="Opowiedz ten fragment własnymi słowami i w innej kolejności myśli. Zachowaj fakty, nie dopisuj nowych.",
            section_heading=heading, fact_ids=[], source_ids=[source["id"]], auto_fixable=True))
    return issues
