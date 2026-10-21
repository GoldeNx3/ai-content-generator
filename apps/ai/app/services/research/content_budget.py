# Rola pliku: Przycina teksty źródeł do limitów znaków, aby łączny materiał przekazany LLM mieścił się w
# budżecie konfiguracji.

from app.services.markdown import fences

TRUNCATION_MARKER = "\n\n[... treść skrócona ...]"


# Slice zachowuje początek, rfind szuka końca akapitu lub zdania; na końcu dodajemy znacznik skrócenia.
def truncate_text(text: str, max_chars: int) -> str:
    """Keeps the beginning of the article (lead + key sections), cut on a paragraph/sentence boundary."""
    text = text.strip()
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    # Znacznik też trafia do promptu: rezerwujemy dla niego miejsce w limicie.
    # Przy bardzo małym budżecie zachowujemy sam początek tekstu bez znacznika.
    if max_chars <= len(TRUNCATION_MARKER):
        limit = max_chars
        for block in fences(text):
            if block.start < limit < block.end:
                limit = block.start
        return text[:limit].rstrip()
    content_limit = max_chars - len(TRUNCATION_MARKER)
    for block in fences(text):
        if block.start < content_limit < block.end:
            content_limit = block.start
    cut = text[:content_limit]
    for separator in ("\n\n", "\n", ". "):
        position = cut.rfind(separator)
        if position > content_limit * 0.6:
            cut = cut[: position + (1 if separator == ". " else 0)]
            break
    for block in fences(text):
        if block.start < len(cut) < block.end:
            cut = text[:block.start]
    return cut.rstrip() + TRUNCATION_MARKER


# Dokumenty przychodzą w kolejności priorytetu; dalsze materiały dostają tylko pozostały budżet.
def fit_documents(
    contents: list[str], per_document: list[int], total_budget: int
) -> list[str]:
    """Truncates each document to its own limit, then shrinks the tail so the sum fits total_budget.

    Documents are expected in priority order (original article first, then best-scored sources).
    """
    trimmed = [truncate_text(content, limit) for content, limit in zip(contents, per_document, strict=True)]
    remaining = total_budget
    result: list[str] = []
    for content in trimmed:
        if remaining <= 500:
            break
        if len(content) > remaining:
            content = truncate_text(content, remaining)
        result.append(content)
        remaining -= len(content)
    return result
