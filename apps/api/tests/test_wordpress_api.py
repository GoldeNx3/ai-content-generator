import json
from datetime import datetime,timedelta,timezone
from uuid import UUID,uuid4
import httpx
import pytest
from sqlalchemy import select,update
from app.models import Article,WordPressPublication
from app.models.job import Job
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.preparation import wp_content_hash
from tests.test_qa_api import article_fixture,FakeQA

class WPHTTP:
    def __init__(self):
        self.posts={};self.operations={};self.next_id=100;self.creates=0;self.updates=0
        self.categories={};self.tags={};self.error=None;self.meta_keys=None
    def handle(self,r):
        path=r.url.path;data=json.loads(r.content or b'{}') if 'media' not in path else {}
        if self.error:
            error=self.error;self.error=None
            if error=='timeout':raise httpx.ReadTimeout('timeout',request=r)
            return httpx.Response(error,json={'code':'error'})
        if path.endswith('/capabilities'):
            from app.services.wordpress.adapters import adapter_for
            keys=adapter_for('yoast').mapping.values()
            return httpx.Response(200,json={'bridge_version':'1.0.0','seo_plugin':'yoast','meta_keys':list(keys) if self.meta_keys is None else self.meta_keys,'timezone':'Europe/Warsaw','can_publish':True,'can_edit':True,'author_id':1})
        if path.endswith('/operation'):
            return httpx.Response(200,json={'exists':r.url.params.get('operation') in self.operations})
        if '/users/' in path: return httpx.Response(200,json={'id':1,'name':'Author'})
        if '/categories' in path or '/tags' in path:
            store=self.tags if '/tags' in path else self.categories
            if r.method=='GET':return httpx.Response(200,json=[v for v in store.values() if v['name']==r.url.params.get('search')])
            term={'id':len(store)+1,'name':data['name']};store[term['id']]=term
            return httpx.Response(201,json=term)
        if path.endswith('/media'):return httpx.Response(201,json={'id':77})
        if '/content-engine/v1/posts' in path:
            op=data['operation']
            if op in self.operations:return httpx.Response(200,json=self.operations[op])
            payload=data['post'];tail=path.rsplit('/',1)[-1]
            if tail=='posts':
                active=[p for p in self.posts.values() if p['status']!='trash']
                if active:
                    post=active[-1]
                    if wp_content_hash(post)!=__import__('hashlib').sha256(payload['content'].encode()).hexdigest():
                        return httpx.Response(409,json={'code':'ce_content_conflict','data':{'current_hash':wp_content_hash(post),'post_id':post['id']}})
                else:
                    self.creates+=1;self.next_id+=1
                    post={'id':self.next_id,'title':{'raw':''},'content':{'raw':''},'status':'draft','featured_media':0,'meta':{},'link':'https://wp.example/blog/article/','ce_permalink':'https://wp.example/blog/article/'}
                    self.posts[post['id']]=post
            else:
                post=self.posts.get(int(tail))
                if post is None or (post['status']=='trash' and payload.get('status')!='draft'):
                    return httpx.Response(404,json={'code':'ce_missing'})
                if data.get('expected_hash') and data['expected_hash']!=wp_content_hash(post):
                    return httpx.Response(409,json={'code':'content_conflict','data':{'current_hash':wp_content_hash(post)}})
                self.updates+=1
            for k,v in payload.items():
                if k in ('title','content'):post[k]={'raw':v,'rendered':v}
                elif k=='meta':post['meta'].update(v)
                else:post[k]=v
            self.operations[op]=dict(post)
            return httpx.Response(200,json=post)
        if '/wp/v2/posts/' in path:
            post=self.posts.get(int(path.rsplit('/',1)[-1]))
            return httpx.Response(200,json=post) if post else httpx.Response(404,json={'code':'missing'})
        return httpx.Response(200,json=[])

@pytest.fixture
async def wordpress(monkeypatch):
    from app.core.config import get_settings
    from app.api.deps import get_settings as dep_settings
    config=get_settings().model_copy(update={'wordpress_url':'https://wp.example/blog','wordpress_username':'editor','wordpress_app_password':'test-secret'})
    monkeypatch.setattr('app.services.wordpress.service.get_settings',lambda:config)
    # Endpoint settings dependency is overridden by client; give model defaults here.
    monkeypatch.setattr('app.services.wordpress.api_helpers.get_settings',lambda:config)
    remote=WPHTTP();http=httpx.AsyncClient(transport=httpx.MockTransport(remote.handle))
    original=WordPressClient.__init__
    def init(self,settings,http_client=None):original(self,config,http)
    monkeypatch.setattr(WordPressClient,'__init__',init)
    yield remote
    await http.aclose()

