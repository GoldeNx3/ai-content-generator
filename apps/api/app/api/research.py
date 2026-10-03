# Rola pliku: Endpointy HTTP zasobu research: przekazują pracę serwisom/repozytoriom i wystawiają wyniki
# oraz błędy przez FastAPI.

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import ResearchRunnerDep, ResearchServiceDep
from app.models import Research, ResearchSource
from app.schemas.research import ManualSourceCreate, ResearchRead, ResearchSourceRead
from app.services.research.research import (
    CandidateNotFoundError,
    DuplicateSourceError,
    ResearchError,
    ResearchInProgressError,
    ResearchNotFoundError,
)

router = APIRouter(prefix="/candidates/{candidate_id}/research", tags=["research"])

T = TypeVar("T")

_ERROR_STATUS: dict[type[ResearchError], int] = {
    CandidateNotFoundError: status.HTTP_404_NOT_FOUND,
    ResearchNotFoundError: status.HTTP_404_NOT_FOUND,
    ResearchInProgressError: status.HTTP_409_CONFLICT,
    DuplicateSourceError: status.HTTP_409_CONFLICT,
}


# Wspólna granica API: wyjątki domenowe z serwisu są tłumaczone na odpowiedzi HTTP dla klienta.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def _call(fn: Callable[[], Awaitable[T]]) -> T:
    try:
        return await fn()
    except ResearchError as exc:
        code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        raise HTTPException(code, detail=str(exc)) from exc


@router.get("", response_model=ResearchRead)
async def get_research(candidate_id: int, service: ResearchServiceDep) -> Research:
    research = await service.get_for_candidate(candidate_id)
    if research is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Research not found")
    return research


@router.post("", response_model=ResearchRead, status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    candidate_id: int, service: ResearchServiceDep, runner: ResearchRunnerDep, background: BackgroundTasks
) -> Research:
    """Starts a full research (fetch original, discover sources, LLM analysis) in the background.

    Poll GET /research until status is completed or failed.
    """
    research = await _call(lambda: service.start(candidate_id, discover=True))
    background.add_task(runner, research.id, True)
    return research


@router.post("/retry", response_model=ResearchRead, status_code=status.HTTP_202_ACCEPTED)
async def retry_research(
    candidate_id: int, service: ResearchServiceDep, runner: ResearchRunnerDep, background: BackgroundTasks
) -> Research:
    """Re-runs the analysis on the existing sources (incl. manual ones); refetches failed sources."""
    research = await _call(lambda: service.start(candidate_id, discover=False))
    background.add_task(runner, research.id, False)
    return research


@router.post("/sources", response_model=ResearchSourceRead, status_code=status.HTTP_201_CREATED)
async def add_manual_source(
    candidate_id: int, payload: ManualSourceCreate, service: ResearchServiceDep
) -> ResearchSource:
    """Fetches, extracts and saves a user-provided URL. Run /retry afterwards to include it in the report."""
    return await _call(lambda: service.add_manual_source(candidate_id, str(payload.url)))
