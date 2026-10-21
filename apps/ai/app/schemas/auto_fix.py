from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class FixRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    issue_ids: list[int] | None = Field(default=None,min_length=1)

class RejectRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str | None = Field(default=None,max_length=2000)

class FixPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field: Literal['title','lead','content','slug','meta_title','meta_description']
    before: str = Field(min_length=1)
    after: str
    qa_issue_ids: list[int] = Field(min_length=1)
    fact_ids: list[int]
    source_ids: list[int]

class FixIssueResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    qa_issue_id: int
    status: Literal['fixed','skipped','failed']
    reason: str = Field(min_length=1)

class FixOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str = Field(min_length=1)
    patches: list[FixPatch]
    fix_results: list[FixIssueResult]

class FixIssueRead(FixIssueResult):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

class ArticleFixRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_article_version_id: int
    result_article_version_id: int | None
    qa_id: int
    job_id: UUID | None
    status: Literal['pending','running','completed','failed']
    iteration: int
    issues_requested: int
    issues_fixed: int
    issues_skipped: int
    summary: str | None
    change_ratio: Decimal | None
    warnings: list[str]
    changes: list[dict]
    llm_model: str | None
    llm_input_tokens: int | None
    llm_output_tokens: int | None
    estimated_cost_usd: Decimal | None
    issues: list[FixIssueRead]
    created_at: datetime
    updated_at: datetime
