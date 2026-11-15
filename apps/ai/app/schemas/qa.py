"""Strict evidence audit and public QA report contracts."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QAIssueType(StrEnum):
    UNSUPPORTED_CLAIM = 'unsupported_claim'
    CONTRADICTION = 'contradiction'
    INCORRECT_NUMBER = 'incorrect_number'
    INCORRECT_DATE = 'incorrect_date'
    UNSUPPORTED_QUOTE = 'unsupported_quote'
    UNSUPPORTED_NAME = 'unsupported_name'
    SOURCE_MISMATCH = 'source_mismatch'
    MISSING_UNCERTAINTY = 'missing_uncertainty'
    IGNORED_CONFLICT = 'ignored_conflict'
    TITLE_MISMATCH = 'title_mismatch'
    REPETITION = 'repetition'
    STYLE_ISSUE = 'style_issue'
    STRUCTURE_ISSUE = 'structure_issue'
    SEO_ISSUE = 'seo_issue'
    OVERCLAIM = 'overclaim'
    TOO_CLOSE_TO_SOURCE = 'too_close_to_source'
    UNVERIFIED_NUMBER = 'unverified_number'
    OTHER = 'other'


class QAIssueOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: QAIssueType
    severity: Literal['info', 'warning', 'high', 'critical']
    excerpt: str
    reason: str = Field(min_length=1)
    suggestion: str
    section_heading: str | None
    fact_ids: list[int]
    source_ids: list[int]
    auto_fixable: bool


class QAClaim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    excerpt: str = Field(min_length=1)
    section_heading: str | None
    verdict: Literal['supported', 'unsupported', 'contradicted', 'uncertain']
    fact_ids: list[int]
    source_ids: list[int]


class QAOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    factual_score: int = Field(ge=0, le=100, strict=True)
    source_score: int = Field(ge=0, le=100, strict=True)
    style_score: int = Field(ge=0, le=100, strict=True)
    structure_score: int = Field(ge=0, le=100, strict=True)
    seo_score: int = Field(ge=0, le=100, strict=True)
    summary: str = Field(min_length=1)
    issues: list[QAIssueOutput]
    claims: list[QAClaim] = Field(min_length=1)


class QAIssueRead(QAIssueOutput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    article_qa_id: int
    created_at: datetime
    updated_at: datetime


class ArticleQARead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    article_id: int
    article_version: int
    job_id: UUID | None
    status: Literal['pending', 'running', 'completed', 'failed']
    overall_score: int | None
    factual_score: int | None
    source_score: int | None
    style_score: int | None
    structure_score: int | None
    seo_score: int | None
    supported_claims_count: int
    unsupported_claims_count: int
    critical_issue_count: int
    warning_count: int
    summary: str | None
    llm_model: str | None
    llm_input_tokens: int | None
    llm_output_tokens: int | None
    estimated_cost_usd: Decimal | None
    qa_passed: bool
    pass_score: int
    is_stale: bool = False
    issues: list[QAIssueRead]
    created_at: datetime
    updated_at: datetime
