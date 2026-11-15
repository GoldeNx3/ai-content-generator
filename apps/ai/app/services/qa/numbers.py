# Rola pliku: Deterministyczna kontrola liczb QA: kwoty, procenty, duże liczby i daty z artykułu muszą występować
# (po normalizacji zapisu) w faktach, treści źródeł albo „Naszym zdaniu”. Darmowa, bez wywołań AI.
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.schemas.qa import QAIssueOutput

MAX_ISSUES = 10
FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+", re.M)
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ0-9„\"])")
NUMBER = re.compile(
    r"(?P<pre>[$€£])?\s?"
    r"(?P<num>\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?P<post>\s?(?:%|procent\w*|mln|mld|tys\.?|milion\w*|miliard\w*|tysi\w*|million|billion|thousand|zł|pln|usd|eur|€)(?!\w))?",
    re.I,
)
MULTIPLIERS = (("mld", 10**9), ("miliard", 10**9), ("billion", 10**9), ("mln", 10**6), ("milion", 10**6),
               ("million", 10**6), ("tys", 10**3), ("thousand", 10**3))
NOT_NAMES = {"W", "Ponad", "Prawie", "Około", "Do", "Od", "Po", "Za", "Na", "O", "Z", "I", "A", "To", "Ma", "Jest",
             "Tylko", "Aż", "Nawet", "Blisko", "Niemal", "Ok", "Co", "Przez", "Dla", "Mamy", "Ma"}


def _value(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(" ", "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


def _multiplier(post: str) -> int:
    post = post.strip().lower()
    return next((factor for prefix, factor in MULTIPLIERS if post.startswith(prefix)), 1)


def _known(texts: list[str]) -> tuple[set[Decimal], set[str]]:
    values: set[Decimal] = set()
    dates: set[str] = set()
    for text in texts:
        dates.update(ISO_DATE.findall(text))
        for match in NUMBER.finditer(ISO_DATE.sub(" ", text)):
            value = _value(match["num"])
            if value is not None:
                values.update({value, value * _multiplier(match["post"] or "")})
    return values, dates


def _is_version(text: str, start: int, has_unit: bool) -> bool:
    before = text[:start]
    if before[-1:].isalpha() or (before[-1:] == "-" and before[-2:-1].isalpha()):
        return True
    word = re.search(r"([A-Za-z][A-Za-z0-9]*) $", before)
    return not has_unit and word is not None and word[1][0].isupper() and word[1] not in NOT_NAMES


def _claims(sentence: str) -> list[str]:
    found = [f"{d}" for d in ISO_DATE.findall(sentence)]
    text = ISO_DATE.sub(" ", sentence)
    recent = {date.today().year, date.today().year - 1}
    for match in NUMBER.finditer(text):
        value = _value(match["num"])
        has_unit = bool(match["pre"] or match["post"])
        if value is None or _is_version(text, match.start("num") - (1 if match["pre"] else 0), has_unit):
            continue
        if not has_unit and (value < 10 or (value == value.to_integral_value() and int(value) in recent)):
            continue
        found.append(match.group(0).strip())
    return found


def _confirmed(claim: str, values: set[Decimal], dates: set[str]) -> bool:
    if ISO_DATE.fullmatch(claim):
        return claim in dates
    match = NUMBER.search(claim)
    value = _value(match["num"]) if match else None
    return value is not None and (value in values or value * _multiplier(match["post"] or "") in values)


def _paragraphs(lead: str, content: str) -> list[tuple[str | None, str]]:
    found: list[tuple[str | None, str]] = [(None, lead)]
    heading: str | None = None
    prose = LIST_MARKER.sub("", URL.sub(" ", LINK.sub(r"\1", INLINE_CODE.sub(" ", FENCE.sub("\n\n", content)))))
    for block in re.split(r"\n\s*\n", prose):
        stripped = block.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            continue
        found.append((heading, stripped))
    return found


def unverified_number_issues(snapshot: dict) -> list[QAIssueOutput]:
    research = snapshot.get("research", {})
    texts = [fact.get("claim") or "" for fact in research.get("facts", [])]
    texts += [source.get("content") or "" for source in research.get("sources", [])]
    texts.append((snapshot.get("brief") or {}).get("editor_take") or "")
    values, dates = _known(texts)
    article = snapshot["article"]
    issues: list[QAIssueOutput] = []
    for heading, paragraph in _paragraphs(article.get("lead") or "", article.get("content") or ""):
        for sentence in SENTENCE.split(paragraph):
            missing = [claim for claim in _claims(sentence) if not _confirmed(claim, values, dates)]
            if not missing:
                continue
            issues.append(QAIssueOutput(type="unverified_number", severity="warning", excerpt=sentence.strip(),
                reason="Liczby bez potwierdzenia w faktach i źródłach: " + ", ".join(dict.fromkeys(missing)) + ".",
                suggestion="Sprawdź wartość w researchu: popraw ją na wartość z faktów albo usuń, jeśli źródła jej nie podają.",
                section_heading=heading, fact_ids=[], source_ids=[], auto_fixable=True))
            if len(issues) >= MAX_ISSUES:
                return issues
    return issues
