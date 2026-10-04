from uuid import uuid4, UUID
import pytest
from sqlalchemy import select
from app.models import Article, ArticleQA, ArticleQAIssue
from app.models.job import Job
from app.services.llm.base import LLMUsage, LLMError
from app.services.llm.auto_fix import FixResult
from app.schemas.auto_fix import FixOutput
from tests.test_qa_api import article_fixture, FakeQA


class FakeFix:
    def __init__(self,error=None,skip=False): self.calls=0; self.error=error; self.skip=skip
    async def fix(self,payload):
        self.calls+=1
        if self.error: raise self.error
        issue=next(i for i in payload['issues'] if i['auto_fixable'])
        return FixResult(FixOutput(summary='Usunięto niepopartą liczbę.',
            patches=[] if self.skip else [dict(field='content',before=issue['excerpt'],after='',
                qa_issue_ids=[issue['id']],fact_ids=[],source_ids=[])],
            fix_results=[dict(qa_issue_id=i['id'],status='skipped' if self.skip or not i['auto_fixable'] else 'fixed',
                reason='Brak danych.' if self.skip else 'Usunięto fragment.') for i in payload['issues']]),
            LLMUsage('gpt-4.1-mini',1000,200))


async def fix_fixture(client,session):
    article,_=await article_fixture(session)
    edited=(await client.patch(f'/api/articles/{article.id}',json={'content':article.content+'\n\nWzrost o 47%.'})).json()
    version=await session.get(Article,edited['id'])
    from app.services.qa.context import build_qa_payload,input_hash
    data=build_qa_payload(version)
    report=ArticleQA(article_id=version.id,article_version=version.version,status='completed',
        input_snapshot=data,input_hash=input_hash(data),factual_score=60,source_score=90,style_score=90,
        structure_score=90,seo_score=90,overall_score=75,qa_passed=False,pass_score=85,
        issues=[ArticleQAIssue(type='unsupported_claim',severity='high',excerpt='Wzrost o 47%.',
            reason='Brak danych.',suggestion='Usuń zdanie.',fact_ids=[],source_ids=[],auto_fixable=True)])
    session.add(report);await session.commit();await session.refresh(report)
    return version,report


async def test_fix_creates_version_and_enqueues_qa(client,session,execute_job):
    source,report=await fix_fixture(client,session); old=source.content
    key=str(uuid4()); url=f'/api/article-versions/{source.id}/auto-fix'
    queued=await client.post(url,headers={'Idempotency-Key':key})
    assert queued.status_code==202, queued.json()
    duplicate=await client.post(url);assert duplicate.status_code==409
    assert (await client.post(url,headers={'Idempotency-Key':key})).json()['id']==queued.json()['id']
    provider=FakeFix();await execute_job({'auto_fix_article':provider})
    job=(await client.get('/api/jobs/'+queued.json()['id'])).json();assert job['status']=='succeeded'
    fix=(await client.get('/api/article-fixes/'+str(job['result_id']))).json()
    assert fix['status']=='completed' and fix['issues_fixed']==1 and fix['estimated_cost_usd']=='0.000720'
    result=(await client.get('/api/articles/'+str(fix['result_article_version_id']))).json()
    assert result['id']!=source.id and result['parent_version_id']==source.id
    assert result['created_by']=='auto_fix' and result['auto_fix_iteration']==1
    assert result['content_hash']!=source.content_hash and not result['qa_passed']
    assert (await client.get(f'/api/articles/{source.id}')).json()['content']==old
    assert (await client.get(f"/api/articles/{result['id']}/qa")).json()['status']=='pending'
    await execute_job({'qa_article':FakeQA()})
    result=(await client.get('/api/articles/'+str(result['id']))).json()
    assert result['status']=='ready_for_approval'
    approval=await client.post(f"/api/article-versions/{result['id']}/approve")
    assert approval.status_code==200 and approval.json()['status']=='approved' and approval.json()['approved_at']
    history=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()
    assert history[0]['id']==fix['id'] and provider.calls==1


async def test_all_skipped_has_no_version_or_new_qa(client,session,execute_job):
    source,_=await fix_fixture(client,session)
    queued=await client.post(f'/api/article-versions/{source.id}/auto-fix')
    await execute_job({'auto_fix_article':FakeFix(skip=True)})
    job=(await client.get('/api/jobs/'+queued.json()['id'])).json()
    fix=(await client.get('/api/article-fixes/'+str(job['result_id']))).json()
    assert fix['result_article_version_id'] is None and fix['issues_skipped']==1
    assert (await client.get(f'/api/articles/{source.id}')).json()['status']=='manual_review_required'
    assert not (await session.scalars(select(Job).where(Job.kind=='qa_article'))).all()


@pytest.mark.parametrize('error',[LLMError('failure'),LLMError('malformed',code='invalid_output')])
async def test_fix_failure(client,session,execute_job,error):
    source,_=await fix_fixture(client,session)
    queued=await client.post(f'/api/article-versions/{source.id}/auto-fix')
    await execute_job({'auto_fix_article':FakeFix(error=error)})
    history=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()
    assert history[0]['status']=='failed' and history[0]['result_article_version_id'] is None
    assert (await client.get('/api/jobs/'+queued.json()['id'])).json()['status']=='failed'