async def approved(client,session,execute_job):
    a,_=await article_fixture(session)
    await client.post(f'/api/articles/{a.id}/qa');await execute_job({'qa_article':FakeQA()})
    response=await client.post(f'/api/article-versions/{a.id}/approve')
    assert response.status_code==200
    await session.refresh(a)
    return a

async def publish(client,a,execute_job,body=None):
    result=await client.post(f'/api/article-versions/{a.id}/wordpress',json=body or {'status':'draft'})
    assert result.status_code==202,result.text
    await execute_job({'wordpress':True})
    job=(await client.get('/api/jobs/'+result.json()['id'])).json()
    return job,(await client.get(f'/api/article-versions/{a.id}/wordpress')).json()

async def test_approved_creates_draft_and_canonical(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded',job
    p=state['publication'];assert p['status']=='draft_created' and p['wordpress_post_id']==101
    assert p['profile']['canonical_url']=='https://wp.example/blog/article/'
    assert wordpress.posts[101]['meta']['_yoast_wpseo_canonical']==p['wordpress_url']
    assert wordpress.posts[101]['author']==1 and wordpress.creates==1
    assert p['media_id'] is None

async def test_unapproved_blocked(client,session,wordpress):
    a,_=await article_fixture(session)
    assert (await client.post(f'/api/article-versions/{a.id}/wordpress',json={'status':'draft'})).status_code==409
    assert wordpress.creates==0

async def test_lost_local_mapping_recovers_conflict_and_allows_explicit_sync(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job)
    p=await session.scalar(select(WordPressPublication).where(WordPressPublication.candidate_id==a.candidate_id))
    p.wordpress_post_id=None;p.last_synced_content_hash=None
    await session.commit()
    wordpress.posts[101]['content']={'raw':'Ręczna treść WordPress'}
    job,state=await publish(client,a,execute_job)
    assert job['status']=='failed'
    assert job['error_code']=='wordpress_conflict'
    assert 'WordPress' in job['error_message'] and 'nadpis' in job['error_message']
    assert state['publication']['wordpress_post_id']==101
    assert state['conflict']['current_hash']==wp_content_hash(wordpress.posts[101])
    assert wordpress.posts[101]['content']['raw']=='Ręczna treść WordPress'
    result=await client.post(f'/api/article-versions/{a.id}/wordpress/sync',json={'expected_wp_hash':state['conflict']['current_hash']})
    assert result.status_code==202,result.text
    await execute_job({'wordpress':True})
    state=(await client.get(f'/api/article-versions/{a.id}/wordpress')).json()
    assert state['publication']['status']=='draft_created'
    assert state['publication']['wordpress_post_id']==101
    assert wordpress.creates==1

async def test_stale_qa_blocked(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job);a.content+=' changed';await session.commit()
    assert (await client.post(f'/api/article-versions/{a.id}/wordpress',json={'status':'draft'})).status_code==409

async def test_existing_publication_update_without_duplicate(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job);job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded' and wordpress.creates==1 and state['publication']['wordpress_post_id']==101

@pytest.mark.parametrize('error,status',[(401,'failed'),(403,'failed'),(429,'retrying'),(500,'retrying'),('timeout','retrying')])
async def test_worker_retry_policy(client,session,execute_job,wordpress,error,status):
    a=await approved(client,session,execute_job)
    wordpress.error=error
    job,_=await publish(client,a,execute_job)
    assert job['status']==status,job
    if status=='retrying':
        await session.execute(update(Job).where(Job.id==UUID(job['id'])).values(available_at=datetime.now(timezone.utc)))
        await session.commit();await execute_job({'wordpress':True})
        assert (await client.get('/api/jobs/'+job['id'])).json()['status']=='succeeded'
        assert wordpress.creates==1

@pytest.mark.parametrize('target',['future','publish'])
async def test_schedule_and_publish(client,session,execute_job,wordpress,target):
    a=await approved(client,session,execute_job)
    body={'status':target}
    if target=='future':body['scheduled_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    job,state=await publish(client,a,execute_job,body)
    assert job['status']=='succeeded',job
    assert wordpress.posts[101]['status']==target
    if target=='future':assert 'date_gmt' in wordpress.posts[101]

async def test_category_and_tags(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    response=await client.patch(f'/api/article-versions/{a.id}/wordpress/settings',json={'category':'AI','tags':['Claude','Anthropic','Barclays']})
    assert response.status_code==200,response.text
    job,_=await publish(client,a,execute_job)
    assert job['status']=='succeeded'
    assert [v['name'] for v in wordpress.categories.values()]==['AI']
    assert len(wordpress.tags)==3 and len(wordpress.posts[101]['tags'])==3

async def test_missing_yoast_meta_warns(client,session,execute_job,wordpress):
    wordpress.meta_keys=[]
    a=await approved(client,session,execute_job)
    job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded',job
    assert any('SEO' in message for message in state['publication']['warnings'])

async def test_manual_conflict_then_explicit_sync(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job);await publish(client,a,execute_job)
    wordpress.posts[101]['content']['raw']='Ręczna zmiana'
    result=await client.post(f'/api/article-versions/{a.id}/wordpress/sync',json={})
    assert result.status_code==202
    await execute_job({'wordpress':True})
    state=(await client.get(f'/api/article-versions/{a.id}/wordpress')).json()
    assert state['publication']['error_code']=='wordpress_conflict'
    assert wordpress.posts[101]['content']['raw']=='Ręczna zmiana'
    result=await client.post(f'/api/article-versions/{a.id}/wordpress/sync',json={'expected_wp_hash':state['conflict']['current_hash']})
    assert result.status_code==202,result.text
    await execute_job({'wordpress':True})
    assert wordpress.posts[101]['content']['raw']!='Ręczna zmiana'

async def test_secrets_not_in_job_payload(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    result=await client.post(f'/api/article-versions/{a.id}/wordpress',json={'status':'draft'})
    job=await session.get(Job,UUID(result.json()['id']))
    assert 'wordpress_app_password' not in job.payload['settings']
    assert 'test-secret' not in json.dumps(job.payload)

async def test_retry_after_remote_create_response_is_lost(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    original=wordpress.handle;lost=True
    def handle(r):
        nonlocal lost
        response=original(r)
        if r.url.path.endswith('/content-engine/v1/posts') and lost:
            lost=False;raise httpx.ReadTimeout('Response lost after server commit',request=r)
        return response
    wordpress.handle=handle
    # Existing MockTransport calls the original bound method; replace its callable.
    from app.services.wordpress.client import WordPressClient
    client_http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    from app.core.config import get_settings
    config=get_settings().model_copy(update={'wordpress_url':'https://wp.example/blog'})
    import unittest.mock
    init=WordPressClient.__init__
    with unittest.mock.patch.object(WordPressClient,'__init__',lambda self,settings,http=None:init(self,config,client_http)):
        # Fixture init ignores the injected http; override request transport after construction.
        original_request=WordPressClient.request
        async def request(self,*args,**kwargs):
            self.http=client_http;return await original_request(self,*args,**kwargs)
        with unittest.mock.patch.object(WordPressClient,'request',request):
            job,_=await publish(client,a,execute_job)
            assert job['status']=='retrying' and wordpress.creates==1
            await session.execute(update(Job).where(Job.id==UUID(job['id'])).values(available_at=datetime.now(timezone.utc)))
            await session.commit();await execute_job({'wordpress':True})
            assert (await client.get('/api/jobs/'+job['id'])).json()['status']=='succeeded'
            assert wordpress.creates==1
    await client_http.aclose()

async def test_new_approved_version_syncs_same_post(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job);await publish(client,a,execute_job)
    version=(await client.patch(f'/api/articles/{a.id}',json={'content':a.content+'\n\nDodatkowe wyjaśnienie.'})).json()
    await client.post(f"/api/articles/{version['id']}/qa");await execute_job({'qa_article':FakeQA()})
    await client.post(f"/api/article-versions/{version['id']}/approve")
    state=(await client.get(f"/api/article-versions/{version['id']}/wordpress")).json()
    assert state['newer_approved_version_id']==version['id'] and wordpress.creates==1
    result=await client.post(f"/api/article-versions/{version['id']}/wordpress/sync",json={})
    assert result.status_code==202,result.text
    await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+result.json()['id'])).json()['status']=='succeeded'
    assert wordpress.creates==1 and 'Dodatkowe wyjaśnienie' in wordpress.posts[101]['content']['raw']

async def test_approval_revoked_while_queued_blocks_send(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    result=await client.post(f'/api/article-versions/{a.id}/wordpress',json={'status':'draft'})
    await client.post(f'/api/article-versions/{a.id}/reject')
    await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+result.json()['id'])).json()['status']=='failed'
    assert wordpress.creates==0

async def test_sync_reconciles_remote_status_after_cron(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job,{'status':'future','scheduled_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
    wordpress.posts[101]['status']='publish'
    p=await session.scalar(select(WordPressPublication));p.scheduled_at=datetime.now(timezone.utc)-timedelta(days=1)
    await session.commit()
    response=await client.post(f'/api/article-versions/{a.id}/wordpress/sync',json={})
    assert response.status_code==202,response.text
    await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+response.json()['id'])).json()['status']=='succeeded'
    assert wordpress.posts[101]['status']=='publish'


async def test_elapsed_schedule_cannot_publish_implicitly(client,session,execute_job,wordpress,monkeypatch):
    a=await approved(client,session,execute_job)
    scheduled=datetime.now(timezone.utc)+timedelta(minutes=1)
    queued=await client.post(f'/api/article-versions/{a.id}/wordpress',json={'status':'future','scheduled_at':scheduled.isoformat()})
    assert queued.status_code==202
    class Later(datetime):
        @classmethod
        def now(cls,tz=None):return scheduled+timedelta(minutes=1)
    monkeypatch.setattr('app.services.wordpress.service.datetime',Later)
    await execute_job({'wordpress':True})
    job=(await client.get('/api/jobs/'+queued.json()['id'])).json()
    assert job['status']=='failed' and job['error']['code']=='wordpress_schedule_elapsed',job
    assert wordpress.posts[101]['status']=='draft'

async def test_failed_publication_manual_retry_tracks_job(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    wordpress.error=401
    job,_=await publish(client,a,execute_job)
    retried=await client.post('/api/jobs/'+job['id']+'/retry')
    assert retried.status_code==202,retried.text
    state=(await client.get(f'/api/article-versions/{a.id}/wordpress')).json()
    assert state['publication']['status']=='queued'
    await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+retried.json()['id'])).json()['status']=='succeeded'
    assert wordpress.creates==1


async def test_trashed_publication_creates_new_draft_and_preserves_trash(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job)
    wordpress.posts[101]['status']='trash'
    job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded',job
    assert state['publication']['wordpress_post_id']==102
    assert wordpress.posts[101]['status']=='trash' and wordpress.posts[102]['status']=='draft'
    assert wordpress.creates==2

async def test_permanently_deleted_post_recreated_once(client,session,execute_job,wordpress):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job)
    del wordpress.posts[101]
    job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded',job
    assert state['publication']['wordpress_post_id']==102 and wordpress.creates==2
    job,state=await publish(client,a,execute_job)
    assert job['status']=='succeeded' and wordpress.creates==2


