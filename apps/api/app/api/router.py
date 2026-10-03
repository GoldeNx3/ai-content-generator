# Rola pliku: Łączy routery poszczególnych zasobów w jeden router API, który main.py podpina do aplikacji.

from fastapi import APIRouter

from app.api import articles, candidates, research, sources, stats

api_router = APIRouter(prefix="/api")
api_router.include_router(sources.router)
api_router.include_router(candidates.router)
api_router.include_router(research.router)
api_router.include_router(articles.router)
api_router.include_router(stats.router)
