# Rola pliku: Pipeline RSS: pobiera wpisy, odrzuca zbyt stare, deduplikuje po URL i zapisuje nowe rekordy
# Candidate.

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.source_repository import SourceRepository
from app.schemas.source import FetchResult
from app.services.rss_fetcher import FeedEntry, FeedFetchError, RssFetcher

logger = logging.getLogger(__name__)


class IngestionService:
    """Fetches sources, deduplicates entries by URL and stores new candidates."""

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, session: AsyncSession, fetcher: RssFetcher, max_age_days: int = 0) -> None:
        self.session = session
        self.fetcher = fetcher
        self.max_age_days = max_age_days
        self.sources = SourceRepository(session)
        self.candidates = CandidateRepository(session)

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def fetch_all_active(self) -> FetchResult:
        total = FetchResult()
        for source in await self.sources.list_all(active_only=True):
            total.add(await self.fetch_source(source))
        return total

    async def fetch_source(self, source: Source) -> FetchResult:
        """Never raises for feed problems: errors are logged and counted."""
        result = FetchResult(sources_processed=1)
        try:
            entries = await self.fetcher.fetch(source)
        except FeedFetchError as exc:
            logger.warning("Fetching source %s (%s) failed: %s", source.id, source.name, exc)
            result.errors = 1
            return result
        except Exception:
            logger.exception("Unexpected error while fetching source %s (%s)", source.id, source.url)
            result.errors = 1
            return result

        result.items_found = len(entries)
        fresh_entries = self._drop_old(entries)
        result.skipped_old = len(entries) - len(fresh_entries)
        try:
            result.new_candidates = await self._save_new(source, fresh_entries)
            await self.sources.mark_fetched(source, datetime.now(UTC))
            # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza
            # jeszcze trwałego zapisu.
            await self.session.commit()
        except Exception:
            # rollback wycofuje niezakończoną transakcję po błędzie; wcześniejsze commity pozostają zapisane.
            await self.session.rollback()
            logger.exception("Saving candidates for source %s failed", source.id)
            result.errors = 1
            result.new_candidates = 0
        result.duplicates = len(fresh_entries) - result.new_candidates
        logger.info(
            "Source %s: found=%d new=%d duplicates=%d skipped_old=%d",
            source.name, result.items_found, result.new_candidates, result.duplicates, result.skipped_old,
        )
        return result

    # Brak daty nie eliminuje wpisu; list comprehension tworzy nową listę wpisów spełniających warunek wieku.
    def _drop_old(self, entries: list[FeedEntry]) -> list[FeedEntry]:
        if self.max_age_days <= 0:
            return entries
        cutoff = datetime.now(UTC) - timedelta(days=self.max_age_days)
        return [e for e in entries if e.published_at is None or e.published_at >= cutoff]

    # Najpierw deduplikacja w samym feedzie, potem porównanie z bazą; końcowy insert chroni też przed
    # konfliktem równoległych zapisów.
    async def _save_new(self, source: Source, entries: list[FeedEntry]) -> int:
        unique: dict[str, FeedEntry] = {}
        for entry in entries:
            unique.setdefault(entry.url, entry)
        existing = await self.candidates.existing_urls(unique.keys())
        rows = [
            {
                "source_id": source.id,
                "external_url": entry.url,
                "title": entry.title,
                "summary": entry.summary,
                "original_published_at": entry.published_at,
            }
            for url, entry in unique.items()
            if url not in existing
        ]
        return await self.candidates.insert_many(rows)