async def test_recreate_after_trash_lost_response_retries_same_payload(client,session,execute_job,wordpress,monkeypatch):
    a=await approved(client,session,execute_job)
    await publish(client,a,execute_job)
    wordpress.posts[101]['status']='trash'
    original=WordPressClient.create_post
    sent=[]
    async def lose_response(self,payload,**kwargs):
        result=await original(self,payload,**kwargs)
        if kwargs.get('operation','').endswith(':create'):
            sent.append(dict(payload))
            if len(sent)==1:
                from app.services.wordpress.errors import WordPressError
                raise WordPressError('wordpress_timeout',True)
        return result
    monkeypatch.setattr(WordPressClient,'create_post',lose_response)
    job,_=await publish(client,a,execute_job)
    assert job['status']=='retrying'
    await session.execute(update(Job).where(Job.id==UUID(job['id'])).values(available_at=datetime.now(timezone.utc)))
    await session.commit();await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+job['id'])).json()['status']=='succeeded'
    assert len(sent)==2 and sent[0]==sent[1] and sent[1]['status']=='draft'
    assert wordpress.creates==2 and wordpress.posts[101]['status']=='trash'

@pytest.mark.parametrize('deleted',['trash','missing'])
async def test_new_approved_version_can_be_sent_after_wp_deletion(client,session,execute_job,wordpress,deleted):
    a=await approved(client,session,execute_job);await publish(client,a,execute_job)
    if deleted=='trash':wordpress.posts[101]['status']='trash'
    else:del wordpress.posts[101]
    version=(await client.patch(f'/api/articles/{a.id}',json={'content':a.content+'\n\nNowa wersja po usunięciu.'})).json()
    await client.post(f"/api/articles/{version['id']}/qa");await execute_job({'qa_article':FakeQA()})
    await client.post(f"/api/article-versions/{version['id']}/approve")
    state=(await client.get(f"/api/article-versions/{version['id']}/wordpress")).json()
    assert state['remote_status']==deleted
    result=await client.post(f"/api/article-versions/{version['id']}/wordpress",json={'status':'draft'})
    assert result.status_code==202,result.text
    await execute_job({'wordpress':True})
    assert (await client.get('/api/jobs/'+result.json()['id'])).json()['status']=='succeeded'
    post=wordpress.posts[102]
    assert post['status']=='draft' and 'Nowa wersja po usunięciu' in post['content']['raw']
    assert wordpress.creates==2

