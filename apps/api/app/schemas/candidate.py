from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CandidateCategory, CandidateStatus


class CandidateSortField(StrEnum):
    CREATED_AT = "created_at"
    ORIGINAL_PUBLISHED_AT = "original_published_at"
    TOTAL_SCORE = "total_score"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class CandidateFilters(BaseModel):
    status: CandidateStatus | None = None
    category: CandidateCategory | None = None
    source_id: int | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    max_score: int | None = Field(default=None, ge=0, le=100)
    sort: CandidateSortField = CandidateSortField.TOTAL_SCORE
    order: SortOrder = SortOrder.DESC
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    source_name: str
    external_url: str
    title: str
    summary: str | None
    original_published_at: datetime | None
    status: CandidateStatus
    relevance_score: int | None
    freshness_score: int | None
    search_potential_score: int | None
    commercial_potential_score: int | None
    total_score: int | None
    category: CandidateCategory | None
    llm_reason: str | None
    classified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CandidatePage(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int


class CandidateStatusUpdate(BaseModel):
    status: CandidateStatus
