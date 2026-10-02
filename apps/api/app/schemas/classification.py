from pydantic import BaseModel, Field

from app.models.enums import CandidateCategory


class CandidateClassification(BaseModel):
    """Structured output expected from the LLM. total_score is computed by the backend."""

    relevance: int = Field(ge=0, le=100)
    freshness: int = Field(ge=0, le=100)
    search_potential: int = Field(ge=0, le=100)
    commercial_potential: int = Field(ge=0, le=100)
    category: CandidateCategory
    reason: str

class ClassifyBatchResult(BaseModel):
    processed: int = 0
    classified: int = 0
    errors: int = 0
