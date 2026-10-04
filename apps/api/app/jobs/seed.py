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
    # =========================================================
    # AI / LLM
    # =========================================================
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Anthropic", "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("Microsoft Research", "https://www.microsoft.com/en-us/research/feed/"),
    ("NVIDIA Developer", "https://developer.nvidia.com/blog/feed/"),
    ("Simon Willison", "https://simonwillison.net/atom/entries/"),

    # =========================================================
    # PROGRAMMING / SOFTWARE DEVELOPMENT
    # =========================================================
    ("GitHub", "https://github.blog/feed/"),
    ("Martin Fowler", "https://martinfowler.com/feed.atom"),
    ("JetBrains", "https://blog.jetbrains.com/feed/"),
    ("Laravel News", "https://laravel-news.com/feed"),
    ("Symfony Blog", "https://symfony.com/blog/rss"),
    ("Node.js", "https://nodejs.org/en/feed/blog.xml"),

    # =========================================================
    # FRONTEND
    # =========================================================
    ("React", "https://react.dev/rss.xml"),
    ("Next.js", "https://nextjs.org/feed.xml"),
    ("Vue.js", "https://blog.vuejs.org/feed.rss"),
    ("Svelte", "https://svelte.dev/blog/rss.xml"),
    ("Astro", "https://astro.build/rss.xml"),
    ("Tailwind CSS", "https://tailwindcss.com/feeds/feed.xml"),
    ("MDN", "https://developer.mozilla.org/en-US/blog/rss.xml"),
    ("web.dev", "https://web.dev/static/blog/feed.xml"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),

    # =========================================================
    # DEVOPS / CLOUD / KUBERNETES
    # =========================================================
    ("Kubernetes", "https://kubernetes.io/feed.xml"),
    ("Docker", "https://www.docker.com/blog/feed/"),
    ("CNCF", "https://www.cncf.io/blog/feed/"),
    ("Cloudflare", "https://blog.cloudflare.com/rss/"),
    ("AWS DevOps", "https://aws.amazon.com/blogs/devops/feed/"),
    ("AWS Architecture", "https://aws.amazon.com/blogs/architecture/feed/"),
    ("Azure DevOps", "https://devblogs.microsoft.com/devops/feed/"),
    ("Microsoft Azure", "https://azure.microsoft.com/en-us/blog/feed/"),

    # =========================================================
    # FINANCE / SAVING / INVESTING
    # =========================================================
    ("Subiektywnie o Finansach", "https://subiektywnieofinansach.pl/feed/"),
    ("Marcin Iwuć", "https://marciniwuc.com/feed/"),
    ("Jak Oszczędzać Pieniądze", "https://jakoszczedzacpieniadze.pl/feed/"),
    ("Blogi Bossa", "https://blogi.bossa.pl/feed/"),
    ("Of Dollars And Data", "https://ofdollarsanddata.com/feed/"),
    ("A Wealth of Common Sense", "https://awealthofcommonsense.com/feed/"),
    ("Mr. Money Mustache", "https://www.mrmoneymustache.com/feed/"),
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
