# Rola pliku: Dodaje przykładowe źródła RSS do bazy. Sprawdzenie istniejących adresów pozwala uruchamiać
# seed wielokrotnie.

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


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def seed() -> None:
    async with SessionLocal() as session:
        repo = SourceRepository(session)
        created = 0
        for name, url in SEED_SOURCES:
            if await repo.get_by_url(url) is None:
                await repo.add(Source(name=name, url=url))
                created += 1
        # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
        # trwałego zapisu.
        await session.commit()
    logger.info("Seed finished: %d new sources (%d total in seed list)", created, len(SEED_SOURCES))


if __name__ == "__main__":
    setup_logging()
    asyncio.run(seed())
