# Rola pliku: Punkt wejścia API: tworzy aplikację FastAPI, podpina routery i CORS oraz zarządza startem i
# zatrzymaniem aplikacji. Scheduler i worker mają osobne procesy.

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging


# Kod przed yield wykonuje się przy starcie API, a po yield przy zamykaniu; context manager wyznacza cykl
# życia aplikacji.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield


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
