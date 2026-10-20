# Rola pliku: Osobny scheduler pobiera RSS i zleca klasyfikację kolejce.
# Advisory lock zapobiega równoczesnym przebiegom dwóch schedulerów.
# Płatne operacje wykonuje wyłącznie worker, nie scheduler ani proces API.

import asyncio
import logging
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, text, select

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.models import Candidate
from app.demo import DEMO_PREFIX
from app.models.job import Job
from app.services.auth.service import AuthService
from app.services.ingestion_service import IngestionService
from app.services.jobs.errors import JobConflict, JobInputError
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
                # Limit CLASSIFY_BATCH_LIMIT obowiązuje per workspace, aby jeden workspace nie zagłodził innych.
                prior = select(Job.id).where(Job.candidate_id == Candidate.id, Job.kind == 'classify').exists()
                ranked = select(Candidate.id, Candidate.workspace_id, func.row_number().over(
                    partition_by=Candidate.workspace_id, order_by=Candidate.id.desc()).label('rank')).where(
                    Candidate.total_score.is_(None), ~Candidate.external_url.startswith(DEMO_PREFIX), ~prior).subquery()
                rows = (await session.execute(select(ranked.c.id, ranked.c.workspace_id)
                        .where(ranked.c.rank <= settings.classify_batch_limit)
                        .order_by(ranked.c.workspace_id, ranked.c.id.desc()))).all()
                service = JobService(session, settings)
                over_budget = set()
                for candidate_id, workspace_id in rows:
                    if workspace_id in over_budget:
                        continue
                    try:
                        key = uuid5(NAMESPACE_URL, f'scheduled-classify:{candidate_id}')
                        await service.enqueue('classify', candidate_id, key=key)
                    except JobConflict:
                        await session.rollback()
                    except JobInputError as exc:
                        await session.rollback()
                        if exc.status_code != 402:
                            raise
                        # Budżet workspace'u wyczerpany: bez automatycznej klasyfikacji do końca miesiąca.
                        logger.info('Scheduler: workspace %s over AI budget, skipping classification', workspace_id)
                        over_budget.add(workspace_id)
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
