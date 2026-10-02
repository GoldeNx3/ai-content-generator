TRUNCATION_MARKER = "\n\n[... treść skrócona ...]"


def truncate_text(text: str, max_chars: int) -> str:
    """Keeps the beginning of the article (lead + key sections), cut on a paragraph/sentence boundary."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for separator in ("\n\n", "\n", ". "):
        position = cut.rfind(separator)
        if position > max_chars * 0.6:
            cut = cut[: position + (1 if separator == ". " else 0)]
            break
    return cut.rstrip() + TRUNCATION_MARKER


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
