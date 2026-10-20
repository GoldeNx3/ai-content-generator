# Rola pliku: Zapytania o wpisy: filtrowanie, paginacja, statystyki i zbiorczy zapis z ochroną przed
# duplikatami URL.

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, String, case, cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Candidate, CandidateStatus, WordPressPublication
from app.demo import DEMO_PREFIX
from app.schemas.candidate import CandidateFilters, SortOrder

INSERT_CHUNK_SIZE = 500


def workflow_status_expression():
    # Use the last verified WordPress state, including while a new send is
    # queued or has failed. A queued request is never evidence of publication.
    publication = select(case(
        (WordPressPublication.wp_status == 'publish', 'published'),
        (WordPressPublication.wp_status == 'draft', 'draft'),
        (WordPressPublication.wp_status == 'future', 'scheduled'),
    )).where(
        WordPressPublication.candidate_id == Candidate.id,
        WordPressPublication.wordpress_post_id.is_not(None),
        WordPressPublication.last_synced_at.is_not(None),
    ).correlate(Candidate).scalar_subquery()
    article = select(case((Article.status == 'approved', 'approved'), else_='draft')).where(
        Article.candidate_id == Candidate.id, Article.is_current.is_(True),
    ).correlate(Candidate).scalar_subquery()
    return func.coalesce(publication, case(
        (Candidate.status == CandidateStatus.IGNORED, 'ignored'),
        else_=func.coalesce(article, cast(Candidate.status, String)),
    ))


class CandidateRepository:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def get(self, candidate_id: int) -> Candidate | None:
        row = (await self.session.execute(select(Candidate, workflow_status_expression())
            .where(Candidate.id == candidate_id))).unique().one_or_none()
        if row is None:
            return None
        candidate, workflow_status = row
        candidate.workflow_status = workflow_status
        return candidate

    async def existing_urls(self, urls: Iterable[str], workspace_id: int) -> set[str]:
        url_list = list(urls)
        if not url_list:
            return set()
        query = select(Candidate.external_url).where(
            Candidate.workspace_id == workspace_id, Candidate.external_url.in_(url_list))
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
                .on_conflict_do_nothing(index_elements=[Candidate.workspace_id, Candidate.external_url])
                .returning(Candidate.id)
            )
            inserted += len((await self.session.execute(statement)).all())
        return inserted

    async def search(self, filters: CandidateFilters, workspace_id: int) -> tuple[Sequence[Candidate], int]:
        query = self._apply_filters(select(Candidate, workflow_status_expression()), filters, workspace_id)
        total = await self.session.scalar(
            self._apply_filters(select(func.count(Candidate.id)), filters, workspace_id)
        )

        column = getattr(Candidate, filters.sort.value)
        ordering = column.asc() if filters.order == SortOrder.ASC else column.desc()
        query = (
            query.order_by(ordering.nulls_last(), Candidate.created_at.desc(), Candidate.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        rows = (await self.session.execute(query)).unique().all()
        items = []
        for candidate, workflow_status in rows:
            candidate.workflow_status = workflow_status
            items.append(candidate)
        return items, total or 0

    # „Niesklasyfikowany” oznacza tutaj brak total_score, niezależnie od statusu decyzji redaktora.
    async def list_unclassified_ids(self, limit: int | None = None, workspace_id: int | None = None) -> list[int]:
        query = (
            select(Candidate.id)
            .where(Candidate.total_score.is_(None), ~Candidate.external_url.startswith(DEMO_PREFIX))
            .order_by(Candidate.original_published_at.desc().nulls_last(), Candidate.id.desc())
            .limit(limit)
        )
        if workspace_id is not None:
            query = query.where(Candidate.workspace_id == workspace_id)
        return list((await self.session.scalars(query)).all())

    async def count(self, *conditions: Any) -> int:
        return await self.session.scalar(select(func.count(Candidate.id)).where(*conditions)) or 0

    async def average_score(self, workspace_id: int) -> float | None:
        value = await self.session.scalar(
            select(func.avg(Candidate.total_score)).where(
                Candidate.total_score.is_not(None), Candidate.workspace_id == workspace_id)
        )
        return round(float(value), 1) if value is not None else None

    async def count_created_since(self, since: datetime, workspace_id: int,
                                  status: CandidateStatus | None = None) -> int:
        conditions = [Candidate.created_at >= since, Candidate.workspace_id == workspace_id]
        if status is not None:
            conditions.append(Candidate.status == status)
        return await self.count(*conditions)

    # Kolejne where zawężają zapytanie; sprawdzamy is not None, bo zero jest prawidłową granicą punktacji.
    # staticmethod nie dostaje automatycznie self; to funkcja pomocnicza umieszczona w przestrzeni nazw klasy.
    @staticmethod
    def _apply_filters(query: Select[Any], filters: CandidateFilters, workspace_id: int) -> Select[Any]:
        query = query.where(Candidate.workspace_id == workspace_id)
        if filters.status is not None:
            query = query.where(Candidate.status == filters.status)
        if filters.workflow_status is not None:
            query = query.where(workflow_status_expression() == filters.workflow_status)
        if filters.category is not None:
            query = query.where(Candidate.category == filters.category)
        if filters.source_id is not None:
            query = query.where(Candidate.source_id == filters.source_id)
        if filters.min_score is not None:
            query = query.where(Candidate.total_score >= filters.min_score)
        if filters.max_score is not None:
            query = query.where(Candidate.total_score <= filters.max_score)
        return query
