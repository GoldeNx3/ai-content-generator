# Rola pliku: Modele tabel candidate: mapują rekordy SQL na obiekty Pythona i definiują pola oraz powiązania.

from datetime import datetime
from uuid import UUID
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import CandidateCategory, CandidateStatus
from app.models.mixins import TimestampMixin
from app.models.source import Source


def enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


class Candidate(TimestampMixin, Base):
    __tablename__ = "candidates"

    # Powiązanie wyniku z zadaniem; stare dane mogą nie mieć tego pola.
    classification_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", name="fk_candidate_classification_job_id", use_alter=True, ondelete="SET NULL"),
         nullable=True,
    )

    # Mapped[T] opisuje typ pola ORM; mapped_column definiuje kolumnę SQL, a relationship relację między
    # obiektami.
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    external_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    original_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, name="candidate_status", values_callable=enum_values),
        default=CandidateStatus.PENDING,
        index=True,
        nullable=False,
    )

    relevance_score: Mapped[int | None] = mapped_column(Integer)
    freshness_score: Mapped[int | None] = mapped_column(Integer)
    search_potential_score: Mapped[int | None] = mapped_column(Integer)
    commercial_potential_score: Mapped[int | None] = mapped_column(Integer)
    total_score: Mapped[int | None] = mapped_column(Integer, index=True)

    category: Mapped[CandidateCategory | None] = mapped_column(
        Enum(CandidateCategory, name="candidate_category", values_callable=enum_values)
    )
    llm_reason: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str | None] = mapped_column(String(200))
    llm_input_tokens: Mapped[int | None] = mapped_column(Integer)
    llm_output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship(lazy="joined")

    # property pozwala odczytywać wynik metody jak pole: obj.nazwa zamiast obj.nazwa().
    @property
    def source_name(self) -> str:
        return self.source.name
