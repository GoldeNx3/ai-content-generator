from dataclasses import dataclass

from app.models import CandidateCategory
from app.schemas.article import ArticleLength

# Rough number of words one granular research fact can support without padding.
WORDS_PER_FACT = 45
BASE_WORDS = 150
# Below this share of the target length the draft gets a review warning.
SHORT_DRAFT_RATIO = 0.6


@dataclass(frozen=True, slots=True)
class ArticleTypeGuide:
    min_words: int
    max_words: int
    structure: str
    style: str

    def describe(self) -> str:
        return f"Struktura: {self.structure}\nStyl: {self.style}"


GUIDES: dict[CandidateCategory, ArticleTypeGuide] = {
    CandidateCategory.NEWS: ArticleTypeGuide(
        600, 1200,
        "Lead -> Co się wydarzyło -> Najważniejsze informacje -> Dlaczego to ważne -> Co dalej "
        "(sekcję 'Co dalej' pomiń, jeśli research nic o tym nie mówi).",
        "Newsowy, rzeczowy, najważniejsze na początku (odwrócona piramida).",
    ),
    CandidateCategory.RELEASE: ArticleTypeGuide(
        600, 1400,
        "Lead -> Co zostało wydane -> Najważniejsze zmiany i możliwości -> Dostępność / dla kogo -> Kontekst.",
        "Konkretny, techniczny, z nazwami funkcji i wersji z faktów.",
    ),
    CandidateCategory.GUIDE: ArticleTypeGuide(
        1200, 2500,
        "Lead -> Czego dotyczy -> Wymagania -> Kroki / sposób użycia -> Ograniczenia -> Podsumowanie praktyczne.",
        "Poradnikowy, praktyczny, kroki numerowane tylko tam, gdzie wynikają z faktów.",
    ),
    CandidateCategory.COMPARISON: ArticleTypeGuide(
        1500, 2500,
        "Lead -> Co porównujemy -> Różnice w kluczowych obszarach -> Dla kogo które rozwiązanie -> Wnioski.",
        "Analityczny, neutralny; porównuj tylko parametry obecne w faktach.",
    ),
    CandidateCategory.PRICING: ArticleTypeGuide(
        500, 1200,
        "Lead -> Ile kosztuje / co się zmienia -> Szczegóły planów -> Kogo dotyczy -> Kontekst.",
        "Konkretny; każda cena i limit wyłącznie z faktów.",
    ),
    CandidateCategory.TOOL: ArticleTypeGuide(
        700, 1500,
        "Lead -> Czym jest narzędzie -> Najważniejsze funkcje -> Dla kogo -> Ograniczenia i dostępność.",
        "Praktyczny, z perspektywy użytkownika.",
    ),
    CandidateCategory.OTHER: ArticleTypeGuide(
        500, 1200,
        "Lead -> 2-4 sekcje porządkujące temat -> krótkie zakończenie.",
        "Informacyjny, rzeczowy.",
    ),
}

LENGTH_FRACTIONS = {
    ArticleLength.SHORT: 0.0,
    ArticleLength.STANDARD: 0.5,
    ArticleLength.LONG: 1.0,
}


def guide_for(article_type: CandidateCategory) -> ArticleTypeGuide:
    return GUIDES[article_type]


def facts_word_cap(facts_count: int) -> int:
    return BASE_WORDS + WORDS_PER_FACT * facts_count


def length_hint(article_type: CandidateCategory, length: ArticleLength, facts_count: int) -> str:
    guide = guide_for(article_type)
    cap = facts_word_cap(facts_count)
    if length == ArticleLength.AUTO:
        target = f"preferowane {guide.min_words}-{guide.max_words} słów"
    else:
        words = int(guide.min_words + (guide.max_words - guide.min_words) * LENGTH_FRACTIONS[length])
        target = f"około {words} słów"
    return f"{target}; materiał ({facts_count} faktów) wystarcza na ok. {cap} słów."


def resolve_length(
    article_type: CandidateCategory, length: ArticleLength, brief_words: int, facts_count: int
) -> int:
    """Backend decides the final target: type range, user choice, and what the facts can support."""
    guide = guide_for(article_type)
    if length == ArticleLength.AUTO:
        target = min(max(brief_words, guide.min_words), guide.max_words)
    else:
        target = int(guide.min_words + (guide.max_words - guide.min_words) * LENGTH_FRACTIONS[length])
    return min(target, facts_word_cap(facts_count))
