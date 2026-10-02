from app.schemas.classification import CandidateClassification

# Weights in percent (sum = 100). Integer math avoids float rounding surprises.
WEIGHTS = {
    "relevance": 40,
    "freshness": 20,
    "search_potential": 25,
    "commercial_potential": 15,
}


def compute_total_score(classification: CandidateClassification) -> int:
    """Weighted average of the four scores, rounded half up to an integer 0-100."""
    weighted = sum(getattr(classification, field) * weight for field, weight in WEIGHTS.items())
    return (weighted + 50) // 100
