# Rola pliku: Łączy routery poszczególnych zasobów w jeden router API, który main.py podpina do aplikacji.

from fastapi import APIRouter

from app.api import wordpress, auto_fix, qa, articles, candidates, jobs, pricing, research, sources, stats

api_router = APIRouter(prefix="/api")
api_router.include_router(jobs.router)
api_router.include_router(pricing.router)
api_router.include_router(sources.router)
api_router.include_router(candidates.router)
api_router.include_router(research.router)
api_router.include_router(articles.router)
api_router.include_router(qa.router)
api_router.include_router(auto_fix.router)
api_router.include_router(stats.router)

api_router.include_router(wordpress.router)
