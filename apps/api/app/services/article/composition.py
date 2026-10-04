# Rola pliku: Czyści wynik writera, tworzy slug i składa sekcje w Markdown. Tu powstaje tekst zapisywany
# jako content.

import re
import unicodedata

from app.schemas.article import WriterOutput
from app.services.markdown import transform_prose, without_fenced_code

META_TITLE_MAX = 70
META_DESCRIPTION_MAX = 170

# Writers sometimes leak inline references ("[FACT #8]", "(FACT #11, #12)", "[SOURCE #2]").
_MARKER = re.compile(r"\s*[\[(]\s*(?:FACT|SOURCE|ŹRÓDŁO|FAKT)[^\])]*[\])]", re.IGNORECASE)
_MARKER_FACT_IDS = re.compile(r"#?(\d+)")

_POLISH = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
_MARKDOWN_NOISE = re.compile(r"[#*_>`\[\]()|]|https?://\S+")
_WORD = re.compile(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ][\w\-ąćęłńóśźżĄĆĘŁŃÓŚŹŻ.,%]*")


# Usuwamy techniczne znaczniki z tekstu, ale zwracamy znalezione ID faktów, aby zachować referencje.
def strip_markers(text: str) -> tuple[str, list[int]]:
    """Removes inline FACT/SOURCE markers, returning clean text and the fact ids they named."""
    fact_ids: list[int] = []
    def clean(prose):
        for marker in _MARKER.findall(prose):
            if "fact" in marker.lower() or "fakt" in marker.lower():
                fact_ids.extend(int(n) for n in _MARKER_FACT_IDS.findall(marker))
        return _MARKER.sub("", prose)
    return transform_prose(text, clean), fact_ids


# Kopie sekcji łączą referencje ze structured output i znaczniki znalezione w tekście; wynik jest nowym
# obiektem.
def sanitize_output(output: WriterOutput) -> WriterOutput:
    """Strips leaked markers; fact ids named in them are merged into the structured references."""
    lead, lead_ids = strip_markers(output.lead)
    conclusion, conclusion_ids = strip_markers(output.conclusion)
    sections = []
    for section in output.sections:
        content, ids = strip_markers(section.content)
        sections.append(
            section.model_copy(update={"content": content, "used_fact_ids": [*section.used_fact_ids, *ids]})
        )
    return output.model_copy(
        update={
            "title": strip_markers(output.title)[0],
            "lead": lead,
            "lead_fact_ids": [*output.lead_fact_ids, *lead_ids],
            "conclusion": conclusion,
            "conclusion_fact_ids": [*output.conclusion_fact_ids, *conclusion_ids],
            "sections": sections,
        }
    )


# Normalizacja Unicode i zamiana polskich znaków tworzą fragment URL z małych liter, cyfr i myślników.
def slugify(text: str, max_length: int = 120) -> str:
    text = unicodedata.normalize("NFKD", text.translate(_POLISH)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "artykul"


def strip_heading_marks(heading: str) -> str:
    return heading.strip().lstrip("#").strip()


# Tytuł i lead mają osobne pola; content zawiera sekcje z nagłówkami H2 i opcjonalne zakończenie.
def compose_content(output: WriterOutput) -> str:
    """Markdown body: H2 sections + conclusion. Title and lead are stored separately."""
    parts = []
    for section in output.sections:
        parts.append(f"## {strip_heading_marks(section.heading)}\n\n{section.content.strip()}")
    if output.conclusion.strip():
        parts.append(output.conclusion.strip())
    return "\n\n".join(parts).strip() + "\n"


# *texts zbiera dowolną liczbę tekstów; sum sumuje wyniki generatora po usunięciu składni Markdown.
def count_words(*texts: str) -> int:
    return sum(len(_WORD.findall(_MARKDOWN_NOISE.sub(" ", without_fenced_code(text)))) for text in texts)


# Words that must not end a truncated title/description ("... współpracę z").
_DANGLING = {"i", "a", "o", "u", "w", "z", "ze", "we", "na", "do", "od", "po", "za", "dla", "oraz", "lub",
             "ale", "że", "to", "the", "and", "of", "for", "to", "in", "with"}


# Skracamy do pełnych słów i usuwamy końcowe spójniki/przyimki, aby tytuł nie urwał się np. na „z”.
def trim_text(text: str, max_length: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    words = text[:max_length].rsplit(" ", 1)[0].split(" ")
    while len(words) > 1 and (words[-1].lower().strip(",;:-–") in _DANGLING or not words[-1].strip(",;:-–")):
        words.pop()
    return " ".join(words).rstrip(",;:-–")
