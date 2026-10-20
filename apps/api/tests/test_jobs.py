# Rola pliku: Kontrakty trwałej kolejki na prawdziwej bazie PostgreSQL.
# Osobne sesje udają niezależne procesy workerów; nie mockujemy blokad SQL.

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.models import Candidate, Source
from app.core.config import Settings
from app.models.job import Job, JobAttempt
from app.repositories.job_repository import JobRepository
from app.services.jobs.errors import JobConflict, LeaseLostError
from app.services.jobs.execution import JobExecution
from app.services.jobs.service import JobService


async def candidate_for(session, source):
    candidate = Candidate(workspace_id=1, source_id=source.id, external_url='https://example.com/job', title='Job')
    session.add(candidate)
    await session.commit()
    return candidate


async def test_enqueue_is_durable_and_idempotent(session, source):
    candidate = await candidate_for(session, source)
    key = uuid4()
    service = JobService(session, settings=Settings(openai_api_key='test'))
    first = await service.enqueue('classify', candidate.id, key=key)
    second = await service.enqueue('classify', candidate.id, key=key)
    assert first.id == second.id
    assert first.status == 'queued'
    with pytest.raises(JobConflict):
        await service.enqueue('research', candidate.id, key=key)
    with pytest.raises(JobConflict):
        await service.enqueue('classify', candidate.id, key=uuid4())


async def test_two_workers_claim_once(session, session_factory, source):
    candidate = await candidate_for(session, source)
    job = await JobService(session, settings=Settings(openai_api_key='test')).enqueue('classify', candidate.id)
    async def claim(worker):
        async with session_factory() as db:
            return await JobRepository(db).claim(worker, lease_seconds=60)
    results = await asyncio.gather(claim('one'), claim('two'))
    claimed = [result for result in results if result is not None]
    assert len(claimed) == 1
    assert claimed[0].id == job.id
    assert claimed[0].attempt_count == 1


async def test_expired_worker_cannot_publish(session, session_factory, source):
    candidate = await candidate_for(session, source)
    job = await JobService(session, settings=Settings(openai_api_key='test')).enqueue('classify', candidate.id)
    claimed = await JobRepository(session).claim('old', 60)
    execution = JobExecution(session_factory, claimed)
    old_token = claimed.lease_token
    await session.execute(text("UPDATE jobs SET locked_until = clock_timestamp() - interval '1 second' WHERE id=:id"), {'id': job.id})
    await session.commit()
    assert await JobRepository(session).recover_expired() == 1
    await session.execute(text('UPDATE jobs SET available_at=clock_timestamp() WHERE id=:id'), {'id': job.id})
    await session.commit()
    replacement = await JobRepository(session).claim('new', 60)
    assert replacement.lease_token != old_token
    async with session_factory() as db:
        item = await db.get(Candidate, candidate.id)
        item.title = 'Stary worker nadpisuje dane'
        with pytest.raises(LeaseLostError):
            await execution.commit(db, result=item)
    await session.refresh(candidate)
    assert candidate.title == 'Job'


async def test_result_and_success_share_one_commit(session, session_factory, source):
    candidate = await candidate_for(session, source)
    await JobService(session, settings=Settings(openai_api_key='test')).enqueue('classify', candidate.id)
    claimed = await JobRepository(session).claim('worker', 60)
    execution = JobExecution(session_factory, claimed)
    async with session_factory() as db:
        item = await db.get(Candidate, candidate.id)
        item.total_score = 88
        await execution.commit(db, result=item)
    await session.refresh(candidate)
    await session.refresh(claimed)
    assert candidate.total_score == 88
    assert claimed.status == 'succeeded'
    assert claimed.result_id == candidate.id
    assert candidate.classification_job_id == claimed.id
    attempts = (await session.scalars(select(JobAttempt).where(JobAttempt.job_id == claimed.id))).all()
    assert attempts[0].outcome == 'succeeded'


async def test_heartbeat_does_not_revive_expired_lease(session, source):
    candidate = await candidate_for(session, source)
    await JobService(session, settings=Settings(openai_api_key='test')).enqueue('classify', candidate.id)
    claimed = await JobRepository(session).claim('worker', 60)
    await session.execute(text("UPDATE jobs SET locked_until=clock_timestamp()-interval '1 second' WHERE id=:id"), {'id': claimed.id})
    await session.commit()
    assert not await JobRepository(session).heartbeat(claimed.id, claimed.lease_token, 60)


