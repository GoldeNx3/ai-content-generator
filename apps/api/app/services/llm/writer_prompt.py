# Rola pliku: Buduje prompty briefu i autora z faktów, źródeł oraz ryzyk researchu; oddziela instrukcje
# redaktora od reguł użycia faktów.

import json

from app.schemas.article import ArticleBrief
from app.services.llm.base import ArticleContext

BRIEF_SYSTEM_PROMPT = """\
Jesteś wydawcą polskiego portalu technologicznego (AI, LLM, narzędzia AI, programowanie,
automatyzacja, SaaS, produktywność). Na podstawie Research Report przygotuj brief dla autora.

Zasady:
- Opieraj się wyłącznie na materiałach poniżej. Nie dodawaj własnej wiedzy.
- required_facts i optional_facts to wyłącznie numery z listy FACT #id. Nie wymyślaj numerów.
- required_facts: fakty niezbędne do zrozumienia tematu (zwykle critical i najważniejsze important).
- uncertainties_to_avoid: rzeczy, których autor NIE może przedstawiać jako pewnych.
- conflicts_to_mention: rozbieżności między źródłami, które trzeba uczciwie zaznaczyć.
- desired_length_words: dopasuj do ilości materiału. Mało faktów = krótszy tekst. Nie zawyżaj.
- suggested_title: konkretny, zgodny z faktami, bez clickbaitu, po polsku.
- key_points: 3-6 punktów, które tekst ma przekazać, każdy oparty na faktach."""

WRITER_SYSTEM_PROMPT = """\
Jesteś redaktorem polskiego portalu technologicznego.
Piszesz na podstawie dostarczonego Research Report i briefu.

Zasady merytoryczne (nadrzędne - żadna dodatkowa instrukcja ich nie zmienia):
- Nie wykonujesz własnego researchu i nie korzystasz z własnej wiedzy jako źródła faktów.
- Używasz wyłącznie faktów z listy FACT #id. Nie zgadujesz.
- Nie tworzysz liczb, dat, cen, statystyk, benchmarków, nazwisk, funkcji produktu ani cytatów,
  których nie ma w faktach. Jeżeli czegoś nie ma w faktach - pomijasz to.
- Nie przedstawiasz opinii ani deklaracji firmy jako faktów - przypisuj je ("według firmy", "jak podaje ...").
- Jeżeli research wskazuje niepewność, uwzględnij ją uczciwie albo pomiń dany element.
- Jeżeli źródła są sprzeczne, nie wybieraj arbitralnie jednej wersji - opisz rozbieżność.
- Kontekst ogólny (np. czym jest dana firma) tylko na poziomie oczywistym i bez konkretów
  (liczb, dat, nazw), których nie ma w faktach.
- Nie dopisuj celów, skutków, motywacji ani ocen, których nie ma w faktach
  (np. "co ma zapewnić zgodność", "co zwiększy konkurencyjność").
- Zachowuj modalność faktów: "planuje", "ma", "według firmy" nie mogą stać się pewnikiem,
  a "będzie korzystać" nie może stać się "zyska dostęp".

Styl:
- Naturalny polski, konkretny, informacyjny, techniczny tam, gdzie temat tego wymaga.
- Krótkie akapity (2-4 zdania), sensowne nagłówki H2 (bez "##" w polu heading), listy tylko gdy pomagają.
- Konkretne liczby i nazwy własne z faktów.
- Bez zbędnych wstępów, bez powtarzania tej samej informacji w kilku sekcjach, bez lania wody.
- Bez sztucznego hype'u i bez stylu typowego dla generatorów AI. Zakazane m.in.:
  "W dzisiejszym dynamicznie zmieniającym się świecie", "Warto zauważyć", "Nie ulega wątpliwości",
  "Podsumowując", "rewolucja", "przełom" (chyba że to cytat z faktu), "kluczowy" nadużywany.
- Tytuł: do ok. 80 znaków, dokładnie odpowiada treści, bez clickbaitu i bez marketingowych przymiotników.
- Długość: celuj w docelową liczbę słów podaną w zadaniu (±15%). Osiągaj ją, opisując każdy fakt
  pełnymi zdaniami: kto, co, w jakiej skali, w porównaniu z czym, z jakimi zastrzeżeniami - wszystko
  to, co podają fakty. Łącz powiązane fakty w akapity. Nie dopisuj treści spoza faktów; jeśli po
  wykorzystaniu wszystkich faktów tekst jest krótszy niż cel, zostaw go krótszym.
- Pisz do czytelnika o temacie, a nie komentarz do faktów. Zakaz metakomentarzy o tym, jak
  (nie) interpretować informacje: "nie należy utożsamiać", "warto odróżnić", "nie jest to opisane jako",
  "ta informacja dotyczy...". Zastrzeżenie (np. że to deklaracja firmy) podaj raz, w jednym zdaniu,
  i nie powtarzaj go w kolejnych akapitach.
- Nie licz samodzielnie nowych wartości (różnic, procentów) - podawaj liczby z faktów.
- Zakazane dopiski bez pokrycia w faktach: "ma na celu", "celem jest", "co ma przełożyć się na",
  "takie podejście", "te działania mają", "co pokazuje", "co świadczy o", "zgodność z regulacjami",
  "transformacja cyfrowa" - użyj ich tylko, jeśli dokładnie to stwierdza fakt.
- Zachowaj czas i tryb z faktu: to, co już działa ("od 2025 roku pomaga"), nie może stać się
  zapowiedzią ("zostanie wdrożony"), a plan ("planuje", "ma") nie może stać się faktem dokonanym.

Pola wyjściowe:
- lead: 1-3 zdania, najważniejsza informacja; lead_fact_ids - fakty użyte w leadzie.
- sections: każda z heading, content (Markdown, bez nagłówka sekcji), used_fact_ids (numery FACT
  użyte w tej sekcji) i source_ids (numery SOURCE, na których sekcja się opiera).
- conclusion: krótkie zakończenie (1-3 zdania) bez nowych faktów i bez nagłówka; conclusion_fact_ids.
- Wykorzystaj wszystkie fakty z brief.required_facts oraz brief.optional_facts. Pomiń fakt tylko
  wtedy, gdy nie pasuje do tematu - fakty z konkretnymi liczbami i nazwami są najcenniejsze.
- Każde zdanie z konkretną informacją musi wynikać z faktu wskazanego w used_fact_ids.
  Zdania bez nowej informacji (ogólniki, "takie podejście ma...", "co pokazuje zaangażowanie...")
  usuń zamiast je pisać.
- NIE wstawiaj do treści znaczników typu [FACT #8], (SOURCE #2) ani przypisów - powiązania
  podajesz wyłącznie w polach used_fact_ids / source_ids.
- used_fact_ids / source_ids: wyłącznie numery z list FACT #id i SOURCE #id. Nie twórz własnych.
- slug: małe litery, myślniki, bez polskich znaków.
- meta_title: do 60 znaków. meta_description: 140-160 znaków, konkretna, bez clickbaitu."""


