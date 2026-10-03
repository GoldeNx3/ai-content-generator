# Rola pliku: Endpointy HTTP zasobu stats: przekazują pracę serwisom/repozytoriom i wystawiają wyniki
# oraz błędy przez FastAPI.

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.stats import DashboardStats
from app.services.stats_service import get_dashboard_stats

router = APIRouter(prefix="/stats", tags=["stats"])


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
@router.get("", response_model=DashboardStats)
async def dashboard_stats(session: SessionDep) -> DashboardStats:
    return await get_dashboard_stats(session)
