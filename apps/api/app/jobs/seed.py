"""Idempotent seed of example RSS sources: python -m app.jobs.seed"""

import asyncio
import logging

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.models import Source
from app.repositories.source_repository import SourceRepository

logger = logging.getLogger(__name__)

SEED_SOURCES: list[tuple[str, str]] = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Anthropic", "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("GitHub", "https://github.blog/feed/"),
]


async def seed() -> None:
    async with SessionLocal() as session:
        repo = SourceRepository(session)
        created = 0
        for name, url in SEED_SOURCES:
            if await repo.get_by_url(url) is None:
                await repo.add(Source(name=name, url=url))
                created += 1
        await session.commit()
    logger.info("Seed finished: %d new sources (%d total in seed list)", created, len(SEED_SOURCES))


if __name__ == "__main__":
    setup_logging()
    asyncio.run(seed())
