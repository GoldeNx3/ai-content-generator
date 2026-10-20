# Rola pliku: Schemat zużycia AI workspace'u w bieżącym miesiącu (UTC) względem budżetu.

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class UsageRead(BaseModel):
    period_start: datetime
    spent_usd: Decimal
    # None = bez limitu.
    budget_usd: Decimal | None
    remaining_usd: Decimal | None
    exceeded: bool
    # Wywołania przerwane przed zapisem kosztu (np. awaria workera): koszt nieznany, nie wliczony.
    unknown_cost_calls: int
