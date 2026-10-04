# Rola pliku: Endpointy HTTP zasobu sources: przekazują pracę serwisom/repozytoriom i wystawiają wyniki
# oraz błędy przez FastAPI.

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import IngestionDep, SessionDep
from app.models import Source
from app.repositories.source_repository import SourceRepository
from app.schemas.source import FetchResult, SourceCreate, SourceRead, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


# Pobranie rekordu i sprawdzenie braku danych są wspólne dla endpointów, które potrzebują istniejącego zasobu.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def _get_or_404(repo: SourceRepository, source_id: int) -> Source:
    source = await repo.get(source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.get("", response_model=list[SourceRead])
async def list_sources(session: SessionDep) -> list[Source]:
    return list(await SourceRepository(session).list_all())


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreate, session: SessionDep) -> Source:
    repo = SourceRepository(session)
    url = str(payload.url)
    if await repo.get_by_url(url):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Source with this URL already exists")
    source = await repo.add(
        Source(name=payload.name.strip(), url=url, type=payload.type, active=payload.active)
    )
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
    await session.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(source_id: int, payload: SourceUpdate, session: SessionDep) -> Source:
    repo = SourceRepository(session)
    source = await _get_or_404(repo, source_id)
    if payload.name is not None:
        source.name = payload.name.strip()
    if payload.url is not None:
        url = str(payload.url)
        existing = await repo.get_by_url(url)
        if existing and existing.id != source.id:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Source with this URL already exists")
        source.url = url
    if payload.active is not None:
        source.active = payload.active
    await session.commit()
    await session.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: int, session: SessionDep) -> Response:
    repo = SourceRepository(session)
    from sqlalchemy import select
    from app.models import Candidate
    from app.models.job import Job
    await _get_or_404(repo, source_id)
    ids = (await session.scalars(select(Candidate.id).where(Candidate.source_id == source_id).with_for_update())).all()
    if ids and await session.scalar(select(Job.id).where(Job.candidate_id.in_(ids)).limit(1)):
        raise HTTPException(409, 'Źródło ma historię zadań i nie może zostać usunięte.')
    await repo.delete(await _get_or_404(repo, source_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/fetch", response_model=FetchResult)
async def fetch_all_sources(ingestion: IngestionDep) -> FetchResult:
    return await ingestion.fetch_all_active()


@router.post("/{source_id}/fetch", response_model=FetchResult)
async def fetch_source(source_id: int, session: SessionDep, ingestion: IngestionDep) -> FetchResult:
    source = await _get_or_404(SourceRepository(session), source_id)
    return await ingestion.fetch_source(source)
