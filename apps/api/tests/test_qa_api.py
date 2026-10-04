from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from app.models import ArticleQA
from app.core.config import DEFAULT_LLM_PRICING
from app.models.job import Job
from app.services.article.write import ArticleService
from app.schemas.article import GenerateArticleRequest
from app.services.llm.base import LLMError, LLMUsage
from app.services.llm.cost import LLMCostCalculator
from app.services.llm.qa import QAResult
from app.schemas.qa import QAOutput, QAIssueOutput
from tests.article_fakes import FakeArticleLLM, research_fixture


class FakeQA:
    def __init__(self, error=None, during=None):
        self.calls = 0
        self.error = error
        self.during = during
        self.payload = None

    async def evaluate(self, payload):
        self.calls += 1
        self.payload = payload
        if self.during:
            await self.during()
        if self.error:
            raise self.error
        fact = payload['research']['facts'][0]
        return QAResult(QAOutput(factual_score=96, source_score=90, style_score=88,
            structure_score=92, seo_score=85, summary='Artykuł oparty na researchu.', issues=[],
            claims=[dict(excerpt='Barclays rozszerza współpracę z Anthropic.', section_heading='Lead',
                         verdict='supported', fact_ids=[fact['id']], source_ids=fact['source_ids'])]),
            LLMUsage('gpt-4.1-mini', 1000, 200))


async def article_fixture(session):
    candidate, research = await research_fixture(session)
    article = await ArticleService(session, FakeArticleLLM(), LLMCostCalculator(DEFAULT_LLM_PRICING)).generate(
        candidate.id, GenerateArticleRequest())
    return article, research


async def test_qa_queue_completed_persistent_report(client, session, execute_job):
    article, _ = await article_fixture(session)
    assert (await client.get(f'/api/articles/{article.id}/qa')).status_code == 404
    key = str(uuid4())
    response = await client.post(f'/api/articles/{article.id}/qa', headers={'Idempotency-Key': key})
    assert response.status_code == 202
    assert response.json()['kind'] == 'qa_article'
    assert response.json()['article_id'] == article.id
    provider = FakeQA()
    assert provider.calls == 0
    assert (await client.get(f'/api/articles/{article.id}/qa')).json()['status'] == 'pending'
    await execute_job({'qa_article': provider})
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'completed' and report['overall_score'] == 92
    assert report['qa_passed'] and not report['is_stale']
    assert report['estimated_cost_usd'] == '0.000720'
    job = (await client.get(f"/api/jobs/{response.json()['id']}")).json()
    assert job['status'] == 'succeeded' and job['result_type'] == 'article_qa'
    assert job['result_id'] == report['id'] and provider.calls == 1
    assert (await client.get(f'/api/articles/{article.id}')).json()['qa_passed']
    again = await client.post(f'/api/articles/{article.id}/qa', headers={'Idempotency-Key': key})
    assert again.json()['id'] == response.json()['id']
    edited = (await client.patch(f'/api/articles/{article.id}', json={'meta_title': 'Inny tytuł'})).json()
    assert not edited['qa_passed'] and edited['id'] != article.id
    assert not (await client.get(f'/api/articles/{article.id}/qa')).json()['is_stale']
    assert (await client.get(f"/api/articles/{edited['id']}/qa")).status_code == 404


async def test_duplicate_qa_request_and_retry(client, session, execute_job):
    article, _ = await article_fixture(session)
    first = await client.post(f'/api/articles/{article.id}/qa')
    duplicate = await client.post(f'/api/articles/{article.id}/qa')
    assert duplicate.status_code == 409
    assert duplicate.json()['detail']['job_id'] == first.json()['id']
    failed = FakeQA(LLMError('Bad output', code='invalid_output'))
    await execute_job({'qa_article': failed})
    assert (await client.get(f'/api/articles/{article.id}/qa')).json()['status'] == 'failed'
    retried = await client.post(f'/api/articles/{article.id}/qa/retry')
    assert retried.status_code == 202 and retried.json()['id'] != first.json()['id']
    await execute_job({'qa_article': FakeQA()})
    assert (await client.get(f'/api/articles/{article.id}/qa')).json()['status'] == 'completed'
    reports = (await session.scalars(select(ArticleQA).where(ArticleQA.article_id == article.id))).all()
    assert len(reports) == 2


async def test_snapshot_and_edit_during_qa(client, session, execute_job):
    article, research = await article_fixture(session)
    original_claim = article.research_snapshot['facts'][0]['claim']
    research.facts[0].claim = 'Nowy research, którego writer nie znał.'
    await session.commit()
    await client.post(f'/api/articles/{article.id}/qa')
    async def edit():
        await client.patch(f'/api/articles/{article.id}', json={'content': 'Nowy tekst.'})
    provider = FakeQA(during=edit)
    await execute_job({'qa_article': provider})
    assert provider.payload['research']['facts'][0]['claim'] == original_claim
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'completed' and not report['is_stale'] and report['qa_passed']
    versions = (await client.get(f'/api/candidates/{article.candidate_id}/articles')).json()
    assert len(versions) == 2 and not versions[0]['qa_passed']


async def test_transient_failure_retries_same_report(client, session, execute_job):
    article, _ = await article_fixture(session)
    response = await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': FakeQA(LLMError('timeout', retryable=True))})
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'pending'
    from datetime import datetime, timezone
    await session.execute(update(Job).where(Job.id == UUID(response.json()['id']))
        .values(available_at=datetime.now(timezone.utc)))
    await session.commit()
    await execute_job({'qa_article': FakeQA()})
    assert (await client.get(f'/api/articles/{article.id}/qa')).json()['id'] == report['id']


