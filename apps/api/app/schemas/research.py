from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import (
    FactBasis,
    FactImportance,
    FetchStatus,
    ResearchSourceOrigin,
    ResearchSourceType,
    ResearchStatus,
)

# ---------- LLM structured output ----------


class SearchQueries(BaseModel):
    queries: list[str] = Field(description="Maksymalnie 3 krótkie zapytania wyszukiwania")


class LLMFact(BaseModel):
    claim: str
    importance: FactImportance
    basis: FactBasis
    confidence: int = Field(ge=0, le=100)
    source_urls: list[str]


class LLMUncertainty(BaseModel):
    claim: str
    reason: str


class LLMConflictSource(BaseModel):
    url: str
    claim: str


class LLMConflict(BaseModel):
    topic: str
    sources: list[LLMConflictSource]


class LLMSourceAssessment(BaseModel):
    url: str
    source_type: ResearchSourceType


class ResearchOutput(BaseModel):
    summary: str
    why_it_matters: str
    suggested_angle: str
    facts: list[LLMFact]
    uncertainties: list[LLMUncertainty]
    conflicts: list[LLMConflict]
    source_types: list[LLMSourceAssessment] = Field(
        description="Sugerowany typ każdego źródła (backend i tak liczy wiarygodność sam)"
    )


# ---------- API ----------


class ManualSourceCreate(BaseModel):
    url: HttpUrl


class ResearchSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    origin: ResearchSourceOrigin
    title: str | None
    publisher: str | None
    source_type: ResearchSourceType
    source_score: int
    published_at: datetime | None
    extracted_content: str | None
    fetch_status: FetchStatus
    http_status: int | None
    error: str | None
    created_at: datetime


class ResearchFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim: str
    importance: FactImportance
    confidence: int
    source_ids: list[int]


class UncertaintyRead(BaseModel):
    claim: str
    reason: str


class ConflictRead(BaseModel):
    topic: str
    sources: list[LLMConflictSource]


class ResearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    status: ResearchStatus
    summary: str | None
    why_it_matters: str | None
    suggested_angle: str | None
    search_queries: list[str]
    uncertainties: list[UncertaintyRead]
    conflicts: list[ConflictRead]
    error: str | None
    llm_model: str | None
    llm_input_tokens: int
    llm_output_tokens: int
    estimated_cost_usd: Decimal | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    sources: list[ResearchSourceRead]
    facts: list[ResearchFactRead]
