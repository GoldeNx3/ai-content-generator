"""Durable, version-bound editorial changes; never owns article content."""
from decimal import Decimal
from uuid import UUID
from typing import Any
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base
from app.models.mixins import TimestampMixin

class ArticleFix(TimestampMixin, Base):
    __tablename__ = 'article_fixes'
    __table_args__ = (CheckConstraint("status IN ('pending','running','completed','failed')", name='ck_article_fix_status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_article_version_id: Mapped[int] = mapped_column(ForeignKey('articles.id',ondelete='RESTRICT'),index=True)
    result_article_version_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id',ondelete='RESTRICT'),unique=True)
    qa_id: Mapped[int] = mapped_column(ForeignKey('article_qas.id',ondelete='RESTRICT'))
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey('jobs.id',ondelete='SET NULL'),unique=True)
    status: Mapped[str] = mapped_column(String(20),default='pending')
    iteration: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64))
    input_snapshot: Mapped[dict[str,Any]] = mapped_column(JSONB)
    issues_requested: Mapped[int] = mapped_column(Integer,default=0)
    issues_fixed: Mapped[int] = mapped_column(Integer,default=0)
    issues_skipped: Mapped[int] = mapped_column(Integer,default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    change_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8,6))
    warnings: Mapped[list[str]] = mapped_column(JSONB,default=list)
    changes: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,default=list)
    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_input_tokens: Mapped[int | None] = mapped_column(Integer)
    llm_output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12,6))
    issues: Mapped[list['ArticleFixIssue']] = relationship(cascade='all, delete-orphan',lazy='selectin',order_by='ArticleFixIssue.id')

class ArticleFixIssue(TimestampMixin,Base):
    __tablename__ = 'article_fix_issues'
    __table_args__ = (UniqueConstraint('article_fix_id','qa_issue_id',name='uq_fix_issue'),
        CheckConstraint("status IN ('fixed','skipped','failed')",name='ck_fix_issue_status'))
    id: Mapped[int] = mapped_column(primary_key=True)
    article_fix_id: Mapped[int] = mapped_column(ForeignKey('article_fixes.id',ondelete='CASCADE'),index=True)
    qa_issue_id: Mapped[int] = mapped_column(ForeignKey('article_qa_issues.id',ondelete='RESTRICT'))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