async def test_worker_classifies_without_browser(session, session_factory, source):
    from app.workers.worker import Worker
    from tests.test_classification import FakeProvider
    candidate = await candidate_for(session, source)
    job = await JobService(session, Settings(openai_api_key='test')).enqueue('classify', candidate.id)
    worker = Worker(session_factory, providers={'classify': FakeProvider()})
    assert await worker.run_once()
    await session.refresh(job)
    await session.refresh(candidate)
    assert job.status == 'succeeded'
    assert candidate.total_score == 79


async def test_write_retry_reuses_brief(session, session_factory):
    from app.workers.worker import Worker
    from app.services.llm.base import LLMError
    from tests.article_fakes import FakeArticleLLM, research_fixture
    candidate, _ = await research_fixture(session)
    class RetryWriter(FakeArticleLLM):
        async def write_article(self, context, brief):
            if not self.briefs:
                self.briefs.append(brief)
                raise LLMError('Temporary', retryable=True)
            return await super().write_article(context, brief)
    provider = RetryWriter()
    job = await JobService(session, Settings(openai_api_key='test')).enqueue('write', candidate.id)
    worker = Worker(session_factory, providers={'write': provider})
    await worker.run_once()
    await session.refresh(job)
    assert job.status == 'retrying'
    await session.execute(text('UPDATE jobs SET available_at=clock_timestamp() WHERE id=:id'), {'id': job.id})
    await session.commit()
    await worker.run_once()
    await session.refresh(job)
    assert job.status == 'succeeded'
    assert job.attempt_count == 2
    assert len(provider.contexts) == 1  # brief tylko raz, writer ponowiony
    attempts = (await session.scalars(select(JobAttempt).where(JobAttempt.job_id == job.id)
                                     .order_by(JobAttempt.number))).all()
    assert attempts[0].llm_calls[0]['finished'] is True
    assert attempts[0].llm_calls[-1]['finished'] is False
    assert attempts[1].llm_calls[0]['stage'] == 'writing'


async def test_worker_research_completes(session, session_factory, source):
    from app.workers.worker import Worker
    from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for, html_response
    candidate = await candidate_for(session, source)
    job = await JobService(session, Settings(openai_api_key='test')).enqueue('research', candidate.id)
    providers = {'research': FakeResearchLLM(), 'search': FakeSearch(),
                 'extractor': extractor_for({candidate.external_url: html_response('Job')})}
    await Worker(session_factory, providers=providers).run_once()
    await session.refresh(job)
    assert job.status == 'succeeded'
    from app.models import Research
    report = await session.get(Research, job.result_id)
    assert report.status == 'completed'
    assert len(report.sources) == 1
    assert len(report.facts) == 2


async def test_worker_research_without_content_reports_actionable_error(session, session_factory, source):
    from app.models import Research
    from app.workers.worker import Worker
    from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for
    candidate = await candidate_for(session, source)
    job = await JobService(session, Settings(openai_api_key='test')).enqueue('research', candidate.id)
    providers = {'research': FakeResearchLLM(), 'search': FakeSearch(),
                 'extractor': extractor_for({})}
    await Worker(session_factory, providers=providers).run_once()
    await session.refresh(job)
    assert job.status == 'failed'
    assert job.error_code == 'no_source_content'
    assert 'Dodaj dostępne źródło ręcznie' in job.error_message
    assert job.attempt_count == 1
    report = await session.get(Research, job.checkpoints['research_id'])
    assert report.status == 'failed'
    assert report.error == job.error_message
    assert len(report.sources) == 1
    assert report.sources[0].fetch_status == 'failed'


async def test_heartbeat_continues_during_llm_request(session, session_factory, source):
    from app.workers.worker import Worker
    from tests.test_classification import FakeProvider
    candidate = await candidate_for(session, source)
    class SlowProvider(FakeProvider):
        async def classify_candidate(self, value):
            await asyncio.sleep(0.35)  # dłużej niż pierwsza dzierżawa
            return await super().classify_candidate(value)
    settings = Settings(openai_api_key='test', job_heartbeat_seconds=0.03, job_lease_seconds=0.2)
    job = await JobService(session, settings).enqueue('classify', candidate.id)
    await Worker(session_factory, settings=settings, providers={'classify': SlowProvider()}).run_once()
    await session.refresh(job)
    assert job.status == 'succeeded'
    assert job.attempt_count == 1
    assert job.heartbeat_at > job.started_at


