# Rola pliku: Łączy routery poszczególnych zasobów w jeden router API, który main.py podpina do aplikacji.
# Tylko /auth jest publiczne; pozostałe zasoby wymagają ważnej sesji (get_current_user).

from fastapi import APIRouter, Depends

from app.api import auth, wordpress, auto_fix, qa, articles, candidates, jobs, pricing, research, sources, stats
from app.api.deps import get_current_user

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)

protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(jobs.router)
protected.include_router(pricing.router)
protected.include_router(sources.router)
protected.include_router(candidates.router)
protected.include_router(research.router)
protected.include_router(articles.router)
protected.include_router(qa.router)
protected.include_router(auto_fix.router)
protected.include_router(stats.router)
protected.include_router(wordpress.router)
api_router.include_router(protected)
