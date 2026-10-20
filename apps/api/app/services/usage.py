# Rola pliku: Zużycie i budżet AI workspace'u. Źródłem kosztów są zapisy płatnych wywołań w próbach
# jobów (JobAttempt.llm_calls, CallRecorder), więc liczą się także ponowienia i nieudane próby.
# Budżet blokuje nowe płatne zadania; zadanie już zlecone może przekroczyć limit o swój koszt.

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Numeric, cast, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Workspace
from app.models.job import Job, JobAttempt
from app.services.jobs.errors import JobInputError

# Zadania bez wywołań LLM nie podlegają budżetowi (prepare_wordpress może generować SEO, więc jest płatne).
FREE_KINDS = frozenset({"publish_wordpress"})


@dataclass(frozen=True)
class Usage:
    period_start: datetime
    spent_usd: Decimal
    budget_usd: Decimal | None
    unknown_cost_calls: int

    @property
    def remaining_usd(self) -> Decimal | None:
        return None if self.budget_usd is None else max(self.budget_usd - self.spent_usd, Decimal("0"))

    @property
    def exceeded(self) -> bool:
        return self.budget_usd is not None and self.spent_usd >= self.budget_usd


def period_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def budget_for(session: AsyncSession, workspace_id: int, settings: Settings) -> Decimal | None:
    own = await session.scalar(select(Workspace.monthly_budget_usd).where(Workspace.id == workspace_id))
    if own is not None:
        return Decimal(own)
    default = settings.default_monthly_budget_usd
    return None if default is None else Decimal(str(default))


async def usage_for(session: AsyncSession, workspace_id: int, settings: Settings, now: datetime | None = None) -> Usage:
    start = period_start(now)
    call = func.jsonb_array_elements(JobAttempt.llm_calls).table_valued("value").alias("call")
    cost = call.c.value.op("->>")(literal_column("'estimated_cost_usd'"))
    finished = call.c.value.op("->>")(literal_column("'finished'"))
    row = (await session.execute(
        select(func.coalesce(func.sum(cast(cost, Numeric)), 0),
               func.count().filter((cost.is_(None)) & (finished == "false")))
        .select_from(JobAttempt).join(Job, Job.id == JobAttempt.job_id).join(call, literal_column("true"))
        .where(Job.workspace_id == workspace_id, JobAttempt.started_at >= start)
    )).one()
    return Usage(start, Decimal(row[0]).quantize(Decimal("0.000001")), await budget_for(session, workspace_id, settings),
                 int(row[1] or 0))


async def ensure_budget(session: AsyncSession, workspace_id: int, settings: Settings) -> None:
    """Blokuje nowe płatne zadanie, gdy workspace wyczerpał budżet bieżącego miesiąca."""
    if (await budget_for(session, workspace_id, settings)) is None:
        return
    if (await usage_for(session, workspace_id, settings)).exceeded:
        raise JobInputError("budget_exceeded", 402)
