from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.candidate import enum_values
from app.models.enums import (
    FactImportance,
    FetchStatus,
    ResearchSourceOrigin,
    ResearchSourceType,
    ResearchStatus,
)
from app.models.mixins import TimestampMixin

research_fact_sources = Table(
    "research_fact_sources",
    Base.metadata,
    Column("fact_id", ForeignKey("research_facts.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", ForeignKey("research_sources.id", ondelete="CASCADE"), primary_key=True),
)


class Research(TimestampMixin, Base):
    __tablename__ = "researches"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One current research per candidate.
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus, name="research_status", values_callable=enum_values),
        default=ResearchStatus.PENDING,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text)
    why_it_matters: Mapped[str | None] = mapped_column(Text)
    suggested_angle: Mapped[str | None] = mapped_column(Text)
    search_queries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    uncertainties: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sources: Mapped[list["ResearchSource"]] = relationship(
        back_populates="research",
        cascade="all, delete-orphan",
        order_by="ResearchSource.id",
        lazy="selectin",
    )
    facts: Mapped[list["ResearchFact"]] = relationship(
        back_populates="research",
        cascade="all, delete-orphan",
        order_by="ResearchFact.id",
        lazy="selectin",
    )


class ResearchSource(TimestampMixin, Base):
    __tablename__ = "research_sources"
    __table_args__ = (UniqueConstraint("research_id", "url", name="uq_research_sources_research_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    origin: Mapped[ResearchSourceOrigin] = mapped_column(
        Enum(ResearchSourceOrigin, name="research_source_origin", values_callable=enum_values),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(1000))
    publisher: Mapped[str | None] = mapped_column(String(300))
    source_type: Mapped[ResearchSourceType] = mapped_column(
        Enum(ResearchSourceType, name="research_source_type", values_callable=enum_values),
        default=ResearchSourceType.OTHER,
        nullable=False,
    )
    source_score: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Raw HTML (capped) kept for debugging / future re-extraction. Never sent to the LLM.
    raw_content: Mapped[str | None] = mapped_column(Text, deferred=True)
    extracted_content: Mapped[str | None] = mapped_column(Text)
    fetch_status: Mapped[FetchStatus] = mapped_column(
        Enum(FetchStatus, name="fetch_status", values_callable=enum_values),
        default=FetchStatus.PENDING,
        nullable=False,
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    research: Mapped[Research] = relationship(back_populates="sources")


class ResearchFact(TimestampMixin, Base):
    __tablename__ = "research_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[FactImportance] = mapped_column(
        Enum(FactImportance, name="fact_importance", values_callable=enum_values), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)

    research: Mapped[Research] = relationship(back_populates="facts")
    sources: Mapped[list[ResearchSource]] = relationship(
        secondary=research_fact_sources, lazy="selectin", order_by="ResearchSource.id"
    )

    @property
    def source_ids(self) -> list[int]:
        return [source.id for source in self.sources]
