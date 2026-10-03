# Rola pliku: Endpointy HTTP zasobu candidates: przekazują pracę serwisom/repozytoriom i wystawiają
# wyniki oraz błędy przez FastAPI.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import ProviderDep, SessionDep
from app.core.config import get_settings
from app.models import Candidate
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.candidate import CandidateFilters, CandidatePage, CandidateRead, CandidateStatusUpdate
from app.schemas.classification import ClassifyBatchResult
from app.services.classification_service import ClassificationService
from app.services.llm.base import LLMError, LLMNotConfiguredError

router = APIRouter(prefix="/candidates", tags=["candidates"])


# Pobranie rekordu i sprawdzenie braku danych są wspólne dla endpointów, które potrzebują istniejącego zasobu.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def _get_or_404(session: SessionDep, candidate_id: int) -> Candidate:
    candidate = await CandidateRepository(session).get(candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


# Depends wskazuje fabrykę zależności; FastAPI dostarcza jej wynik jako argument endpointu lub kolejnej
# fabryki.
@router.get("", response_model=CandidatePage)
async def list_candidates(
    session: SessionDep, filters: Annotated[CandidateFilters, Depends()]
) -> CandidatePage:
    items, total = await CandidateRepository(session).search(filters)
    return CandidatePage(
        items=[CandidateRead.model_validate(item) for item in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@router.post("/classify-pending", response_model=ClassifyBatchResult)
async def classify_pending(
    session: SessionDep,
    provider: ProviderDep,
    limit: Annotated[int | None, Query(ge=1, le=1000, description="Defaults to CLASSIFY_BATCH_LIMIT")] = None,
) -> ClassifyBatchResult:
    try:
        return await ClassificationService(session, provider).classify_pending(
            limit or get_settings().classify_batch_limit
        )
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(candidate_id: int, session: SessionDep) -> Candidate:
    return await _get_or_404(session, candidate_id)


@router.post("/{candidate_id}/classify", response_model=CandidateRead)
async def classify_candidate(candidate_id: int, session: SessionDep, provider: ProviderDep) -> Candidate:
    candidate = await _get_or_404(session, candidate_id)
    try:
        return await ClassificationService(session, provider).classify(candidate)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.patch("/{candidate_id}/status", response_model=CandidateRead)
async def update_status(
    candidate_id: int, payload: CandidateStatusUpdate, session: SessionDep
) -> Candidate:
    candidate = await _get_or_404(session, candidate_id)
    candidate.status = payload.status
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
    await session.refresh(candidate)
    return candidate
