# Rola pliku: Modele tabel article: mapują rekordy SQL na obiekty Pythona i definiują pola oraz powiązania.

from decimal import Decimal
from uuid import UUID
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.candidate import enum_values
from app.models.enums import ArticleStatus, CandidateCategory
from app.models.mixins import TimestampMixin


class Article(TimestampMixin, Base):
    """One row per generated version. Regeneration adds a row; only one row per candidate is current."""

    __tablename__ = "articles"

    @property
    def article_format(self) -> str:
        # New versions store the resolved format in their existing JSON brief.
        # Older versions retain the format implied by their old category.
        return (self.brief or {}).get("article_format") or {
            "guide": "guide", "comparison": "comparison", "news": "news",
        }.get(self.article_type, "explainer")

    # Powiązanie wyniku z zadaniem; stare dane mogą nie mieć tego pola.
    generation_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", name="fk_article_generation_job_id", use_alter=True, ondelete="SET NULL"),
        unique=True, nullable=True,
    )
    __table_args__ = (
        UniqueConstraint("candidate_id", "version", name="uq_articles_candidate_version"),
        Index(
            "uq_articles_one_current_per_candidate",
            "candidate_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    # Mapped[T] opisuje typ pola ORM; mapped_column definiuje kolumnę SQL, a relationship relację między
    # obiektami.
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_id: Mapped[int | None] = mapped_column(ForeignKey("researches.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    status: Mapped[ArticleStatus] = mapped_column(
        Enum(ArticleStatus, name="article_status", values_callable=enum_values),
        default=ArticleStatus.DRAFT,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False)
    lead: Mapped[str] = mapped_column(Text, nullable=False)
    # Markdown body (sections + conclusion). Editable by humans.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Untouched LLM output, kept for diffing manual edits / future fact checking.
    generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_title: Mapped[str] = mapped_column(String(300), nullable=False)
    meta_description: Mapped[str] = mapped_column(String(500), nullable=False)
    article_type: Mapped[CandidateCategory] = mapped_column(
        Enum(CandidateCategory, name="candidate_category", values_callable=enum_values, create_type=False),
        nullable=False,
    )
    angle: Mapped[str | None] = mapped_column(Text)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Generation details (structured, as returned by the LLM after backend validation).
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    lead_fact_ids: Mapped[list[int]] = mapped_column(JSONB, default=list, nullable=False)
    generation_options: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Facts/sources as they were when generating - research can be re-run later, history stays readable.
    research_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validation_warnings: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sections_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    facts_used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    facts_available_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Totals (brief + writer) ...
    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    # ... and per step.
    brief_llm_model: Mapped[str | None] = mapped_column(String(100))
    brief_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brief_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brief_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    writer_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    writer_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    writer_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
