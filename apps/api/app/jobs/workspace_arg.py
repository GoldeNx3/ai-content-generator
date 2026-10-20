# Rola pliku: Wybór workspace'u dla komend CLI (seedy, zakładanie kont): jawne ID z argumentu
# albo najstarszy workspace; czytelny błąd, gdy żaden nie istnieje.

import argparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workspace


class WorkspaceNotFound(Exception):
    pass


async def resolve_workspace(session: AsyncSession, workspace_id: int | None) -> int:
    if workspace_id is not None:
        if await session.get(Workspace, workspace_id) is None:
            raise WorkspaceNotFound(f"Workspace {workspace_id} nie istnieje")
        return workspace_id
    oldest = await session.scalar(select(Workspace.id).order_by(Workspace.created_at, Workspace.id).limit(1))
    if oldest is None:
        raise WorkspaceNotFound("Brak workspace'u: najpierw załóż konto (`make create-user EMAIL=...`)")
    return oldest


def workspace_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", type=int, default=None,
                        help="ID workspace'u (domyślnie najstarszy)")
