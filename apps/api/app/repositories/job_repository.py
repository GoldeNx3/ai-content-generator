# Rola pliku: SQL kolejki — claim, heartbeat i odzyskiwanie zadań.
# Blokada istnieje tylko w krótkiej transakcji, nigdy podczas żądania LLM.

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobAttempt
from app.models import Research, ResearchStatus


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim(self, worker_id: str, lease_seconds: float = 60) -> Job | None:
        query = (select(Job).where(Job.status.in_(('queued', 'retrying')),
                                  Job.available_at <= func.clock_timestamp())
                 .order_by(Job.available_at, Job.created_at, Job.id)
                 .with_for_update(skip_locked=True).limit(1))
        job = await self.session.scalar(query.execution_options(populate_existing=True))
        if job is None:
            await self.session.rollback()
            return None
        now = await self.session.scalar(select(func.clock_timestamp()))
        job.status = 'running'
        job.attempt_count += 1
        job.worker_id = worker_id
        job.lease_token = uuid4()
        job.started_at = job.started_at or now
        job.heartbeat_at = now
        job.locked_until = now + timedelta(seconds=lease_seconds)
        job.finished_at = None
        self.session.add(JobAttempt(job_id=job.id, number=job.attempt_count, worker_id=worker_id))
        await self.session.commit()
        return job

    async def heartbeat(self, job_id, token, lease_seconds: float = 60) -> bool:
        # UPDATE jest warunkowy: wygasłego tokenu nie wolno „ożywić”.
        result = await self.session.execute(
            update(Job).where(Job.id == job_id, Job.status == 'running',
                              Job.lease_token == token, Job.locked_until > func.clock_timestamp())
            .values(heartbeat_at=func.clock_timestamp(),
                    locked_until=func.clock_timestamp() + timedelta(seconds=lease_seconds))
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return result.rowcount == 1

    async def recover_expired(self) -> int:
        jobs = (await self.session.scalars(
            select(Job).where(Job.status == 'running', Job.locked_until <= func.clock_timestamp())
            .with_for_update(skip_locked=True).execution_options(populate_existing=True)
        )).all()
        now = await self.session.scalar(select(func.clock_timestamp()))
        for job in jobs:
            attempt = await self.session.scalar(select(JobAttempt).where(
                JobAttempt.job_id == job.id, JobAttempt.number == job.attempt_count))
            if attempt:
                attempt.outcome = 'interrupted'
                attempt.finished_at = now
                attempt.error_code = 'worker_lost'
                attempt.last_stage = job.stage
            job.status = 'retrying' if job.attempt_count < job.max_attempts else 'failed'
            job.available_at = now + timedelta(seconds=15 if job.attempt_count == 1 else 60)
            job.finished_at = now if job.status == 'failed' else None
            job.error_code = 'worker_lost'
            job.error_message = 'Worker został przerwany; poprzednie wywołanie mogło naliczyć koszt.'
            job.lease_token = None
            job.worker_id = None
            job.locked_until = None
            if job.kind == 'research' and job.status == 'failed':
                report = await self.session.scalar(select(Research).where(Research.job_id == job.id))
                if report:
                    report.status = ResearchStatus.FAILED
                    report.error = job.error_message
                    report.completed_at = now
        await self.session.commit()
        return len(jobs)
