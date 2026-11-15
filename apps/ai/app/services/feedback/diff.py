# Rola pliku: Wycina z tekstu AI i wersji poprawionej przez redaktora tylko zmienione akapity (przed → po),
# żeby analiza poprawek nie płaciła za niezmienioną treść.

import difflib

MAX_PASSAGES = 30
MAX_CHARS = 1500


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]


def changed_passages(original: str, edited: str) -> list[dict[str, str]]:
    before, after = _paragraphs(original), _paragraphs(edited)
    passages: list[dict[str, str]] = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        passages.append({"before": "\n\n".join(before[a1:a2])[:MAX_CHARS], "after": "\n\n".join(after[b1:b2])[:MAX_CHARS]})
        if len(passages) >= MAX_PASSAGES:
            break
    return passages
