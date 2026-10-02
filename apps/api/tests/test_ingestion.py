import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, CandidateStatus, Source
from app.services.ingestion_service import IngestionService
from app.services.rss_fetcher import RssFetcher
from tests.feeds import ATOM_FEED, RSS_FEED

FEEDS = {
    "https://example.com/feed.xml": RSS_FEED,
    "https://example.com/atom.xml": ATOM_FEED,
}


def make_fetcher() -> RssFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        content = FEEDS.get(str(request.url))
        return httpx.Response(200, content=content) if content else httpx.Response(404)

    return RssFetcher(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), timeout=1)


async def count_candidates(session: AsyncSession) -> int:
    return await session.scalar(select(func.count(Candidate.id))) or 0


async def test_creates_candidates_from_feed(session: AsyncSession, source: Source) -> None:
    result = await IngestionService(session, make_fetcher()).fetch_source(source)

    assert result.items_found == 3
    assert result.new_candidates == 2
    assert result.duplicates == 1  # duplicate URL inside the same feed
    assert result.errors == 0

    candidates = (await session.scalars(select(Candidate).order_by(Candidate.id))).all()
    assert [c.external_url for c in candidates] == [
        "https://example.com/posts/1",
        "https://example.com/posts/2",
    ]
    assert candidates[0].status == CandidateStatus.PENDING
    assert candidates[0].total_score is None
    assert candidates[0].source_id == source.id
    await session.refresh(source)
    assert source.last_fetched_at is not None


async def test_deduplicates_by_url(session: AsyncSession, source: Source) -> None:
    service = IngestionService(session, make_fetcher())
    await service.fetch_source(source)

    second = await service.fetch_source(source)

    assert second.new_candidates == 0
    assert second.duplicates == 3
    assert await count_candidates(session) == 2


async def test_failing_source_does_not_stop_others(session: AsyncSession) -> None:
    session.add_all(
        [
            Source(name="Broken", url="https://example.com/missing.xml"),
            Source(name="Atom", url="https://example.com/atom.xml"),
            Source(name="Inactive", url="https://example.com/feed.xml", active=False),
        ]
    )
    await session.commit()

    result = await IngestionService(session, make_fetcher()).fetch_all_active()

    assert result.sources_processed == 2
    assert result.errors == 1
    assert result.new_candidates == 1
    assert await count_candidates(session) == 1


async def test_skips_entries_older_than_max_age(session: AsyncSession, source: Source) -> None:
    result = await IngestionService(session, make_fetcher(), max_age_days=14).fetch_source(source)

    # The dated entry (2025) is too old; entries without a date are kept.
    assert result.items_found == 3
    assert result.skipped_old == 1
    assert result.new_candidates == 2
    assert result.duplicates == 0
