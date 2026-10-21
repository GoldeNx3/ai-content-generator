# Rola pliku: Instrukcje klasyfikatora i składanie wiadomości z danymi wpisu. Tekst promptu to dane
# przekazywane do LLM.

from datetime import UTC, datetime

from app.services.llm.base import CandidateInput

CLASSIFIER_SYSTEM_PROMPT = """\
Jesteś redaktorem prowadzącym polskiego portalu technologicznego. Portal pisze o:
AI, LLM, narzędziach AI, programowaniu, automatyzacji, nowych modelach, SaaS,
produktywności oraz technologiach powiązanych z AI.

Oceń, czy podany temat (news/artykuł ze źródła RSS) warto opisać na portalu.
Zwróć oceny w skali 0-100:
- relevance: dopasowanie do tematyki portalu,
- freshness: aktualność i "newsowość" tematu (świeży release/ogłoszenie = wysoko, temat evergreen lub stary = nisko),
- search_potential: potencjał ruchu z wyszukiwarek w Polsce (popularne marki, produkty, frazy),
- commercial_potential: potencjał komercyjny (afiliacja, narzędzia płatne, porównania, cenniki, B2B).

Wybierz jedną kategorię: news, guide, comparison, pricing, release, tool, other.
W polu reason podaj krótkie (1-2 zdania) uzasadnienie po polsku.
Nie podawaj łącznego wyniku - zostanie obliczony osobno."""


# f-string wstawia dane wpisu do szablonu; gotowy tekst jest wiadomością użytkownika dla klasyfikatora.
def build_user_prompt(candidate: CandidateInput, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    published = candidate.published_at.isoformat() if candidate.published_at else "nieznana"
    return (
        f"Aktualna data: {now.date().isoformat()}\n"
        f"Źródło: {candidate.source}\n"
        f"Data publikacji: {published}\n"
        f"Tytuł: {candidate.title}\n"
        f"Streszczenie: {candidate.summary or 'brak'}"
    )
