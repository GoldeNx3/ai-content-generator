"""The interactive demo uses the real durable pipeline without external providers."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models import Article, ArticleFix, ArticleQA, Candidate, Research, Source
from app.models.job import Job, JobAttempt
from app.repositories.candidate_repository import CandidateRepository
from app.services.jobs.errors import JobInputError
from app.services.jobs.service import JobService
from app.workers.worker import Worker

PREFIX = 'https://demo.content-engine.invalid/'

async def test_demo_full_queue_flow_never_constructs_network_client(session, session_factory, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Demo must not construct external providers')
    monkeypatch.setattr('app.workers.providers.OpenAIClient', forbidden)
    monkeypatch.setattr('httpx.AsyncClient', forbidden)
    source = Source(name='Demo', url=PREFIX + 'feed', active=False)
    session.add(source)
    await session.flush()
    candidate = Candidate(source_id=source.id, title='Nexa Studio', external_url=PREFIX + 'interactive')
    session.add(candidate)
    await session.commit()
    settings = Settings(openai_api_key='', tavily_api_key='')
    service = JobService(session, settings)
    worker = Worker(session_factory, settings=settings)
    async def run(kind, options=None):
        job = await service.enqueue(kind, candidate.id, options)
        assert job.payload['demo'] is True
        assert job.payload['settings']['openai_writer_model'] == 'demo-static'
        assert await worker.run_once()
        await session.refresh(job)
        assert job.status == 'succeeded', job.error_message
        attempt = await session.scalar(select(JobAttempt).where(JobAttempt.job_id == job.id))
        assert all(Decimal(call['estimated_cost_usd']) == 0 for call in attempt.llm_calls)
        return job
    await run('classify')
    assert candidate.id not in await CandidateRepository(session).list_unclassified_ids()
    await run('research')
    research = await session.scalar(select(Research).where(Research.candidate_id == candidate.id))
    assert any('9,99' in f.claim for f in research.facts)
    await run('write')
    article = await session.scalar(select(Article).where(Article.candidate_id == candidate.id))
    await run('qa_article', {'article_id': article.id})
    report = await session.scalar(select(ArticleQA).where(ArticleQA.article_id == article.id))
    assert not report.qa_passed
    assert any(i.type == 'unsupported_claim' and i.severity == 'high' for i in report.issues)
    await run('auto_fix_article', {'article_id': article.id})
    fix = await session.scalar(select(ArticleFix).where(ArticleFix.source_article_version_id == article.id))
    assert fix.issues_fixed == 1
    fixed = await session.get(Article, fix.result_article_version_id)
    assert '47%' not in fixed.content
    # The corrected version waits for the editor to explicitly start QA.
    assert not await worker.run_once()
    await run('qa_article', {'article_id': fixed.id})
    clean = await session.scalar(select(ArticleQA).where(ArticleQA.article_id == fixed.id))
    assert clean.qa_passed
    assert clean.issues == []

async def test_real_candidate_cannot_bypass_key_by_demo_option(session, source):
    candidate = Candidate(source_id=source.id, title='Real', external_url='https://example.com/real')
    session.add(candidate)
    await session.commit()
    with pytest.raises(JobInputError, match='OPENAI_API_KEY'):
        await JobService(session, Settings(openai_api_key='')).enqueue('classify', candidate.id, {'demo': True})

async def test_demo_unclassified_excluded_from_automatic_batch(session, source):
    demo = Candidate(source_id=source.id, title='Demo', external_url=PREFIX + 'pending')
    real = Candidate(source_id=source.id, title='Real', external_url='https://example.com/pending')
    session.add_all([demo, real])
    await session.commit()
    assert await CandidateRepository(session).list_unclassified_ids() == [real.id]

async def test_snapshot_jobs_are_not_claimed_or_recovered(session, source):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4
    from app.repositories.job_repository import JobRepository
    candidate = Candidate(source_id=source.id, title='Snapshot', external_url=PREFIX + 'snapshot')
    session.add(candidate)
    await session.flush()
    now = datetime.now(UTC)
    queued = Job(id=uuid4(), candidate_id=candidate.id, kind='classify', payload={'demo_snapshot': True},
        idempotency_key=uuid4(), request_hash='queued', status='queued', available_at=now-timedelta(seconds=10))
    running = Job(id=uuid4(), candidate_id=candidate.id, kind='research', payload={'demo_snapshot': True},
        idempotency_key=uuid4(), request_hash='running', status='running', locked_until=now-timedelta(seconds=10))
    other = Candidate(source_id=source.id, title='Running snapshot', external_url=PREFIX + 'running')
    session.add(other)
    await session.flush()
    running.candidate_id = other.id
    session.add_all([queued, running])
    await session.commit()
    repo = JobRepository(session)
    assert await repo.recover_expired() == 0
    assert await repo.claim('test') is None

@pytest.mark.parametrize('fragment,expected,severity', [
    ('Nexa zwiększa produktywność o 47%.', 'unsupported_claim', 'high'),
    ('Anna Nowak powiedziała: „Nexa zmienia wszystko”.', 'unsupported_quote', 'critical'),
    ('Premiera Nexa odbyła się w 2025.', 'contradiction', 'critical'),
    ('Nexa Basic kosztuje 99 USD miesięcznie.', 'incorrect_number', 'high'),
    ('Cena Nexa Enterprise wynosi 100 USD.', 'missing_uncertainty', 'high'),
    ('Dane Nexa są przechowywane wyłącznie w Europie.', 'ignored_conflict', 'high'),
    ('Eksport Markdown jest dostępny. Eksport Markdown jest dostępny.', 'repetition', 'warning'),
])
async def test_demo_qa_evaluates_current_text_and_edits_resolve(fragment, expected, severity):
    from app.workers.demo_providers import DemoQA, PRICE
    payload = {'article': {'title': 'Nexa', 'lead': PRICE, 'content': PRICE + '\n\n' + fragment},
        'research': {'facts': [{'id': 1, 'claim': PRICE, 'source_ids': [2]}]}}
    result = await DemoQA().evaluate(payload)
    assert any(i.type == expected and i.severity == severity for i in result.output.issues)
    payload['article']['content'] = PRICE
    result = await DemoQA().evaluate(payload)
    assert result.output.issues == []

async def test_worker_ignores_forged_demo_flag_on_real_candidate(session, session_factory, source, monkeypatch):
    class RealProviderSelected(Exception): pass
    def real_providers(settings): raise RealProviderSelected()
    monkeypatch.setattr('app.workers.worker.providers_for', real_providers)
    candidate = Candidate(source_id=source.id, title='Real', external_url='https://example.com/real-selection')
    session.add(candidate)
    await session.commit()
    job = await JobService(session, Settings(openai_api_key='dummy')).enqueue('classify', candidate.id)
    job.payload = {**job.payload, 'demo': True}
    await session.commit()
    await Worker(session_factory).run_once()
    await session.refresh(job)
    assert job.status == 'failed'
    assert job.checkpoints == {}

async def test_demo_manual_source_api_never_constructs_external_client(session, client, source, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('External provider created for demo source')
    candidate = Candidate(source_id=source.id, title='Local manual source', external_url=PREFIX + 'manual')
    session.add(candidate)
    await session.commit()
    monkeypatch.setattr('app.services.llm.factory.OpenAIClient', forbidden)
    monkeypatch.setattr('httpx.AsyncClient', forbidden)
    response = await client.post(f'/api/candidates/{candidate.id}/research/sources', json={'url': 'https://example.com/never-fetch'})
    assert response.status_code == 201, response.text
    assert response.json()['fetch_status'] == 'success'
    assert '9,99' in response.json()['extracted_content']

async def test_editorial_warnings_do_not_block_demo_approval():
    from app.workers.demo_providers import DemoQA, PRICE
    from app.services.qa.validation import calculate_scores
    payload={'article':{'lead':PRICE,'content':PRICE+'\n\nEksport Markdown jest dostępny. Eksport Markdown jest dostępny.'},
        'research':{'facts':[{'id':1,'claim':PRICE,'source_ids':[2]}]}}
    result=await DemoQA().evaluate(payload)
    scores=calculate_scores(result.output,85)
    assert scores['warning_count']==1 and scores['qa_passed'] and scores['overall_score']>=85