async def test_approval_supersedes_and_manual_edit_is_new_version(client,session,execute_job):
    first,_=await article_fixture(session)
    assert (await client.post(f'/api/article-versions/{first.id}/approve')).status_code==409
    await client.post(f'/api/articles/{first.id}/qa');await execute_job({'qa_article':FakeQA()})
    assert (await client.post(f'/api/article-versions/{first.id}/approve')).status_code==200
    edited=(await client.patch(f'/api/articles/{first.id}',json={'meta_title':'Nowy opis'})).json()
    assert edited['id']!=first.id and edited['status']=='draft' and edited['parent_version_id']==first.id
    assert (await client.get(f"/api/articles/{edited['id']}/qa")).status_code==404
    assert (await client.get(f'/api/articles/{first.id}')).json()['status']=='approved'
    await client.post(f"/api/articles/{edited['id']}/qa");await execute_job({'qa_article':FakeQA()})
    assert (await client.post(f"/api/article-versions/{edited['id']}/approve")).status_code==200
    assert (await client.get(f'/api/articles/{first.id}')).json()['status']=='superseded'
    rejection=await client.post(f"/api/article-versions/{edited['id']}/reject",json={'reason':'Do poprawy'})
    assert rejection.json()['status']=='rejected' and rejection.json()['rejection_reason']=='Do poprawy'


async def test_limit_and_obsolete_qa(client,session):
    source,report=await fix_fixture(client,session)
    source.auto_fix_iteration=2;await session.commit()
    assert (await client.post(f'/api/article-versions/{source.id}/auto-fix')).status_code==409
    source.auto_fix_iteration=0; source.title='Inny tekst';await session.commit()
    assert (await client.post(f'/api/article-versions/{source.id}/auto-fix')).status_code==409


async def test_wrong_issue_id(client,session):
    source,_=await fix_fixture(client,session)
    assert (await client.post(f'/api/article-versions/{source.id}/auto-fix',json={'issue_ids':[99999]})).status_code==422

async def test_transaction_rolls_back_child_if_qa_enqueue_fails(client,session,execute_job,monkeypatch):
    source,_=await fix_fixture(client,session)
    queued=await client.post(f'/api/article-versions/{source.id}/auto-fix')
    from app.services.jobs.service import JobService
    original=JobService.enqueue
    async def broken(self,kind,*args,**kwargs):
        if kind=='qa_article': raise RuntimeError('Simulated transaction failure')
        return await original(self,kind,*args,**kwargs)
    monkeypatch.setattr(JobService,'enqueue',broken)
    await execute_job({'auto_fix_article':FakeFix()})
    history=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()
    assert history[0]['status']=='failed' and history[0]['result_article_version_id'] is None
    versions=(await client.get(f'/api/candidates/{source.candidate_id}/articles')).json()
    assert len(versions)==2 and versions[0]['id']==source.id and versions[0]['is_current']


async def test_failed_validation_preserves_cost_and_retry_checkpoint(client,session,execute_job):
    source,_=await fix_fixture(client,session)
    class Invalid(FakeFix):
        async def fix(self,payload):
            result=await super().fix(payload)
            result.output.patches[0].fact_ids=[999999]
            return result
    await client.post(f'/api/article-versions/{source.id}/auto-fix')
    await execute_job({'auto_fix_article':Invalid()})
    history=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()
    assert history[0]['status']=='failed' and history[0]['estimated_cost_usd']=='0.000720'


async def test_expired_fix_lease_marks_report_failed(client,session,session_factory):
    from app.repositories.job_repository import JobRepository
    from datetime import datetime,timedelta,timezone
    source,_=await fix_fixture(client,session)
    queued=await client.post(f'/api/article-versions/{source.id}/auto-fix')
    async with session_factory() as other:
        repo=JobRepository(other);job=await repo.claim('expired',1)
        job.locked_until=datetime.now(timezone.utc)-timedelta(seconds=5);job.attempt_count=job.max_attempts
        await other.commit();await repo.recover_expired()
    report=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()[0]
    assert report['status']=='failed'


async def test_concurrent_approval_keeps_only_one_approved(client,session,execute_job):
    import asyncio
    first,_=await article_fixture(session)
    second=(await client.patch(f'/api/articles/{first.id}',json={'meta_title':'Wersja druga'})).json()
    for article_id in (first.id,second['id']):
        await client.post(f'/api/articles/{article_id}/qa');await execute_job({'qa_article':FakeQA()})
    responses=await asyncio.gather(client.post(f'/api/article-versions/{first.id}/approve'),client.post(f"/api/article-versions/{second['id']}/approve"))
    assert all(r.status_code==200 for r in responses)
    versions=(await client.get(f'/api/candidates/{first.candidate_id}/articles')).json()
    assert sum(v['status']=='approved' for v in versions)==1 and sum(v['status']=='superseded' for v in versions)==1

