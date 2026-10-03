# Rola pliku: Testy modułu scoring: scenariusze poprawnego działania i błędów. Funkcje test_* odkrywa i
# uruchamia pytest.

import pytest
from pydantic import ValidationError

from app.models import CandidateCategory
from app.schemas.classification import CandidateClassification
from app.services.scoring import compute_total_score


def classification(relevance: int, freshness: int, search: int, commercial: int) -> CandidateClassification:
    return CandidateClassification(
        relevance=relevance,
        freshness=freshness,
        search_potential=search,
        commercial_potential=commercial,
        category=CandidateCategory.NEWS,
        reason="test",
    )


# parametrize uruchamia ten sam test dla wielu zestawów danych, zamiast powielać jego kod.
@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ((100, 100, 100, 100), 100),
        ((0, 0, 0, 0), 0),
        ((90, 80, 70, 60), 79),  # 36 + 16 + 17.5 + 9 = 78.5 -> 79 (half up)
        ((50, 100, 0, 0), 40),
        ((95, 90, 85, 40), 83),  # 38 + 18 + 21.25 + 6 = 83.25 -> 83
    ],
)
def test_total_score(scores: tuple[int, int, int, int], expected: int) -> None:
    assert compute_total_score(classification(*scores)) == expected


@pytest.mark.parametrize("bad_value", [-1, 101])
def test_scores_must_be_between_0_and_100(bad_value: int) -> None:
    with pytest.raises(ValidationError):
        classification(bad_value, 50, 50, 50)


def test_unknown_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CandidateClassification.model_validate(
            {
                "relevance": 1,
                "freshness": 1,
                "search_potential": 1,
                "commercial_potential": 1,
                "category": "gossip",
                "reason": "x",
            }
        )
