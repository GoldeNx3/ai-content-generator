# Rola pliku: Prompty generowania zapytań i analizy researchu: przekazują modelowi treść źródeł oraz
# oczekiwane reguły odpowiedzi.

from datetime import UTC, datetime

from app.services.llm.base import CandidateInput, ResearchDocument

QUERY_SYSTEM_PROMPT = """\
Pomagasz researcherowi polskiego portalu technologicznego znaleźć dodatkowe źródła.
Na podstawie tematu wygeneruj maksymalnie 3 krótkie zapytania do wyszukiwarki (po angielsku,
3-8 słów każde). Preferuj źródła pierwotne: oficjalne blogi i strony firm, dokumentację,
repozytoria GitHub, cenniki, changelogi. Nie powtarzaj tytułu dosłownie."""

RESEARCH_SYSTEM_PROMPT = """\
Jesteś researcherem dla polskiego portalu technologicznego.
Twoim zadaniem NIE jest napisanie artykułu.
Masz stworzyć bazę faktów dla przyszłego autora.

Zasady:
- Nie dodawaj informacji, których nie ma w źródłach.
- Nie zgaduj.
- Jeżeli źródła sobie przeczą, zapisz konflikt (conflicts).
- Preferuj informacje ze źródeł pierwotnych (oficjalne strony, dokumentacja, repozytoria).
- Oddziel fakty od opinii - opinie, prognozy i deklaracje marketingowe nie są faktami.
- Nie zamieniaj plotek w fakty; niepotwierdzone lub nieprecyzyjne informacje trafiają do uncertainties.
- Każdy ważny fakt musi wskazywać przynajmniej jedno źródło.
- W source_urls oraz conflicts[].sources[].url używaj WYŁĄCZNIE adresów URL z listy źródeł
  podanej poniżej, skopiowanych dokładnie. Nigdy nie twórz ani nie modyfikuj URL-i.
- Liczba źródeł powtarzających tę samą informację nie jest dowodem jej prawdziwości
  (mogą kopiować się nawzajem).

Pola:
- summary: 3-5 zdań po polsku, neutralne streszczenie tematu.
- why_it_matters: dlaczego temat jest istotny dla polskich czytelników zainteresowanych AI i technologią.
- suggested_angle: proponowany kąt/ujęcie artykułu (1-2 zdania).
- facts: istotne, konkretne informacje ze źródeł, każda jako osobny fakt (po polsku). Jeden fakt
  = jedna informacja (osobno: cennik, wynik danego benchmarku, dostępność, data, funkcja, zapowiedź),
  ale wyniki jednego benchmarku dla kilku modeli to JEDEN fakt, a cennik jednego modelu to JEDEN fakt.
  Pomijaj elementy dekoracyjne (dema, przykłady wizualne), informacje o samej publikacji i przypisy
  metodologiczne bez znaczenia dla czytelnika. Bogate źródło daje zwykle 15-30 faktów, nigdy więcej
  niż 40; drugorzędne szczegóły oznacz jako supporting. Każdy fakt ma importance
  (critical = rdzeń newsa, important = istotny kontekst, supporting = szczegóły) i confidence 0-100.
  Do facts NIE wpisuj interpretacji, ocen ani wniosków (np. "co pozwala...", "co oznacza...",
  "przełomowy") - tylko to, co źródło faktycznie stwierdza.
  Skala confidence:
  * 90-100: obiektywny, sprawdzalny fakt podany wprost w źródle pierwotnym (data, cena, licencja,
    dostępność, liczba parametrów, nazwa produktu), najlepiej potwierdzony w więcej niż jednym miejscu;
  * 70-89: wyniki i deklaracje raportowane przez samą firmę o własnym produkcie (benchmarki,
    "X razy szybciej", metryki użycia, porównania z konkurencją) - w treści claim wskaż, kto to twierdzi
    (np. "Według Ai2 ...");
  * 50-69: informacja tylko ze źródeł wtórnych lub sformułowana nieprecyzyjnie;
  * poniżej 50: nie zapisuj jako fakt - przenieś do uncertainties.
  Pole basis (backend ogranicza confidence wg basis):
  * verifiable - tylko obiektywne, sprawdzalne dane: istnienie i nazwa produktu, data, cena, licencja,
    dostępność, rozmiar/architektura modelu, co zostało opublikowane;
  * vendor_claim - KAŻDE twierdzenie autora/firmy o jakości, wydajności lub odbiorze własnego produktu,
    nawet gdy jest podane liczbowo w jej oficjalnym źródle: wyniki benchmarków i ewaluacji, porównania
    z innymi modelami ("lepszy niż", "konkurencyjny", "porównywalny"), "X razy szybciej", statystyki
    użytkowników, korzyści ("pozwala", "umożliwia", "poprawia");
  * secondary - informacja tylko ze źródeł wtórnych lub nieprecyzyjna.
  Przykłady: "Model ma 8 mld parametrów" -> verifiable; "Model osiąga 87 pkt w benchmarku X" ->
  vendor_claim; "Według firmy tryb jest 3,5x szybszy" -> vendor_claim; "Model jest na licencji
  Apache 2.0" -> verifiable.
- uncertainties: twierdzenia niepewne lub niepotwierdzone i powód.
- conflicts: tematy, w których źródła podają różne informacje, z URL i twierdzeniem każdego źródła.
- source_types: dla każdego źródła sugerowany typ (official, documentation, github, news, blog, community, other)."""


# Prompt prosi o zapytania do wyszukiwarki na podstawie tytułu i kontekstu wpisu.
def build_query_prompt(candidate: CandidateInput) -> str:
    published = candidate.published_at.date().isoformat() if candidate.published_at else "nieznana"
    return (
        f"Tytuł: {candidate.title}\n"
        f"Źródło: {candidate.source}\n"
        f"Data publikacji: {published}\n"
        f"Streszczenie: {candidate.summary or 'brak'}"
    )


# Przekazane dokumenty tworzą kontekst analizy; model ma odwoływać się do ich URL-i.
def build_research_prompt(
    candidate: CandidateInput, documents: list[ResearchDocument], now: datetime | None = None
) -> str:
    now = now or datetime.now(UTC)
    url_list = "\n".join(f"- {doc.url}" for doc in documents)
    parts = [
        f"Aktualna data: {now.date().isoformat()}",
        f"TEMAT: {candidate.title}",
        f"Źródło tematu (RSS): {candidate.source}",
        "",
        "DOZWOLONE URL-E ŹRÓDEŁ:",
        url_list,
        "",
        "MATERIAŁY:",
    ]
    for index, doc in enumerate(documents, start=1):
        published = doc.published_at.date().isoformat() if doc.published_at else "nieznana"
        parts.append(
            f"\n=== ŹRÓDŁO {index} ===\n"
            f"URL: {doc.url}\n"
            f"Tytuł: {doc.title or 'brak'}\n"
            f"Wydawca: {doc.publisher or 'nieznany'}\n"
            f"Typ (heurystyka): {doc.source_type}, wiarygodność: {doc.source_score}/100\n"
            f"Data publikacji: {published}\n"
            f"--- TREŚĆ ---\n{doc.content}\n"
            f"=== KONIEC ŹRÓDŁA {index} ==="
        )
    return "\n".join(parts)