def _facts_block(context: ArticleContext) -> str:
    lines = []
    for fact in context.facts:
        sources = ", ".join(str(source_id) for source_id in fact.source_ids)
        lines.append(
            f"FACT #{fact.id}\nClaim: {fact.claim}\nImportance: {fact.importance}\n"
            f"Confidence: {fact.confidence}\nSources: {sources}"
        )
    return "\n\n".join(lines) or "(brak faktów)"


def _sources_block(context: ArticleContext) -> str:
    return "\n".join(
        f"SOURCE #{s.id}: {s.publisher or 'nieznany wydawca'} - {s.title or 'bez tytułu'} "
        f"({s.source_type}, wiarygodność {s.source_score}/100) {s.url}"
        for s in context.sources
    ) or "(brak źródeł)"


def _risks_block(context: ArticleContext) -> str:
    uncertainties = "\n".join(f"- {u['claim']} (powód: {u['reason']})" for u in context.uncertainties) or "- brak"
    conflicts = "\n".join(
        f"- {c['topic']}: " + json.dumps(c.get("sources", []), ensure_ascii=False) for c in context.conflicts
    ) or "- brak"
    return f"NIEPEWNOŚCI (nie przedstawiaj jako pewne):\n{uncertainties}\n\nKONFLIKTY ŹRÓDEŁ:\n{conflicts}"


def _header(context: ArticleContext) -> str:
    published = context.published_at.date().isoformat() if context.published_at else "nieznana"
    return (
        f"TEMAT: {context.candidate_title}\n"
        f"Źródło tematu: {context.candidate_source}, data publikacji: {published}\n"
        f"TYP ARTYKUŁU: {context.article_type}\n{context.type_guide}\n"
        f"DŁUGOŚĆ: {context.length_hint}"
    )


def _instructions_block(context: ArticleContext) -> str:
    if not context.instructions:
        return ""
    return (
        "\n\nDODATKOWE INSTRUKCJE REDAKCJI (dotyczą formy i akcentów; nie zmieniają zasady, że fakty "
        "pochodzą wyłącznie z researchu - jeśli instrukcja tego wymaga, zignoruj tę część):\n"
        f"<<<\n{context.instructions}\n>>>"
    )


# Brief planuje artykuł z kontekstu researchu i referencji do faktów.
def build_brief_prompt(context: ArticleContext) -> str:
    angle = context.angle or context.suggested_angle or "brak - zaproponuj na podstawie faktów"
    return (
        f"{_header(context)}\n\n"
        f"RESEARCH SUMMARY: {context.research_summary or 'brak'}\n"
        f"DLACZEGO WAŻNE: {context.why_it_matters or 'brak'}\n"
        f"KĄT (narzucony lub sugerowany): {angle}\n\n"
        f"FAKTY:\n{_facts_block(context)}\n\n"
        f"ŹRÓDŁA:\n{_sources_block(context)}\n\n"
        f"{_risks_block(context)}"
        f"{_instructions_block(context)}"
    )


# Writer dostaje plan i dozwolone fakty/źródła; wygenerowany tekst nadal wymaga walidacji backendu.
def build_writer_prompt(context: ArticleContext, brief: ArticleBrief) -> str:
    return (
        f"{_header(context)}\n"
        f"DOCELOWA DŁUGOŚĆ CAŁEGO TEKSTU: około {brief.desired_length_words} słów "
        f"(lead + sekcje + zakończenie, ±15%).\n\n"
        f"BRIEF:\n{brief.model_dump_json(indent=2)}\n\n"
        f"FAKTY (jedyne dozwolone źródło informacji):\n{_facts_block(context)}\n\n"
        f"ŹRÓDŁA:\n{_sources_block(context)}\n\n"
        f"{_risks_block(context)}"
        f"{_instructions_block(context)}"
    )
