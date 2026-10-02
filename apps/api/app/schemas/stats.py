from pydantic import BaseModel


class DashboardStats(BaseModel):
    candidates_today: int
    new_today: int
    approved: int
    ignored: int
    average_score: float | None
