# Rola pliku: Odczyt trwałego stanu i enqueue. Żaden endpoint nie wykonuje LLM.

from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Header, HTTPException, Query, Response
from sqlalchemy import func, select

from app.api.deps import JobServiceDep, SessionDep
from app.models import Candidate
from app.models.job import ACTIVE_STATUSES, Job, JobAttempt
from app.schemas.job import JobRead, JobAttemptRead, JobPage, JobStats
from app.services.jobs.errors import JobConflict, JobInputError

router = APIRouter(tags=['jobs'])
IdempotencyKey = Annotated[UUID | None, Header(alias='Idempotency-Key')]


async def enqueue_call(response: Response, action):
    try:
        job = await action()
    except JobConflict as exc:
        raise HTTPException(409, detail={'code': exc.code, 'job_id': str(exc.job_id) if exc.job_id else None}) from exc
    except JobInputError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc
    response.headers['Location'] = f'/api/jobs/{job.id}'
    return job


@router.get('/jobs', response_model=JobPage)
async def queue_jobs(session: SessionDep,
                     status: str = 'active',
                     kind: Literal['classify', 'research', 'write', 'qa_article', 'auto_fix_article', 'prepare_wordpress', 'publish_wordpress'] | None = None,
                     candidate_id: Annotated[int | None, Query(ge=1)] = None,
                     page: Annotated[int, Query(ge=1)] = 1,
                     page_size: Annotated[int, Query(ge=1, le=100)] = 25):
    # Domyślne active zachowuje dotychczasowy kontrakt dashboardu.
    # Panel kolejki używa all albo konkretnego statusu, również zakończonego.
    conditions = []
    if status == 'active':
        conditions.append(Job.status.in_(ACTIVE_STATUSES))
    elif status != 'all':
        if status not in (*ACTIVE_STATUSES, 'failed', 'succeeded'):
            raise HTTPException(422, 'Invalid job status')
        conditions.append(Job.status == status)
    if kind:
        conditions.append(Job.kind == kind)
    if candidate_id is not None:
        conditions.append(Job.candidate_id == candidate_id)
    total = await session.scalar(select(func.count(Job.id)).where(*conditions))
    rows = (await session.execute(select(Job, Candidate.title).join(Candidate, Candidate.id == Job.candidate_id)
            .where(*conditions).order_by(Job.created_at.desc(), Job.id.desc())
            .offset((page-1)*page_size).limit(page_size))).all()
    items = [JobRead.model_validate(job).model_copy(update={'candidate_title': title}) for job, title in rows]
    return JobPage(items=items, total=total, page=page, page_size=page_size)


# Trasa statyczna musi występować przed /jobs/{job_id}, żeby stats nie był UUID.
@router.get('/jobs/stats', response_model=JobStats)
async def queue_stats(session: SessionDep):
    counts = dict((await session.execute(select(Job.status, func.count(Job.id)).group_by(Job.status))).all())
    return JobStats(**counts, total=sum(counts.values()))


@router.get('/jobs/{job_id}', response_model=JobRead)
async def get_job(job_id: UUID, session: SessionDep):
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, 'Job not found')
    return job


@router.get('/jobs/{job_id}/attempts', response_model=list[JobAttemptRead])
async def attempts(job_id: UUID, session: SessionDep):
    if await session.get(Job, job_id) is None:
        raise HTTPException(404, 'Job not found')
    return (await session.scalars(select(JobAttempt).where(JobAttempt.job_id == job_id)
                                 .order_by(JobAttempt.number))).all()


@router.get('/candidates/{candidate_id}/jobs', response_model=JobPage)
async def list_jobs(candidate_id: int, session: SessionDep,
                    status: str | None = None, page: Annotated[int, Query(ge=1)] = 1,
                    page_size: Annotated[int, Query(ge=1, le=100)] = 25):
    if await session.get(Candidate, candidate_id) is None:
        raise HTTPException(404, 'Candidate not found')
    conditions = [Job.candidate_id == candidate_id]
    if status == 'active':
        conditions.append(Job.status.in_(ACTIVE_STATUSES))
    elif status:
        if status not in (*ACTIVE_STATUSES, 'failed', 'succeeded'):
            raise HTTPException(422, 'Invalid job status')
        conditions.append(Job.status == status)
    total = await session.scalar(select(func.count(Job.id)).where(*conditions))
    items = (await session.scalars(select(Job).where(*conditions)
             .order_by(Job.created_at.desc(), Job.id.desc()).offset((page-1)*page_size).limit(page_size))).all()
    return JobPage(items=[JobRead.model_validate(job) for job in items], total=total, page=page, page_size=page_size)


@router.post('/jobs/{job_id}/retry', response_model=JobRead, status_code=202)
async def retry_job(job_id: UUID, service: JobServiceDep, response: Response, key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.retry(job_id, key))
