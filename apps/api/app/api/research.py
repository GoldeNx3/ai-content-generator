# Rola pliku: Endpointy HTTP zasobu research: przekazują pracę serwisom/repozytoriom i wystawiają wyniki
# oraz błędy przez FastAPI.

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import JobServiceDep, ResearchServiceDep, SessionDep
from app.api.jobs import IdempotencyKey, enqueue_call
from app.schemas.job import JobRead
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


@router.post("", response_model=JobRead, status_code=202)
async def start_research(candidate_id: int, service: JobServiceDep, response: Response,
                         key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.enqueue('research', candidate_id, {'discover': True}, key))


@router.post("/retry", response_model=JobRead, status_code=202)
async def retry_research(candidate_id: int, service: JobServiceDep, response: Response,
                         key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.enqueue('research', candidate_id, {'discover': False}, key))


@router.post("/sources", response_model=ResearchSourceRead, status_code=status.HTTP_201_CREATED)
async def add_manual_source(
    candidate_id: int, payload: ManualSourceCreate, service: ResearchServiceDep, session: SessionDep
) -> ResearchSource:
    """Fetches, extracts and saves a user-provided URL. Run /retry afterwards to include it in the report."""
    from sqlalchemy import select
    from app.models import Candidate
    from app.models.job import Job, ACTIVE_STATUSES
    # Ta sama krótka blokada co enqueue chroni wejście researchu.
    await session.scalar(select(Candidate.id).where(Candidate.id == candidate_id).with_for_update())
    active = await session.scalar(select(Job.id).where(Job.candidate_id == candidate_id, Job.status.in_(ACTIVE_STATUSES)))
    if active:
        raise HTTPException(409, detail={"code": "candidate_busy", "job_id": str(active)})
    return await _call(lambda: service.add_manual_source(candidate_id, str(payload.url)))
