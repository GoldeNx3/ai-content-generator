from sqlalchemy import select,func
from app.models import Article,Candidate,Source,ArticleQA,ArticleFix
from app.models.job import Job
from app.jobs.seed_demo import seed_demo,CASES
from app.demo import DEMO_PREFIX

async def test_demo_seed_idempotent_and_preserves_real_data(session):
    real=Source(workspace_id=1, name='Prawdziwe źródło',url='https://example.com/rss');session.add(real);await session.commit()
    first=await seed_demo(session)
    second=await seed_demo(session)
    assert len(first)==len(CASES) and [c['candidate_id'] for c in first]==[c['candidate_id'] for c in second]
    assert await session.scalar(select(func.count(Candidate.id)).where(Candidate.external_url.startswith(DEMO_PREFIX)))==len(CASES)
    assert (await session.get(Source,real.id)).name=='Prawdziwe źródło'
    demo_source=await session.scalar(select(Source).where(Source.url==DEMO_PREFIX+'feed.xml'))
    assert not demo_source.active
    assert all(c['description'] and c['slug'] for c in first)

async def test_static_demo_jobs_never_claimed_or_recovered(session,session_factory,client):
    from app.repositories.job_repository import JobRepository
    from app.repositories.candidate_repository import CandidateRepository
    await seed_demo(session)
    repo=JobRepository(session)
    assert await repo.claim('real-worker') is None
    assert await repo.recover_expired()==0
    assert await CandidateRepository(session).list_unclassified_ids(1000)==[]
    assert all(job.estimated_cost_usd==0 for job in (await session.scalars(select(ArticleFix))).all())

async def test_demo_qa_readiness_and_auto_fix_examples(client,session):
    from app.services.auto_fix.validation import eligible
    cases={c['slug']:c for c in await seed_demo(session)}
    async def article(slug):
        versions=(await client.get(f"/api/candidates/{cases[slug]['candidate_id']}/articles")).json()
        assert versions
        return (await client.get(f"/api/articles/{versions[0]['id']}")).json()
    unsafe=await article('qa-unsupported')
    qa=(await client.get(f"/api/articles/{unsafe['id']}/qa")).json()
    assert qa['overall_score']==75 and not qa['qa_passed'] and any(eligible(i) for i in qa['issues'])
    quote=await article('qa-quote')
    qa=(await client.get(f"/api/articles/{quote['id']}/qa")).json()
    assert qa['overall_score']<=60 and not any(eligible(i) for i in qa['issues'])
    ready=await article('fix-ready')
    assert ready['status']=='ready_for_approval' and ready['qa_passed'] and ready['parent_version_id']
    assert len((await client.get(f"/api/article-versions/{ready['id']}/fixes")).json())==1
    limited=await article('fix-limit');assert limited['auto_fix_iterations_remaining']==0 and limited['status']=='manual_review_required'
    stale=await article('qa-stale');assert (await client.get(f"/api/articles/{stale['id']}/qa")).json()['is_stale']
    manual=await article('manual-edit');assert manual['status']=='draft' and (await client.get(f"/api/articles/{manual['id']}/qa")).status_code==404
    assert (await client.get(f"/api/candidates/{cases['discovered']['candidate_id']}")).json()['is_demo']

async def test_seeded_successful_fixes_are_real_changes(session):
    await seed_demo(session)
    for fix in (await session.scalars(select(ArticleFix).where(ArticleFix.result_article_version_id.is_not(None)))).all():
        before=await session.get(Article,fix.source_article_version_id)
        after=await session.get(Article,fix.result_article_version_id)
        assert before.content_hash!=after.content_hash
        assert fix.change_ratio>0 and fix.issues_fixed>0
        for issue in fix.issues:
            qa_issue=next(i for i in (await session.get(ArticleQA,fix.qa_id)).issues if i.id==issue.qa_issue_id)
            if issue.status=='fixed':assert qa_issue.excerpt not in after.content

async def test_all_demo_research_reports_are_readable(client,session):
    for case in await seed_demo(session):
        response=await client.get(f"/api/candidates/{case['candidate_id']}/research")
        assert response.status_code in (200,404)
        if response.status_code==200:
            assert all('claim' in u and 'reason' in u for u in response.json()['uncertainties'])
            assert all('topic' in c and 'sources' in c for c in response.json()['conflicts'])
