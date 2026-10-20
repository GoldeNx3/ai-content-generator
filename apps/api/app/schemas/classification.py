# Rola pliku: Schematy danych classification: Pydantic waliduje dane wejścia/wyjścia; te klasy nie tworzą
# tabel SQL.

from pydantic import BaseModel, Field, PrivateAttr

from app.enums import CandidateCategory


class CandidateClassification(BaseModel):
    """Structured output expected from the LLM. total_score is computed by the backend."""

    # Field dodaje walidację Pydantic: ge/le to granice liczb, a default/default_factory określają
    # wartość domyślną.
    _usage: dict[str, str | int] | None = PrivateAttr(default=None)

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
