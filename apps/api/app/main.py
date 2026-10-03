# Rola pliku: Punkt wejścia API: tworzy aplikację FastAPI, podpina routery i CORS oraz zarządza startem i
# zatrzymaniem schedulera.

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.jobs.scheduler import run_scheduler
from app.services.research.research import mark_interrupted_researches


# Kod przed yield wykonuje się przy starcie API, a po yield przy zamykaniu; context manager wyznacza cykl
# życia aplikacji.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    settings = get_settings()
    async with SessionLocal() as session:
        interrupted = await mark_interrupted_researches(session)
    if interrupted:
        logging.getLogger(__name__).warning("Marked %d interrupted researches as failed", interrupted)
    task: asyncio.Task[None] | None = None
    if settings.fetch_interval_minutes > 0:
        task = asyncio.create_task(run_scheduler(settings.fetch_interval_minutes))
    yield
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Content Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,  # cache CORS preflight responses (the panel polls research status)
    )
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
