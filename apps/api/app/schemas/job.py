# Rola pliku: Publiczny stan zadania. Brak payload, sekretów i tokenu dzierżawy.

from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, computed_field


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: Literal['classify', 'research', 'write', 'qa_article', 'auto_fix_article']
    article_id: int | None = None
    candidate_id: int
    candidate_title: str | None = None
    status: Literal['queued', 'running', 'retrying', 'succeeded', 'failed']
    stage: str | None
    attempt_count: int
    max_attempts: int
    available_at: datetime
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result_type: str | None
    result_id: int | None
    error_code: str | None
    error_message: str | None

    @computed_field
    @property
    def result(self) -> dict | None:
        return {'type': self.result_type, 'id': self.result_id} if self.result_id is not None else None

    @computed_field
    @property
    def error(self) -> dict | None:
        return {'code': self.error_code, 'message': self.error_message} if self.error_code else None


class JobAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    number: int
    started_at: datetime
    finished_at: datetime | None
    outcome: str
    error_code: str | None
    error_message: str | None
    last_stage: str | None
    llm_calls: list[dict[str, Any]]


class JobPage(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int


class EnqueuedBatch(BaseModel):
    job_ids: list[UUID]
    enqueued: int
    existing: int
    skipped_busy: int


class JobStats(BaseModel):
    # Liczniki obejmują całą zapisaną historię, niezależnie od paginacji listy.
    queued: int = 0
    running: int = 0
    retrying: int = 0
    succeeded: int = 0
    failed: int = 0
    total: int = 0
