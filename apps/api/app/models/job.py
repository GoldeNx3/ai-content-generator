# Rola pliku: Trwałe zadania i historia prób w PostgreSQL.
# Status zadania jest niezależny od statusu redakcyjnego artykułu.

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ACTIVE_STATUSES = ('queued', 'running', 'retrying')


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        CheckConstraint("kind IN ('classify','research','write','qa_article','auto_fix_article','prepare_wordpress','publish_wordpress')", name='ck_jobs_kind'),
        CheckConstraint("status IN ('queued','running','retrying','succeeded','failed')", name='ck_jobs_status'),
        Index('uq_jobs_active_candidate', 'candidate_id', unique=True,
              postgresql_where=text("status IN ('queued','running','retrying')")),
        Index('ix_jobs_ready', 'available_at', 'created_at', 'id',
              postgresql_where=text("status IN ('queued','retrying')")),
        Index('ix_jobs_expired', 'locked_until', postgresql_where=text("status='running'")),
        Index('ix_jobs_candidate_history', 'candidate_id', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(20))
    candidate_id: Mapped[int] = mapped_column(ForeignKey('candidates.id', ondelete='RESTRICT'))
    article_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id', name='fk_jobs_article', use_alter=True, ondelete='RESTRICT'))
    status: Mapped[str] = mapped_column(String(20), default='queued')
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    idempotency_key: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    request_hash: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str | None] = mapped_column(String(50))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    worker_id: Mapped[str | None] = mapped_column(String(200))
    lease_token: Mapped[UUID | None]
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_type: Mapped[str | None] = mapped_column(String(30))
    result_id: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_of_job_id: Mapped[UUID | None] = mapped_column(ForeignKey('jobs.id'))
    checkpoints: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class JobAttempt(Base):
    __tablename__ = 'job_attempts'
    __table_args__ = (UniqueConstraint('job_id', 'number', name='uq_job_attempt_number'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey('jobs.id', ondelete='CASCADE'), index=True)
    number: Mapped[int]
    worker_id: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(30), default='running')
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    last_stage: Mapped[str | None] = mapped_column(String(50))
    llm_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class JobBatch(Base):
    # Członkostwo partii zapisujemy PRZED enqueue. Powtórzone żądanie po
    # utraconej odpowiedzi nie może wybrać kolejnych płatnych kandydatów.
    __tablename__ = 'job_batches'
    id: Mapped[UUID] = mapped_column(primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    candidate_ids: Mapped[list[int]] = mapped_column(JSONB)
    skipped_ids: Mapped[list[int]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
