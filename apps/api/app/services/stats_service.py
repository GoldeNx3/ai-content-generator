# Rola pliku: Buduje dane kart dashboardu z zapytań repozytorium, zamiast liczyć statystyki po stronie
# przeglądarki.

from datetime import UTC, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, CandidateStatus
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.stats import DashboardStats


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def get_dashboard_stats(session: AsyncSession, workspace_id: int) -> DashboardStats:
    repo = CandidateRepository(session)
    in_workspace = Candidate.workspace_id == workspace_id
    start_of_day = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    return DashboardStats(
        candidates_today=await repo.count_created_since(start_of_day, workspace_id),
        new_today=await repo.count_created_since(start_of_day, workspace_id, CandidateStatus.PENDING),
        approved=await repo.count(Candidate.status == CandidateStatus.APPROVED, in_workspace),
        ignored=await repo.count(Candidate.status == CandidateStatus.IGNORED, in_workspace),
        average_score=await repo.average_score(workspace_id),
    )
