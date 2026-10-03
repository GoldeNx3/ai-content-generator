# Rola pliku: Modele tabel source: mapują rekordy SQL na obiekty Pythona i definiują pola oraz powiązania.

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import SourceType
from app.models.mixins import TimestampMixin


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    # Mapped[T] opisuje typ pola ORM; mapped_column definiuje kolumnę SQL, a relationship relację między
    # obiektami.
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", values_callable=lambda e: [m.value for m in e]),
        default=SourceType.RSS,
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
