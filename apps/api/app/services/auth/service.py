# Rola pliku: Logika kont: rejestracja (użytkownik + własny workspace), logowanie z limitem nieudanych
# prób, tworzenie/odczyt/usuwanie sesji. Niezależna od FastAPI; używana przez router i komendę CLI.

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import AuthAttempt, User, UserSession, Workspace, WorkspaceMember
from app.enums import AuthAttemptKind, WorkspaceRole
from app.repositories.user_repository import UserRepository
from app.services.auth.passwords import hash_password, needs_rehash, verify_password

# last_seen_at i przedłużenie sesji zapisujemy najwyżej raz na ten okres, nie przy każdym pollingu.
TOUCH_INTERVAL = timedelta(hours=1)


class AuthError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    email: str
    workspace_id: int
    workspace_name: str
    role: WorkspaceRole


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = UserRepository(session)

    # ip=None (komenda CLI) pomija limit rejestracji per IP. workspace_id (tylko CLI) dołącza konto jako
    # owner istniejącego workspace'u zamiast tworzyć nowy.
    async def register(self, email: str, password: str, *, ip: str | None = None,
                       workspace_id: int | None = None) -> User:
        if ip is not None:
            since = datetime.now(UTC) - timedelta(minutes=self.settings.auth_registration_window_minutes)
            count = await self.repo.count_attempts(AuthAttemptKind.REGISTER, ip=ip, since=since)
            if count >= self.settings.auth_max_registrations_per_ip:
                raise AuthError("too_many_registrations")
            # Zapis próby osobno od konta: przy zajętym emailu rollback nie może jej cofnąć.
            attempt = AuthAttempt(kind=AuthAttemptKind.REGISTER, email=email, ip=ip, succeeded=False)
            self.session.add(attempt)
            await self.session.commit()
        user = User(email=email, password_hash=hash_password(password), is_active=True)
        workspace = (await self.session.get(Workspace, workspace_id) if workspace_id is not None
                     else Workspace(name=email.split("@", 1)[0][:200] or email))
        if workspace is None:
            raise AuthError("workspace_not_found")
        self.session.add_all([user, workspace])
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AuthError("email_taken") from exc
        self.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER))
        if ip is not None:
            attempt.succeeded = True
        await self.session.commit()
        return user

    async def check_throttle(self, email: str, ip: str | None) -> None:
        since = datetime.now(UTC) - timedelta(minutes=self.settings.auth_window_minutes)
        failures = await self.repo.count_attempts(AuthAttemptKind.LOGIN, since=since, failed_only=True, email=email)
        if failures >= self.settings.auth_max_failures_per_email:
            raise AuthError("too_many_attempts")
        if ip and await self.repo.count_attempts(
            AuthAttemptKind.LOGIN, since=since, failed_only=True, ip=ip
        ) >= self.settings.auth_max_failures_per_ip:
            raise AuthError("too_many_attempts")

    # Zwraca surowy token do ciasteczka; w bazie zostaje tylko jego hash.
    async def login(self, email: str, password: str, *, ip: str | None, user_agent: str | None) -> str:
        await self.check_throttle(email, ip)
        user = await self.repo.get_by_email(email)
        valid = verify_password(user.password_hash if user else None, password)
        if not valid or user is None or not user.is_active:
            self.session.add(AuthAttempt(kind=AuthAttemptKind.LOGIN, email=email, ip=ip, succeeded=False))
            await self.session.commit()
            raise AuthError("invalid_credentials")
        membership = await self.repo.default_membership(user.id)
        if membership is None:
            raise AuthError("no_workspace")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        now = datetime.now(UTC)
        user.last_login_at = now
        token = secrets.token_urlsafe(32)
        self.session.add(UserSession(
            token_hash=hash_token(token), user_id=user.id, workspace_id=membership.workspace_id,
            expires_at=now + timedelta(days=self.settings.session_ttl_days), last_seen_at=now,
            user_agent=(user_agent or "")[:500] or None, ip=ip,
        ))
        self.session.add(AuthAttempt(kind=AuthAttemptKind.LOGIN, email=email, ip=ip, succeeded=True))
        await self.session.commit()
        return token

    async def resolve(self, token: str) -> CurrentUser | None:
        now = datetime.now(UTC)
        found = await self.repo.resolve_session(hash_token(token), now)
        if found is None:
            return None
        user_session, user, workspace, membership = found
        if now - user_session.last_seen_at >= TOUCH_INTERVAL:
            user_session.last_seen_at = now
            user_session.expires_at = now + timedelta(days=self.settings.session_ttl_days)
            await self.session.commit()
        return CurrentUser(user.id, user.email, workspace.id, workspace.name, membership.role)

    async def logout(self, token: str) -> None:
        await self.repo.delete_session(hash_token(token))
        await self.session.commit()

    async def purge_expired(self) -> None:
        now = datetime.now(UTC)
        await self.repo.purge(now, now - timedelta(days=1))
        await self.session.commit()