async def test_legacy_seo_preview_and_child_inherit_profile_without_mutating_parent(client,session,execute_job,wordpress):
    a,_=await article_fixture(session)
    a.seo_data={};await session.commit()
    await client.post(f'/api/articles/{a.id}/qa');await execute_job({'qa_article':FakeQA()})
    await client.post(f'/api/article-versions/{a.id}/approve')
    p=await session.scalar(select(WordPressPublication).where(WordPressPublication.candidate_id==a.candidate_id))
    if p is None:
        from app.services.wordpress.api_helpers import publication_for
        p=await publication_for(session,a,True)
    p.profile={**p.profile,'version_id':a.id,'focus_keyword':'Claude','secondary_keywords':['Barclays'],
        'excerpt':'Zapisany excerpt','tags':['Claude','Anthropic','Barclays'],'category':'Newsy','schema_type':'NewsArticle'}
    await session.commit()
    state=(await client.get(f'/api/articles/{a.id}')).json()
    assert state['seo_data']=={} and state['seo_preview']['focus_keyword']=='Claude'
    assert state['seo_origin']=='publication_profile'
    assert not (await client.get(f'/api/articles/{a.id}/qa')).json()['is_stale']
    child=(await client.patch(f'/api/articles/{a.id}',json={'content':a.content+'\n\nNowy akapit.'})).json()
    assert child['seo_data']['focus_keyword']=='Claude' and child['seo_data']['tags']==['Claude','Anthropic','Barclays']
    assert child['seo_data']['canonical_url'] is None


