# Rola pliku: Modele tabel mixins: mapują rekordy SQL na obiekty Pythona i definiują pola oraz powiązania.

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    # Mapped[T] opisuje typ pola ORM; mapped_column definiuje kolumnę SQL, a relationship relację między
    # obiektami.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