async def test_research_retry_keeps_discovered_sources(session, session_factory, source):
    from app.workers.worker import Worker
    from app.models import Research
    from app.services.llm.base import LLMError
    from app.services.research.search import SearchResult
    from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for, html_response
    candidate = await candidate_for(session, source)
    extra = 'https://example.com/extra'
    class RetryResearch(FakeResearchLLM):
        calls = 0
        async def research(self, value, documents):
            self.calls += 1
            if self.calls == 1:
                raise LLMError('Transient', retryable=True)
            return await super().research(value, documents)
    search = FakeSearch([SearchResult(url=extra, title='Extra', snippet='Details')])
    provider = RetryResearch()
    job = await JobService(session, Settings(openai_api_key='test')).enqueue('research', candidate.id)
    worker = Worker(session_factory, providers={'research': provider, 'search': search,
        'extractor': extractor_for({candidate.external_url: html_response('Job'), extra: html_response('Extra')})})
    await worker.run_once()
    await session.refresh(job)
    assert job.status == 'retrying'
    report = await session.get(Research, job.checkpoints['research_id'])
    before = [(item.id, item.url) for item in report.sources]
    assert len(before) == 2
    query_count = len(search.queries)
    await session.execute(text('UPDATE jobs SET available_at=clock_timestamp() WHERE id=:id'), {'id': job.id})
    await session.commit()
    await worker.run_once()
    await session.refresh(job)
    await session.refresh(report)
    assert job.status == 'succeeded'
    assert [(item.id, item.url) for item in report.sources] == before
    assert len(search.queries) == query_count
    assert report.llm_input_tokens == 1_000_100


async def test_last_expired_attempt_fails_research(session, session_factory, source):
    from app.models import Research, ResearchStatus
    from app.services.research.research import ResearchService
    from app.services.llm.cost import LLMCostCalculator
    from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for
    candidate = await candidate_for(session, source)
    settings = Settings(openai_api_key='test', job_max_attempts=1)
    job = await JobService(session, settings).enqueue('research', candidate.id)
    claimed = await JobRepository(session).claim('crashed')
    async with session_factory() as db:
        service = ResearchService(db, extractor_for({}), FakeSearch(), FakeResearchLLM(),
            LLMCostCalculator(settings.llm_pricing), settings, JobExecution(session_factory, claimed))
        report = await service.start(candidate.id, discover=True)
        report_id = report.id
    await session.execute(text("UPDATE jobs SET locked_until=clock_timestamp()-interval '1 second' WHERE id=:id"), {'id': job.id})
    await session.commit()
    await JobRepository(session).recover_expired()
    await session.refresh(job)
    report = await session.get(Research, report_id)
    assert job.status == 'failed'
    assert report.status == ResearchStatus.FAILED
    assert report.completed_at is not None


async def test_job_timeout_is_retryable(session, session_factory, source):
    from app.workers.worker import Worker
    from tests.test_classification import FakeProvider
    candidate = await candidate_for(session, source)
    class SlowProvider(FakeProvider):
        async def classify_candidate(self, value):
            await asyncio.sleep(1)
            return await super().classify_candidate(value)
    settings = Settings(openai_api_key='test', job_classify_timeout_seconds=0.1)
    job = await JobService(session, settings).enqueue('classify', candidate.id)
    await Worker(session_factory, settings=settings, providers={'classify': SlowProvider()}).run_once()
    await session.refresh(job)
    await session.refresh(candidate)
    assert job.status == 'retrying'
    assert job.error_code == 'timeout'
    assert candidate.total_score is None


async def test_parallel_enqueue_preserves_single_active_job(session, session_factory, source):
    candidate = await candidate_for(session, source)
    async def enqueue():
        async with session_factory() as db:
            try:
                return await JobService(db, Settings(openai_api_key='test')).enqueue('classify', candidate.id)
            except JobConflict as exc:
                return exc
    results = await asyncio.gather(enqueue(), enqueue())
    assert sum(isinstance(item, Job) for item in results) == 1
    conflict = next(item for item in results if isinstance(item, JobConflict))
    assert conflict.code == 'job_already_active'
    assert conflict.job_id == next(item.id for item in results if isinstance(item, Job))


async def test_batch_replay_does_not_enqueue_next_paid_batch(session, session_factory, source):
    from app.workers.worker import Worker
    from tests.test_classification import FakeProvider
    await candidate_for(session, source)
    other = Candidate(workspace_id=1, source_id=source.id, external_url='https://example.com/second', title='Second')
    session.add(other)
    await session.commit()
    key = uuid4()
    service = JobService(session, Settings(openai_api_key='test'))
    initial = await service.batch(1, key, workspace_id=1)
    await Worker(session_factory, providers={'classify': FakeProvider()}).run_once()
    repeated = await service.batch(1, key, workspace_id=1)
    assert repeated['job_ids'] == initial['job_ids']
    assert repeated['enqueued'] == 0
    assert repeated['existing'] == 1
    assert len((await session.scalars(select(Job))).all()) == 1
    with pytest.raises(JobConflict):
        await service.batch(2, key, workspace_id=1)


