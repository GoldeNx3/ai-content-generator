# Rola pliku: Modele tabel kont: użytkownicy, workspace'y (przestrzenie robocze), członkostwa, sesje
# logowania i próby uwierzytelnienia używane do ograniczania zgadywania haseł.

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.enums import AuthAttemptKind, WorkspaceRole
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Email zapisujemy znormalizowany (lowercase), dlatego zwykły UNIQUE wystarcza.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    # NULL = konto bez hasła (w przyszłości logowanie tylko przez Google/Apple).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    # Łączenie z kontem Google/Apple po emailu jest dozwolone tylko dla potwierdzonego adresu;
    # inaczej ktoś mógłby założyć konto na cudzy email i przejąć je po logowaniu właściciela.
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# Workspace to jednostka, do której w etapie 2 trafi workspace_id na źródłach i kandydatach.
class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Miesięczny limit kosztów AI (USD). NULL = DEFAULT_MONTHLY_BUDGET_USD z .env. Ustawia operator
    # (make set-budget), nie właściciel workspace'u.
    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))


class WorkspaceMember(TimestampMixin, Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )


# W bazie trzymamy tylko sha256 tokenu; wyciek tabeli nie pozwala przejąć sesji.
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip: Mapped[str | None] = mapped_column(String(64))


# Logowania (nieudane liczą się do limitu) i rejestracje (każda liczy się do limitu per IP).
class AuthAttempt(Base):
    __tablename__ = "auth_attempts"
    __table_args__ = (
        Index("ix_auth_attempts_email_created", "email", "created_at"),
        Index("ix_auth_attempts_ip_kind_created", "ip", "kind", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[AuthAttemptKind] = mapped_column(
        Enum(AuthAttemptKind, name="auth_attempt_kind", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