async def workflow_candidate(client, candidate_id, expected):
    detail = (await client.get(f'/api/candidates/{candidate_id}')).json()
    assert detail['workflow_status'] == expected
    page = (await client.get('/api/candidates', params={'workflow_status': expected})).json()
    assert candidate_id in [item['id'] for item in page['items']]
    other = 'published' if expected != 'published' else 'draft'
    excluded = (await client.get('/api/candidates', params={'workflow_status': other})).json()
    assert candidate_id not in [item['id'] for item in excluded['items']]
    return detail


async def test_candidate_workflow_tracks_draft_approval_and_wordpress_actions(client, session, execute_job, wordpress):
    a, _ = await article_fixture(session)
    await workflow_candidate(client, a.candidate_id, 'draft')
    await client.post(f'/api/articles/{a.id}/qa')
    await execute_job({'qa_article': FakeQA()})
    await workflow_candidate(client, a.candidate_id, 'draft')  # QA does not approve.
    assert (await client.post(f'/api/article-versions/{a.id}/approve')).status_code == 200
    await workflow_candidate(client, a.candidate_id, 'approved')
    for target, expected in [('draft', 'draft'), ('publish', 'published'), ('draft', 'draft')]:
        job, _ = await publish(client, a, execute_job, {'status': target})
        assert job['status'] == 'succeeded'
        detail = await workflow_candidate(client, a.candidate_id, expected)
        assert detail['status'] == 'approved'


async def test_failed_publication_does_not_approve_topic_or_show_published(client, session, execute_job, wordpress):
    a = await approved(client, session, execute_job)
    before = (await client.get(f'/api/candidates/{a.candidate_id}')).json()['status']
    wordpress.error = 401
    job, _ = await publish(client, a, execute_job, {'status': 'publish'})
    assert job['status'] == 'failed'
    detail = await workflow_candidate(client, a.candidate_id, 'approved')
    assert detail['status'] == before


async def test_scheduled_publication_has_separate_workflow_status(client, session, execute_job, wordpress):
    a = await approved(client, session, execute_job)
    job, _ = await publish(client, a, execute_job, {
        'status': 'future', 'scheduled_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
    assert job['status'] == 'succeeded'
    await workflow_candidate(client, a.candidate_id, 'scheduled')


async def test_failed_recreation_does_not_reuse_previous_verification(client, session, execute_job, wordpress, monkeypatch):
    from app.services.wordpress.errors import WordPressError
    a = await approved(client, session, execute_job)
    job, _ = await publish(client, a, execute_job, {'status': 'publish'})
    assert job['status'] == 'succeeded'
    await workflow_candidate(client, a.candidate_id, 'published')
    wordpress.posts[101]['status'] = 'trash'
    def fail_verification(*args, **kwargs):
        raise WordPressError('wordpress_verification_failed')
    monkeypatch.setattr('app.services.wordpress.service.WordPressPublisherService.verify', staticmethod(fail_verification))
    job, _ = await publish(client, a, execute_job, {'status': 'draft'})
    assert job['status'] == 'failed'
    await workflow_candidate(client, a.candidate_id, 'approved')
