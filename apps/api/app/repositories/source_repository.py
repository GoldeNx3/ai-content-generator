# Rola pliku: Operacje SQL na źródłach RSS: odczyt, dodawanie, usuwanie i aktualizacja czasu ostatniego
# pobrania.

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source


class SourceRepository:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    # workspace_id=None tylko dla procesów systemowych (scheduler); endpointy zawsze podają workspace.
    async def list_all(self, active_only: bool = False, workspace_id: int | None = None) -> Sequence[Source]:
        query = select(Source).order_by(Source.name)
        if workspace_id is not None:
            query = query.where(Source.workspace_id == workspace_id)
        if active_only:
            query = query.where(Source.active.is_(True))
        return (await self.session.scalars(query)).all()

    async def get(self, source_id: int) -> Source | None:
        return await self.session.get(Source, source_id)

    async def get_by_url(self, url: str, workspace_id: int) -> Source | None:
        return await self.session.scalar(select(Source).where(Source.url == url, Source.workspace_id == workspace_id))

    async def add(self, source: Source) -> Source:
        self.session.add(source)
        # flush wysyła zmiany do bazy (np. nadaje ID), ale nie zatwierdza jeszcze transakcji jak commit.
        await self.session.flush()
        return source

    async def delete(self, source: Source) -> None:
        await self.session.delete(source)

    async def mark_fetched(self, source: Source, fetched_at: datetime) -> None:
        source.last_fetched_at = fetched_at