async def test_retry_endpoint_replays_key_after_completion(client, session, execute_job):
    article, _ = await article_fixture(session)
    await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': FakeQA(LLMError('failure'))})
    key = str(uuid4())
    first = await client.post(f'/api/articles/{article.id}/qa/retry', headers={'Idempotency-Key': key})
    await execute_job({'qa_article': FakeQA()})
    replay = await client.post(f'/api/articles/{article.id}/qa/retry', headers={'Idempotency-Key': key})
    assert replay.status_code == 202 and replay.json()['id'] == first.json()['id']


async def test_normalized_noop_edit_keeps_readiness(client, session, execute_job):
    article, _ = await article_fixture(session)
    await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': FakeQA()})
    patched = await client.patch(f'/api/articles/{article.id}', json={'title': ' '+article.title+' '})
    assert patched.json()['qa_passed']


@pytest.mark.parametrize('text,kind,severity', [
    ('Barclays zwiększył produktywność o 47%.', 'unsupported_claim', 'high'),
    ('Jan Nowak powiedział: „Claude zwiększa produktywność”.', 'unsupported_quote', 'critical'),
    ('Wdrożenie zakończono w 2025 roku.', 'contradiction', 'critical'),
    ('Cena wynosi 99 dolarów.', 'missing_uncertainty', 'high'),
    ('Wszystkie źródła zgadzają się na rok 2026.', 'ignored_conflict', 'high'),
])
async def test_factual_scenarios_are_persisted_and_block_readiness(
        client, session, execute_job, text, kind, severity):
    article, _ = await article_fixture(session)
    edited = (await client.patch(f'/api/articles/{article.id}', json={'content': text})).json()
    article = await session.get(__import__('app.models', fromlist=['Article']).Article, edited['id'])
    class FindingQA(FakeQA):
        async def evaluate(self, payload):
            result = await super().evaluate(payload)
            finding = dict(type=kind, severity=severity, excerpt=text, reason='Brak poparcia w researchu.',
                suggestion='Usuń lub skoryguj twierdzenie.', section_heading=None,
                fact_ids=[], source_ids=[], auto_fixable=True)
            return QAResult(result.output.model_copy(update={'issues': [
                QAIssueOutput(**finding)]}), result.usage)
    await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': FindingQA()})
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'completed'
    assert report['issues'][0]['type'] == kind and report['issues'][0]['excerpt'] == text
    assert report['unsupported_claims_count'] == 1 and not report['qa_passed']


async def test_invalid_output_preserves_known_usage(client, session, execute_job):
    article, _ = await article_fixture(session)
    class InvalidQA(FakeQA):
        async def evaluate(self, payload):
            result = await super().evaluate(payload)
            claim = result.output.claims[0].model_copy(update={'excerpt': 'Fragment nieobecny w artykule.'})
            return QAResult(result.output.model_copy(update={'claims': [claim]}), result.usage)
    await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': InvalidQA()})
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'failed'
    assert report['llm_input_tokens'] == 1000 and report['estimated_cost_usd'] == '0.000720'


async def test_concurrent_qa_requests_create_one_report(client, session):
    import asyncio
    from sqlalchemy import func
    article, _ = await article_fixture(session)
    responses = await asyncio.gather(client.post(f'/api/articles/{article.id}/qa'),
                                     client.post(f'/api/articles/{article.id}/qa'))
    assert sorted(r.status_code for r in responses) == [202, 409]
    assert await session.scalar(select(func.count(ArticleQA.id)).where(ArticleQA.article_id == article.id)) == 1


async def test_expired_final_attempt_marks_qa_failed(client, session, session_factory):
    from datetime import datetime, timezone, timedelta
    from app.repositories.job_repository import JobRepository
    article, _ = await article_fixture(session)
    await client.post(f'/api/articles/{article.id}/qa')
    async with session_factory() as worker_session:
        repo = JobRepository(worker_session)
        job = await repo.claim('lost-qa-worker')
        job.max_attempts = 1
        job.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        await worker_session.commit()
        assert await repo.recover_expired() == 1
    report = (await client.get(f'/api/articles/{article.id}/qa')).json()
    assert report['status'] == 'failed' and not report['qa_passed']


async def test_same_key_retry_race_replays_pending_report(client, session, execute_job, monkeypatch):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    article, _ = await article_fixture(session)
    await client.post(f'/api/articles/{article.id}/qa')
    await execute_job({'qa_article': FakeQA(LLMError('failure'))})
    original = AsyncSession.scalar
    both_selected, first_committed = asyncio.Event(), asyncio.Event()
    calls = 0
    async def synchronized(self, statement, *args, **kwargs):
        nonlocal calls
        if 'FROM article_qas' in str(statement) and 'LIMIT' in str(statement):
            calls += 1
            if calls == 1:
                await both_selected.wait()
            elif calls == 2:
                both_selected.set()
                await first_committed.wait()
        return await original(self, statement, *args, **kwargs)
    monkeypatch.setattr(AsyncSession, 'scalar', synchronized)
    key = str(uuid4())
    tasks = [asyncio.create_task(client.post(f'/api/articles/{article.id}/qa/retry',
        headers={'Idempotency-Key': key})) for _ in range(2)]
    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=5)
    assert done
    first_committed.set()
    responses = await asyncio.gather(*tasks)
    assert [r.status_code for r in responses] == [202, 202]
    assert responses[0].json()['id'] == responses[1].json()['id']
