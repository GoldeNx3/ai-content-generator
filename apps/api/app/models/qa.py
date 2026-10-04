"""Durable evidence audits tied to an article row/version and frozen input."""
from decimal import Decimal
from uuid import UUID
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class ArticleQA(TimestampMixin, Base):
    __tablename__ = 'article_qas'
    __table_args__ = (CheckConstraint("status IN ('pending','running','completed','failed')", name='ck_article_qa_status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('articles.id', ondelete='CASCADE'), index=True)
    article_version: Mapped[int] = mapped_column(Integer)
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey('jobs.id', ondelete='SET NULL'), unique=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    input_hash: Mapped[str] = mapped_column(String(64))
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    factual_score: Mapped[int | None] = mapped_column(Integer)
    source_score: Mapped[int | None] = mapped_column(Integer)
    style_score: Mapped[int | None] = mapped_column(Integer)
    structure_score: Mapped[int | None] = mapped_column(Integer)
    seo_score: Mapped[int | None] = mapped_column(Integer)
    supported_claims_count: Mapped[int] = mapped_column(Integer, default=0)
    unsupported_claims_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_issue_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_input_tokens: Mapped[int | None] = mapped_column(Integer)
    llm_output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    qa_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    pass_score: Mapped[int] = mapped_column(Integer, default=85)
    issues: Mapped[list['ArticleQAIssue']] = relationship(cascade='all, delete-orphan',
        lazy='selectin', order_by='ArticleQAIssue.id')


class ArticleQAIssue(TimestampMixin, Base):
    __tablename__ = 'article_qa_issues'
    __table_args__ = (CheckConstraint("severity IN ('info','warning','high','critical')", name='ck_qa_issue_severity'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    article_qa_id: Mapped[int] = mapped_column(ForeignKey('article_qas.id', ondelete='CASCADE'), index=True)
    type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    excerpt: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)
    section_heading: Mapped[str | None] = mapped_column(Text)
    fact_ids: Mapped[list[int]] = mapped_column(JSONB, default=list)
    source_ids: Mapped[list[int]] = mapped_column(JSONB, default=list)
    auto_fixable: Mapped[bool] = mapped_column(Boolean, default=False)
