# Rola pliku: Osobny scheduler pobiera RSS i zleca klasyfikację kolejce.
# Advisory lock zapobiega równoczesnym przebiegom dwóch schedulerów.
# Płatne operacje wykonuje wyłącznie worker, nie scheduler ani proces API.

import asyncio
import logging
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text, select

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.models import Candidate
from app.demo import DEMO_PREFIX
from app.models.job import Job
from app.services.auth.service import AuthService
from app.services.ingestion_service import IngestionService
from app.services.jobs.errors import JobConflict
from app.services.jobs.service import JobService
from app.services.rss_fetcher import RssFetcher

logger = logging.getLogger(__name__)
SCHEDULER_LOCK = 73481923


async def run_pipeline_once():
    settings = get_settings()
    # Dedykowane połączenie trzyma blokadę sesyjną. Nie wraca do poola,
    # dopóki advisory lock nie zostanie jawnie zwolniony.
    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': SCHEDULER_LOCK})
        if not acquired:
            return
        try:
            async with SessionLocal() as session:
                # Sprzątanie wygasłych sesji i starych prób logowania (niezależne od pobierania RSS).
                await AuthService(session, settings).purge_expired()
                result = await IngestionService(session, RssFetcher(timeout=settings.http_timeout_seconds),
                                                max_age_days=settings.fetch_max_age_days).fetch_all_active()
                logger.info('Scheduled fetch: %s', result.model_dump())
                if not settings.openai_api_key:
                    return
                # Pomijamy już zlecone klasyfikacje PRZED limitowaniem. Błędne
                # zadania ponawia użytkownik; nie blokują następnych tematów.
                prior = select(Job.id).where(Job.candidate_id == Candidate.id, Job.kind == 'classify').exists()
                ids = (await session.scalars(select(Candidate.id).where(
                    Candidate.total_score.is_(None), ~Candidate.external_url.startswith(DEMO_PREFIX), ~prior)
                    .order_by(Candidate.id.desc()).limit(settings.classify_batch_limit))).all()
                service = JobService(session, settings)
                for candidate_id in ids:
                    try:
                        key = uuid5(NAMESPACE_URL, f'scheduled-classify:{candidate_id}')
                        await service.enqueue('classify', candidate_id, key=key)
                    except JobConflict:
                        await session.rollback()
        finally:
            await lock_connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': SCHEDULER_LOCK})


async def run_scheduler(interval_minutes):
    if interval_minutes <= 0:
        # Wyłączenie schedulera nie kończy procesu, który Docker restartowałby.
        await asyncio.Event().wait()
    while True:
        try:
            await run_pipeline_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Scheduler run failed')
        await asyncio.sleep(interval_minutes * 60)


if __name__ == '__main__':
    from app.core.logging import setup_logging
    setup_logging()
    asyncio.run(run_scheduler(get_settings().fetch_interval_minutes))
