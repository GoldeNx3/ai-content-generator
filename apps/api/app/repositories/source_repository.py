from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, active_only: bool = False) -> Sequence[Source]:
        query = select(Source).order_by(Source.name)
        if active_only:
            query = query.where(Source.active.is_(True))
        return (await self.session.scalars(query)).all()

    async def get(self, source_id: int) -> Source | None:
        return await self.session.get(Source, source_id)

    async def get_by_url(self, url: str) -> Source | None:
        return await self.session.scalar(select(Source).where(Source.url == url))

    async def add(self, source: Source) -> Source:
        self.session.add(source)
        await self.session.flush()
        return source

    async def delete(self, source: Source) -> None:
        await self.session.delete(source)

    async def mark_fetched(self, source: Source, fetched_at: datetime) -> None:
        source.last_fetched_at = fetched_at
