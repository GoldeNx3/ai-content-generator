# Rola pliku: Operacje SQL na kontach: użytkownicy, członkostwa w workspace'ach, sesje logowania i liczniki
# nieudanych prób uwierzytelnienia.

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthAttempt, User, UserSession, Workspace, WorkspaceMember
from app.enums import AuthAttemptKind


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    # Pierwszy workspace użytkownika (najstarsze członkostwo) staje się aktywnym przy logowaniu.
    async def default_membership(self, user_id: int) -> WorkspaceMember | None:
        return await self.session.scalar(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.created_at, WorkspaceMember.workspace_id).limit(1)
        )

    # Sesja jest ważna tylko razem z aktywnym kontem i nadal istniejącym członkostwem.
    async def resolve_session(
        self, token_hash: str, now: datetime
    ) -> tuple[UserSession, User, Workspace, WorkspaceMember] | None:
        row = (await self.session.execute(
            select(UserSession, User, Workspace, WorkspaceMember)
            .join(User, User.id == UserSession.user_id)
            .join(Workspace, Workspace.id == UserSession.workspace_id)
            .join(WorkspaceMember, (WorkspaceMember.workspace_id == UserSession.workspace_id)
                  & (WorkspaceMember.user_id == UserSession.user_id))
            .where(UserSession.token_hash == token_hash, UserSession.expires_at > now, User.is_active.is_(True))
        )).first()
        return tuple(row) if row else None

    async def delete_session(self, token_hash: str) -> None:
        await self.session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))

    async def count_attempts(self, kind: AuthAttemptKind, *, since: datetime, email: str | None = None,
                             ip: str | None = None, failed_only: bool = False) -> int:
        query = select(func.count()).select_from(AuthAttempt).where(
            AuthAttempt.kind == kind, AuthAttempt.created_at >= since)
        if failed_only:
            query = query.where(AuthAttempt.succeeded.is_(False))
        if email is not None:
            query = query.where(AuthAttempt.email == email)
        if ip is not None:
            query = query.where(AuthAttempt.ip == ip)
        return int(await self.session.scalar(query) or 0)

    async def purge(self, now: datetime, attempts_before: datetime) -> None:
        await self.session.execute(delete(UserSession).where(UserSession.expires_at <= now))
        await self.session.execute(delete(AuthAttempt).where(AuthAttempt.created_at < attempts_before))
