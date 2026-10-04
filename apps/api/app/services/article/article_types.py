# Rola pliku: Format redakcyjny niezależny od kategorii RSS oraz budżet długości.

from dataclasses import dataclass

from app.models import CandidateCategory
from app.schemas.article import ArticleFormat, ArticleLength, GenerateArticleRequest

# Editorial targets describe depth, not a conversion from fact count to prose.
LONG_TARGETS = {"news": 1000, "explainer": 1800, "case_study": 2200,
                "guide": 2500, "comparison": 2500}


@dataclass(frozen=True, slots=True)
class ArticleTypeGuide:
    max_words: int
    structure: str
    style: str

    def describe(self) -> str:
        return f"Podejście: {self.structure}\nStyl: {self.style}"


GUIDES = {
    ArticleFormat.NEWS: ArticleTypeGuide(
        1200, "Jedno wydarzenie, jego najważniejszy konkret i niezbędny kontekst.",
        "Krótka wiadomość. Najważniejsze na początku. Nie twórz obowiązkowych sekcji ani podsumowania.",
    ),
    ArticleFormat.EXPLAINER: ArticleTypeGuide(
        2500, "Wyjaśnij jedno pytanie czytelnika o produkt, zmianę lub technologię.",
        "Omówienie. Łącz fakty w wyjaśnienie; pomijaj katalog drugorzędnych funkcji.",
    ),
    ArticleFormat.CASE_STUDY: ArticleTypeGuide(
        3000, "Opowiedz o rzeczywistym problemie, decyzji, przeszkodach i rezultacie, jeśli są w researchu.",
        "Studium przypadku. Prowadź historię przez konkretne decyzje i kompromisy; nie udawaj instrukcji dla czytelnika.",
    ),
    ArticleFormat.GUIDE: ArticleTypeGuide(
        3500, "Odpowiedz, jak wykonać konkretne zadanie, używając wyłącznie udokumentowanych kroków.",
        "Poradnik. Numeruj tylko rzeczywiste kroki. Jeśli brakuje instrukcji, wyjaśnij ograniczenie zamiast je wymyślać.",
    ),
    ArticleFormat.COMPARISON: ArticleTypeGuide(
        3500, "Porównaj rozwiązania według wspólnego pytania i parametrów obecnych w researchu.",
        "Porównanie. Pokaż różnice i kompromisy; nie dopisuj rekomendacji bez pokrycia w materiale.",
    ),
}


def legacy_format(category: CandidateCategory | str) -> ArticleFormat:
    return {
        "news": ArticleFormat.NEWS, "guide": ArticleFormat.GUIDE,
        "comparison": ArticleFormat.COMPARISON,
    }.get(category, ArticleFormat.EXPLAINER)


def requested_format(request: GenerateArticleRequest) -> str:
    if request.article_format is not None:
        return request.article_format
    if request.article_type is not None:
        return legacy_format(request.article_type)
    return "auto"


def guide_for(article_format: ArticleFormat | CandidateCategory | str) -> ArticleTypeGuide:
    if article_format == "auto":
        return ArticleTypeGuide(
            3500, "Dobierz format do ukończonego researchu, niezależnie od kategorii RSS.",
            "Wybierz news, explainer, case_study, guide lub comparison. Poradnik tylko z instrukcjami; "
            "porównanie tylko z porównywalnymi danymi. Układ i nagłówki wynikają z tematu.",
        )
    return GUIDES.get(article_format) or GUIDES[legacy_format(article_format)]


def length_hint(article_format: str, length: ArticleLength, facts_count: int) -> str:
    normal = "Cel: news 500-900 słów, omówienie 1200-1800, case study 1500-2200, poradnik lub porównanie 1800-2500."
    preferences = {
        ArticleLength.AUTO: normal,
        ArticleLength.SHORT: "Zwięźle: wybierz sedno, zwykle do 400 słów; krótszy tekst jest poprawny.",
        ArticleLength.STANDARD: normal,
        ArticleLength.LONG: "Pogłębiony tekst. Cel: news 1000-1200 słów, omówienie 1800-2500, "
        "case study 2200-3000, poradnik lub porównanie 2500-3500. Rozwiń mechanizmy, przykłady, "
        "warunki użycia i ograniczenia ze źródeł; braki materiału zgłoś, zamiast je wymyślać.",
    }
    return preferences[length]


def resolve_length(
    article_type: ArticleFormat | CandidateCategory | str,
    length: ArticleLength,
    brief_words: int,
    facts_count: int,
) -> int:
    """Resolve the editorial target independently of the number of mandatory facts.

    facts_count is retained for callers using the previous interface.
    A target never authorizes inventing facts when evidence is insufficient.
    """
    target = brief_words
    if length == ArticleLength.SHORT:
        target = min(target, 400)
    elif length == ArticleLength.LONG:
        format_name = article_type if article_type in GUIDES else legacy_format(article_type)
        target = max(target, LONG_TARGETS[format_name])
    return min(target, guide_for(article_type).max_words)
