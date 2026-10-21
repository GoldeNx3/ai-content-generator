# Rola pliku: Sprawdza twarde limity treści researchu, wliczając znacznik skrócenia.

import pytest

from app.services.research.content_budget import fit_documents, truncate_text


@pytest.mark.parametrize('limit', [0, 1, 10, 30, 600])
def test_truncation_marker_fits_inside_limit(limit: int) -> None:
    # Poprzedni kod przycinał tekst do limitu i dopiero potem doklejał znacznik.
    # Limit ma obejmować cały wynik, który zostanie wysłany do LLM.
    result = truncate_text('Długi akapit. ' * 100, limit)
    assert len(result) <= limit


def test_document_limits_include_marker_and_total_budget() -> None:
    documents = fit_documents(['a' * 2000, 'b' * 2000], [600, 600], 1150)
    assert len(documents) == 2
    assert all(len(document) <= 600 for document in documents)
    assert sum(map(len, documents)) <= 1150


def test_short_text_is_preserved() -> None:
    assert truncate_text('  Gotowy tekst.  ', 100) == 'Gotowy tekst.'
