import asyncio
import logging

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.classification_service import ClassificationService
from app.services.ingestion_service import IngestionService
from app.services.llm.factory import get_llm_provider
from app.services.rss_fetcher import RssFetcher

logger = logging.getLogger(__name__)


async def run_pipeline_once() -> None:
    """Fetch all active sources, then classify new candidates if an LLM is configured."""
    settings = get_settings()
    async with SessionLocal() as session:
        fetch_result = await IngestionService(
            session,
            RssFetcher(timeout=settings.http_timeout_seconds),
            max_age_days=settings.fetch_max_age_days,
        ).fetch_all_active()
        logger.info("Scheduled fetch finished: %s", fetch_result.model_dump())

        if not settings.openai_api_key:
            logger.info("OPENAI_API_KEY not set - skipping automatic classification")
            return
        classify_result = await ClassificationService(session, get_llm_provider()).classify_pending(
            settings.classify_batch_limit
        )
        logger.info("Scheduled classification finished: %s", classify_result.model_dump())


async def run_scheduler(interval_minutes: int) -> None:
    logger.info("Scheduler started, interval=%d min", interval_minutes)
    while True:
        try:
            await run_pipeline_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled pipeline run failed")
        await asyncio.sleep(interval_minutes * 60)
