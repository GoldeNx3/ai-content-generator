# Rola pliku: Zapytania o wpisy: filtrowanie, paginacja, statystyki i zbiorczy zapis z ochroną przed
# duplikatami URL.

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, CandidateStatus
from app.schemas.candidate import CandidateFilters, SortOrder

INSERT_CHUNK_SIZE = 500


class CandidateRepository:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def get(self, candidate_id: int) -> Candidate | None:
        return await self.session.get(Candidate, candidate_id)

    async def existing_urls(self, urls: Iterable[str]) -> set[str]:
        url_list = list(urls)
        if not url_list:
            return set()
        query = select(Candidate.external_url).where(Candidate.external_url.in_(url_list))
        return set((await self.session.scalars(query)).all())

    # Zapis porcjami ogranicza rozmiar zapytania; RETURNING zwraca ID tylko rekordów rzeczywiście dodanych.
    async def insert_many(self, rows: list[dict[str, Any]]) -> int:
        """Insert rows, silently skipping URLs that already exist. Returns inserted count."""
        inserted = 0
        for start in range(0, len(rows), INSERT_CHUNK_SIZE):
            # ON CONFLICT DO NOTHING pomija konflikt unikalności w bazie, także gdy dwa procesy próbują
            # zapisać ten sam URL.
            statement = (
                insert(Candidate)
                .values(rows[start : start + INSERT_CHUNK_SIZE])
                .on_conflict_do_nothing(index_elements=[Candidate.external_url])
                .returning(Candidate.id)
            )
            inserted += len((await self.session.execute(statement)).all())
        return inserted

    async def search(self, filters: CandidateFilters) -> tuple[Sequence[Candidate], int]:
        query = self._apply_filters(select(Candidate), filters)
        total = await self.session.scalar(
            self._apply_filters(select(func.count(Candidate.id)), filters)
        )

        column = getattr(Candidate, filters.sort.value)
        ordering = column.asc() if filters.order == SortOrder.ASC else column.desc()
        query = (
            query.order_by(ordering.nulls_last(), Candidate.created_at.desc(), Candidate.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        items = (await self.session.scalars(query)).unique().all()
        return items, total or 0

    # „Niesklasyfikowany” oznacza tutaj brak total_score, niezależnie od statusu decyzji redaktora.
    async def list_unclassified_ids(self, limit: int | None = None) -> list[int]:
        query = (
            select(Candidate.id)
            .where(Candidate.total_score.is_(None))
            .order_by(Candidate.original_published_at.desc().nulls_last(), Candidate.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(query)).all())

    async def count(self, *conditions: Any) -> int:
        return await self.session.scalar(select(func.count(Candidate.id)).where(*conditions)) or 0

    async def average_score(self) -> float | None:
        value = await self.session.scalar(
            select(func.avg(Candidate.total_score)).where(Candidate.total_score.is_not(None))
        )
        return round(float(value), 1) if value is not None else None

    async def count_created_since(self, since: datetime, status: CandidateStatus | None = None) -> int:
        conditions = [Candidate.created_at >= since]
        if status is not None:
            conditions.append(Candidate.status == status)
        return await self.count(*conditions)

    # Kolejne where zawężają zapytanie; sprawdzamy is not None, bo zero jest prawidłową granicą punktacji.
    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def _apply_filters(query: Select[Any], filters: CandidateFilters) -> Select[Any]:
        if filters.status is not None:
            query = query.where(Candidate.status == filters.status)
        if filters.category is not None:
            query = query.where(Candidate.category == filters.category)
        if filters.source_id is not None:
            query = query.where(Candidate.source_id == filters.source_id)
        if filters.min_score is not None:
            query = query.where(Candidate.total_score >= filters.min_score)
        if filters.max_score is not None:
            query = query.where(Candidate.total_score <= filters.max_score)
        return query
