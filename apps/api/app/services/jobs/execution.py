# Rola pliku: Fencing — kontroluje prawo próby do KAŻDEGO trwałego zapisu.
# Osobne sesje dla postępu i heartbeat nie są współdzielone z sesją serwisu.

from sqlalchemy import func, select, text

from app.models import WordPressPublication, ArticleFix, ArticleQA, Article, Candidate, Research
from app.models.job import Job, JobAttempt
from app.services.jobs.errors import LeaseLostError


class JobExecution:
    def __init__(self, session_factory, job: Job) -> None:
        self.sessions = session_factory
        self.job_id = job.id
        self.token = job.lease_token
        self.attempt_number = job.attempt_count
        self.checkpoints = dict(job.checkpoints)

    async def lock(self, session) -> Job:
        # no_autoflush zapobiega wysłaniu zmienionych obiektów przed kontrolą.
        with session.no_autoflush:
            await session.execute(text("SET LOCAL lock_timeout = '5s'"))
            await session.execute(text("SET LOCAL statement_timeout = '10s'"))
            job = await session.scalar(select(Job).where(Job.id == self.job_id).with_for_update())
            now = await session.scalar(select(func.clock_timestamp()))
            state = (await session.execute(select(Job.status, Job.lease_token, Job.locked_until)
                                           .where(Job.id == self.job_id))).one_or_none()
        if state is None or state.status != 'running' or state.lease_token != self.token or state.locked_until <= now:
            await session.rollback()
            raise LeaseLostError('Dzierżawa zadania wygasła lub zmieniła właściciela.')
        job.locked_until = state.locked_until
        return job

    async def commit(self, session, result=None, checkpoint: dict | None = None, successor=None) -> None:
        job = await self.lock(session)
        if checkpoint:
            self.checkpoints.update(checkpoint)
        job.checkpoints = dict(self.checkpoints)
        if result is not None:
            if isinstance(result, WordPressPublication):
                result.job_id = job.id
                job.result_type = "wordpress_publication"
            elif isinstance(result, ArticleFix):
                result.job_id = job.id
                job.result_type = 'article_fix'
            elif isinstance(result, ArticleQA):
                result.job_id = job.id
                job.result_type = 'article_qa'
            elif isinstance(result, Article):
                result.generation_job_id = job.id
                job.result_type = 'article'
            elif isinstance(result, Research):
                result.job_id = job.id
                job.result_type = 'research'
            elif isinstance(result, Candidate):
                result.classification_job_id = job.id
                job.result_type = 'candidate'
            else:
                raise TypeError('Nieznany rodzaj wyniku zadania')
            await session.flush()
            job.result_id = result.id
            job.status = 'succeeded'
            job.stage = 'saving'
            job.finished_at = await session.scalar(select(func.clock_timestamp()))
            job.error_code = job.error_message = None
            attempt = await self.attempt(session)
            attempt.outcome = 'succeeded'
            attempt.finished_at = job.finished_at
            attempt.last_stage = job.stage
        await session.flush()
        if successor is not None:
            await successor()
        now = await session.scalar(select(func.clock_timestamp()))
        if job.locked_until <= now:
            await session.rollback()
            raise LeaseLostError('Dzierżawa wygasła podczas zapisu.')
        if result is not None:
            # Po sukcesie nie ma już właściciela ani prawa do kolejnych zapisów.
            job.lease_token = job.worker_id = job.locked_until = None
        await session.commit()

    async def attempt(self, session) -> JobAttempt:
        return await session.scalar(select(JobAttempt).where(
            JobAttempt.job_id == self.job_id, JobAttempt.number == self.attempt_number))

    async def stage(self, stage: str) -> None:
        async with self.sessions() as session:
            job = await self.lock(session)
            job.stage = stage
            attempt = await self.attempt(session)
            attempt.last_stage = stage
            await self.commit(session)

    async def record_call(self, stage, record, checkpoint=None) -> None:
        async with self.sessions() as session:
            job = await self.lock(session)
            attempt = await self.attempt(session)
            calls = list(attempt.llm_calls)
            if record.get('finished') and calls and calls[-1]['stage'] == stage:
                calls[-1] = {**calls[-1], **record}
            else:
                calls.append({'stage': stage, **record})
            attempt.llm_calls = calls
            await self.commit(session, checkpoint=checkpoint)

    async def checkpoint(self, key, data) -> None:
        async with self.sessions() as session:
            await self.commit(session, checkpoint={key: data})