async def test_manual_edit_rebuilds_sections(client,session):
    article,_=await article_fixture(session)
    result=(await client.patch(f'/api/articles/{article.id}',json={'content':'## Nowy nagłówek\n\nTekst sekcji.'})).json()
    assert result['sections_count']==1
    assert result['sections'][0]['heading']=='Nowy nagłówek' and result['sections'][0]['content']=='Tekst sekcji.'

async def test_terminal_failure_records_each_issue(client,session,execute_job):
    source,_=await fix_fixture(client,session)
    await client.post(f'/api/article-versions/{source.id}/auto-fix')
    await execute_job({'auto_fix_article':FakeFix(error=LLMError('failure'))})
    fix=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()[0]
    assert len(fix['issues'])==1 and fix['issues'][0]['status']=='failed'

async def test_negative_reqa_revokes_approval(client,session,execute_job):
    from app.schemas.qa import QAIssueOutput
    from app.services.llm.qa import QAResult
    article,_=await article_fixture(session)
    await client.post(f'/api/articles/{article.id}/qa');await execute_job({'qa_article':FakeQA()})
    await client.post(f'/api/article-versions/{article.id}/approve')
    class Negative(FakeQA):
        async def evaluate(self,payload):
            result=await super().evaluate(payload)
            issue=QAIssueOutput(type='unsupported_claim',severity='high',excerpt=payload['article']['lead'],
                reason='Brak potwierdzenia.',suggestion='Sprawdź.',section_heading='Lead',fact_ids=[],source_ids=[],auto_fixable=True)
            return QAResult(result.output.model_copy(update={'issues':[issue]}),result.usage)
    await client.post(f'/api/articles/{article.id}/qa');await execute_job({'qa_article':Negative()})
    version=(await client.get(f'/api/articles/{article.id}')).json()
    assert version['status']=='needs_changes' and version['approved_at']
    assert (await client.post(f'/api/article-versions/{article.id}/approve')).status_code==409

async def test_checkpoint_retry_does_not_pay_or_create_duplicate_child(client,session,execute_job,monkeypatch):
    from app.services.jobs.service import JobService
    from sqlalchemy import update
    from datetime import datetime,timezone
    source,_=await fix_fixture(client,session)
    response=await client.post(f'/api/article-versions/{source.id}/auto-fix')
    enqueue=JobService.enqueue
    fail_once=True
    async def retryable_successor(self,kind,*args,**kwargs):
        nonlocal fail_once
        if kind=='qa_article' and fail_once:
            fail_once=False;raise TimeoutError('Transient successor failure')
        return await enqueue(self,kind,*args,**kwargs)
    monkeypatch.setattr(JobService,'enqueue',retryable_successor)
    provider=FakeFix();await execute_job({'auto_fix_article':provider})
    job=(await client.get('/api/jobs/'+response.json()['id'])).json()
    assert job['status']=='retrying' and provider.calls==1
    await session.execute(update(Job).where(Job.id==UUID(job['id'])).values(available_at=datetime.now(timezone.utc)))
    await session.commit();await execute_job({'auto_fix_article':provider})
    assert provider.calls==1
    job=(await client.get('/api/jobs/'+job['id'])).json();assert job['status']=='succeeded'
    versions=(await client.get(f'/api/candidates/{source.candidate_id}/articles')).json()
    assert len(versions)==3 and versions[0]['auto_fix_iteration']==1


async def test_completed_attempts_inherited_by_manual_edit(client,session,execute_job):
    source,_=await fix_fixture(client,session)
    for iteration in (1,2):
        response=await client.post(f'/api/article-versions/{source.id}/auto-fix')
        assert response.status_code==202
        await execute_job({'auto_fix_article':FakeFix(skip=True)})
        history=(await client.get(f'/api/article-versions/{source.id}/fixes')).json()
        assert history[0]['iteration']==iteration
    assert (await client.post(f'/api/article-versions/{source.id}/auto-fix')).status_code==409
    child=(await client.patch(f'/api/articles/{source.id}',json={'meta_title':'Ręczna poprawka po limicie'})).json()
    assert child['auto_fix_iteration']==2
    fetched=(await client.get(f"/api/articles/{child['id']}")).json()
    assert fetched['auto_fix_iterations_remaining']==0


async def test_failed_qa_at_limit_requires_manual_review(client,session,execute_job):
    from app.schemas.qa import QAIssueOutput
    from app.services.llm.qa import QAResult
    article,_=await article_fixture(session);article.auto_fix_iteration=2;await session.commit()
    class Negative(FakeQA):
        async def evaluate(self,payload):
            result=await super().evaluate(payload)
            issue=QAIssueOutput(type='unsupported_claim',severity='high',excerpt=payload['article']['lead'],
                reason='Brak danych.',suggestion='Sprawdź ręcznie.',section_heading='Lead',fact_ids=[],source_ids=[],auto_fixable=True)
            return QAResult(result.output.model_copy(update={'issues':[issue]}),result.usage)
    await client.post(f'/api/articles/{article.id}/qa');await execute_job({'qa_article':Negative()})
    assert (await client.get(f'/api/articles/{article.id}')).json()['status']=='manual_review_required'
