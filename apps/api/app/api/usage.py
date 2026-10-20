# Rola pliku: Endpoint zużycia AI workspace'u: wydatki bieżącego miesiąca, budżet i pozostała kwota.

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.usage import UsageRead
from app.services.usage import usage_for

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageRead)
async def read_usage(session: SessionDep, settings: SettingsDep, current: CurrentUserDep) -> UsageRead:
    usage = await usage_for(session, current.workspace_id, settings)
    return UsageRead(period_start=usage.period_start, spent_usd=usage.spent_usd, budget_usd=usage.budget_usd,
                     remaining_usd=usage.remaining_usd, exceeded=usage.exceeded,
                     unknown_cost_calls=usage.unknown_cost_calls)
