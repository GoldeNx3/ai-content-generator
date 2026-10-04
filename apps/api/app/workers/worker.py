# Rola pliku: Pętla workera — claim, niezależny heartbeat, wykonanie i retry.
# Sesji SQLAlchemy nigdy nie używamy równocześnie w dwóch korutynach.

import asyncio
import contextlib
import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import ArticleFix, ArticleQA, Candidate, Research, ResearchStatus
from app.demo import is_demo_candidate, demo_settings
from app.core.config import Settings
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.services.jobs.errors import LeaseLostError
from app.services.jobs.execution import JobExecution
from app.services.jobs.retry import failure
from app.services.research.errors import NoSourceContentError
from app.workers.calls import CallRecorder
from app.workers.handlers import classify, research, write, qa, auto_fix
from app.workers.providers import providers_for, settings_for

logger = logging.getLogger(__name__)
HANDLERS = {'classify': classify.handle, 'research': research.handle, 'write': write.handle, 'qa_article': qa.handle, 'auto_fix_article': auto_fix.AutoFixArticleHandler().handle}
HEALTH_FILE = Path('/tmp/worker-health.json')


def healthy():
    HEALTH_FILE.write_text(json.dumps({'time': time.time()}))


class Worker:
    def __init__(self, session_factory, settings=None, providers=None, worker_id=None):
        self.sessions = session_factory
        self.settings = settings or get_settings()
        self.providers = providers
        self.worker_id = worker_id or str(uuid4())
        self.stopping = asyncio.Event()
        self.active = None

    async def run_once(self):
        async with self.sessions() as session:
            repository = JobRepository(session)
            await repository.recover_expired()
            job = await repository.claim(self.worker_id, self.settings.job_lease_seconds)
            healthy()
        if job is None:
            return False
        await self.execute(job)
        return True

    async def execute(self, job):
        execution = JobExecution(self.sessions, job)
        providers = self.providers
        heartbeat = asyncio.create_task(self._heartbeat(job))
        try:
            settings = settings_for(job)
            async with self.sessions() as identity_session:
                candidate = await identity_session.get(Candidate, job.candidate_id)
                demo = is_demo_candidate(candidate)
            if demo:
                settings = Settings(**demo_settings(settings.model_dump()))
                from app.workers.demo_providers import demo_providers
                providers = demo_providers()
            else:
                providers = providers or providers_for(settings)
            timeout = getattr(settings, f'job_{job.kind}_timeout_seconds')
            async with self.sessions() as session:
                async with asyncio.timeout(timeout):
                    recorder = CallRecorder(execution, settings.llm_pricing)
                    await HANDLERS[job.kind](job, session, execution, providers, recorder, settings)
        except LeaseLostError:
            logger.warning('Lease lost job_id=%s', job.id)
        except asyncio.CancelledError:
            await self._failed(job, execution, TimeoutError('Worker interrupted'), interrupted=True)
            raise
        except Exception as exc:
            logger.exception('Job failed job_id=%s kind=%s', job.id, job.kind)
            await self._failed(job, execution, exc)
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            if self.providers is None and providers and providers.get('_client'):
                await providers['_client']._client.close()

    async def _heartbeat(self, job):
        while True:
            await asyncio.sleep(self.settings.job_heartbeat_seconds)
            try:
                async with self.sessions() as session:
                    repo = JobRepository(session)
                    renewed = await repo.heartbeat(job.id, job.lease_token, self.settings.job_lease_seconds)
                    await repo.recover_expired()
                if not renewed:
                    if self.active:
                        self.active.cancel()
                    return
                healthy()
            except Exception:
                logger.exception('Heartbeat failed job_id=%s', job.id)
                # Nie przedłużamy lokalnie dzierżawy, gdy baza jest niedostępna.

    async def _failed(self, job, execution, exc, interrupted=False):
        try:
            async with self.sessions() as session:
                current = await execution.lock(session)
                code, retryable, delay = failure(exc, current.attempt_count)
                now = await session.scalar(select(func.clock_timestamp()))
                current.status = 'retrying' if retryable and current.attempt_count < current.max_attempts else 'failed'
                current.error_code = 'worker_interrupted' if interrupted else code
                current.error_message = ('Praca została przerwana; poprzednie wywołanie mogło naliczyć koszt.'
                                         if interrupted else exc.public_message
                                         if isinstance(exc, NoSourceContentError)
                                         else 'Nie udało się wykonać zadania. ' + code)
                current.available_at = now + timedelta(seconds=delay)
                current.finished_at = now if current.status == 'failed' else None
                attempt = await execution.attempt(session)
                attempt.outcome = 'interrupted' if interrupted else ('retryable_error' if current.status == 'retrying' else 'failed')
                attempt.finished_at = now
                attempt.error_code = current.error_code
                attempt.error_message = current.error_message
                attempt.last_stage = current.stage
                if current.kind == 'auto_fix_article':
                    fix = await session.scalar(select(ArticleFix).where(ArticleFix.job_id == current.id))
                    if fix:
                        from app.services.auto_fix.failure import update_failure
                        update_failure(fix, 'failed' if current.status == 'failed' else 'pending', current.error_message)
                if current.kind == 'qa_article':
                    report = await session.scalar(select(ArticleQA).where(ArticleQA.job_id == current.id))
                    if report:
                        report.status = 'failed' if current.status == 'failed' else 'pending'
                if current.kind == 'research' and current.status == 'failed':
                    report = await session.scalar(select(Research).where(Research.job_id == current.id))
                    if report:
                        report.status = ResearchStatus.FAILED
                        report.error = current.error_message
                        report.completed_at = now
                await session.flush()
                if current.locked_until <= await session.scalar(select(func.clock_timestamp())):
                    await session.rollback()
                    raise LeaseLostError('Dzierżawa wygasła podczas zapisu błędu.')
                # Nadal trzymamy sprawdzoną blokadę. Zmiana stanu kończy dzierżawę.
                current.lease_token = None
                current.locked_until = None
                current.worker_id = None
                await session.commit()
        except LeaseLostError:
            pass
        except Exception:
            logger.exception('Cannot save failure job_id=%s; lease recovery will retry', job.id)

    async def run(self):
        HEALTH_FILE.unlink(missing_ok=True)
        while not self.stopping.is_set():
            try:
                self.active = asyncio.create_task(self.run_once())
                stop = asyncio.create_task(self.stopping.wait())
                done, _ = await asyncio.wait((self.active, stop), return_when=asyncio.FIRST_COMPLETED)
                if stop in done:
                    try:
                        await asyncio.wait_for(asyncio.shield(self.active), timeout=30)
                    except TimeoutError:
                        self.active.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await self.active
                    break
                stop.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stop
                await self.active
            except Exception:
                logger.exception('Worker loop failed')
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=self.settings.job_poll_seconds)
            except TimeoutError:
                pass
