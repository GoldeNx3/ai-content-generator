from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.stats import DashboardStats
from app.services.stats_service import get_dashboard_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=DashboardStats)
async def dashboard_stats(session: SessionDep) -> DashboardStats:
    return await get_dashboard_stats(session)