async def test_scheduler_skips_failed_history_before_limit(session, session_factory, source, engine, monkeypatch):
    from types import SimpleNamespace
    from app.jobs import scheduler
    older = await candidate_for(session, source)
    newer = Candidate(workspace_id=1, source_id=source.id, external_url='https://example.com/newer', title='Newer')
    session.add(newer)
    await session.commit()
    settings = Settings(openai_api_key='test', classify_batch_limit=1)
    failed = await JobService(session, settings).enqueue('classify', newer.id)
    failed.status = 'failed'
    await session.commit()
    async def fake_fetch(_):
        return SimpleNamespace(model_dump=lambda: {'new_candidates': 0})
    monkeypatch.setattr(scheduler, 'engine', engine)
    monkeypatch.setattr(scheduler, 'SessionLocal', session_factory)
    monkeypatch.setattr(scheduler, 'get_settings', lambda: settings)
    monkeypatch.setattr(scheduler.IngestionService, 'fetch_all_active', fake_fetch)
    await scheduler.run_pipeline_once()
    active = (await session.scalars(select(Job).where(Job.status == 'queued'))).all()
    assert [job.candidate_id for job in active] == [older.id]
    await scheduler.run_pipeline_once()
    assert len((await session.scalars(select(Job))).all()) == 2


async def test_failed_job_manual_retry_creates_new_job(session, source):
    candidate = await candidate_for(session, source)
    service = JobService(session, Settings(openai_api_key='test'))
    job = await service.enqueue('classify', candidate.id)
    job.status = 'failed'
    await session.commit()
    key = uuid4()
    retried = await service.retry(job.id, key)
    assert retried.id != job.id
    assert retried.retry_of_job_id == job.id
    assert retried.attempt_count == 0
    assert (await service.retry(job.id, key)).id == retried.id


async def test_failed_final_commit_rolls_back_article_and_success(session, session_factory, monkeypatch):
    from app.models import Article
    from app.services.article.write import ArticleService
    from app.services.llm.cost import LLMCostCalculator
    from app.schemas.article import GenerateArticleRequest
    from tests.article_fakes import FakeArticleLLM, research_fixture
    candidate, _ = await research_fixture(session)
    settings = Settings(openai_api_key='test')
    job = await JobService(session, settings).enqueue('write', candidate.id)
    claimed = await JobRepository(session).claim('crashed')
    async with session_factory() as db:
        async def crash():
            raise RuntimeError('Simulated crash after flush, before commit')
        monkeypatch.setattr(db, 'commit', crash)
        service = ArticleService(db, FakeArticleLLM(), LLMCostCalculator(settings.llm_pricing),
                                 JobExecution(session_factory, claimed))
        with pytest.raises(RuntimeError):
            await service.generate(candidate.id, GenerateArticleRequest())
    await session.refresh(job)
    assert job.status == 'running'
    assert job.result_id is None
    assert (await session.scalars(select(Article))).all() == []


async def test_parallel_batch_skip_cannot_hide_enqueued_child(session, session_factory, source, monkeypatch):
    candidate = await candidate_for(session, source)
    settings = Settings(openai_api_key='test')
    unrelated = await JobService(session, settings).enqueue('research', candidate.id)
    key = uuid4()
    released = asyncio.Event()
    other_done = asyncio.Event()
    async with session_factory() as first_db:
        rollback = first_db.rollback
        async def pause_after_rollback():
            await rollback()
            released.set()
            await asyncio.wait_for(other_done.wait(), timeout=3)
        monkeypatch.setattr(first_db, 'rollback', pause_after_rollback)
        first = asyncio.create_task(JobService(first_db, settings).batch(1, key, workspace_id=1))
        await asyncio.wait_for(released.wait(), timeout=3)
        unrelated.status = 'failed'
        await session.commit()
        async with session_factory() as second_db:
            second = await JobService(second_db, settings).batch(1, key, workspace_id=1)
        other_done.set()
        original = await first
    assert original['job_ids'] == second['job_ids']
    replay = await JobService(session, settings).batch(1, key, workspace_id=1)
    assert replay['job_ids'] == second['job_ids']
    assert replay['skipped_busy'] == 0
