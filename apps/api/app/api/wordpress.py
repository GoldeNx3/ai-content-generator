from datetime import datetime, timezone
from fastapi import APIRouter,HTTPException,Response
from sqlalchemy import select
from app.api.deps import SessionDep,JobServiceDep
from app.api.jobs import IdempotencyKey,enqueue_call
from app.models import Article,WordPressPublication
from app.schemas.job import JobRead
from app.schemas.wordpress import PublishRequest,SyncRequest,SEOData,PublicationRead
from app.services.wordpress.api_helpers import approved_version,publication_for,enqueue_wordpress,get_settings
from app.services.wordpress.preparation import seo_profile,readiness,CATEGORIES
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.errors import WordPressError
from app.services.jobs.errors import JobInputError
router=APIRouter(tags=['wordpress'])

@router.post('/article-versions/{version_id}/wordpress',response_model=JobRead,status_code=202)
async def publish(version_id:int,body:PublishRequest,service:JobServiceDep,response:Response,key:IdempotencyKey=None):
    return await enqueue_call(response,lambda:enqueue_wordpress(service,version_id,body.model_dump(mode='json'),key))

@router.post('/article-versions/{version_id}/wordpress/prepare',response_model=JobRead,status_code=202)
async def prepare(version_id:int,service:JobServiceDep,response:Response,key:IdempotencyKey=None):
    return await enqueue_call(response,lambda:enqueue_wordpress(service,version_id,{},key,'prepare_wordpress'))

@router.post('/article-versions/{version_id}/wordpress/sync',response_model=JobRead,status_code=202)
async def sync(version_id:int,body:SyncRequest,service:JobServiceDep,response:Response,key:IdempotencyKey=None):
    async def action():
        article=await approved_version(service.session,version_id)
        publication=await publication_for(service.session,article)
        if not publication or not publication.wordpress_post_id:raise JobInputError('Najpierw utwórz draft WordPress.')
        client=WordPressClient(get_settings())
        try:remote=await client.get_post(publication.wordpress_post_id)
        except WordPressError as exc:
            if exc.code=='wordpress_http_404':remote={'status':'draft'}
            else:raise JobInputError(exc.code,503) from None
        finally:await client.close()
        status=body.status or ('draft' if remote['status']=='trash' else remote['status'])
        scheduled=body.scheduled_at
        if status=='future' and scheduled is None:
            date=remote.get('date_gmt')
            scheduled=datetime.fromisoformat(date).replace(tzinfo=timezone.utc) if date else publication.scheduled_at
        try:request=PublishRequest(status=status,scheduled_at=scheduled,expected_wp_hash=body.expected_wp_hash)
        except ValueError as exc:raise JobInputError('Nieprawidłowy termin publikacji; wybierz przyszłą datę ze strefą czasową.',422) from None
        return await enqueue_wordpress(service,version_id,{**request.model_dump(mode='json'),'sync':True},key)
    return await enqueue_call(response,action)

@router.get('/article-versions/{version_id}/wordpress')
async def get_state(version_id:int,session:SessionDep):
    article=await session.get(Article,version_id)
    if not article:raise HTTPException(404,'Article version not found')
    publication=await publication_for(session,article)
    qa_ok=True
    try:await approved_version(session,version_id)
    except JobInputError:qa_ok=False
    overrides=publication.profile if publication and publication.profile.get('version_id',article.id)==article.id else {}
    profile=seo_profile(article,overrides)
    current=await session.scalar(select(Article).where(Article.candidate_id==article.candidate_id,Article.status=='approved'))
    remote_status=None
    if publication and publication.wordpress_post_id:
        client=WordPressClient(get_settings())
        try:remote_status=(await client.get_post(publication.wordpress_post_id))['status']
        except WordPressError as exc:remote_status='missing' if exc.code=='wordpress_http_404' else 'unknown'
        finally:await client.close()
    return {'publication':PublicationRead.model_validate(publication) if publication else None,'profile':profile,
        'remote_status':remote_status,'checks':readiness(article,profile,publication,qa_ok),'categories':CATEGORIES,'qa_ok':qa_ok,
        'newer_approved_version_id':current.id if publication and current and current.id!=publication.article_version_id else None,
        'conflict':publication.conflict if publication and remote_status!='missing' else None,
        'wordpress_admin_url':f'{get_settings().wordpress_url.rstrip("/")}/wp-admin/post.php?post={publication.wordpress_post_id}&action=edit' if publication and publication.wordpress_post_id else None}

@router.patch('/article-versions/{version_id}/wordpress/settings')
async def settings(version_id:int,body:SEOData,session:SessionDep):
    try:
        article=await approved_version(session,version_id,lock=True)
        from app.models.job import Job,ACTIVE_STATUSES
        active=await session.scalar(select(Job.id).where(Job.candidate_id==article.candidate_id,Job.status.in_(ACTIVE_STATUSES)))
        if active:raise JobInputError('Poczekaj na zakończenie aktywnego zadania.')
        if body.category and body.category not in CATEGORIES:raise JobInputError('Niedozwolona kategoria.',422)
        publication=await publication_for(session,article,True)
        previous=publication.profile if publication.profile.get('version_id',article.id)==article.id else {}
        values=body.model_dump(exclude_unset=True)
        if 'canonical_url' in values:raise JobInputError('Canonical jest ustalany przez WordPress.',422)
        if values.get('category'):values['category_override']=True
        publication.profile={**seo_profile(article,previous),**values,'version_id':article.id}
        await session.commit()
        return await get_state(version_id,session)
    except JobInputError as exc:raise HTTPException(exc.status_code,str(exc)) from exc

@router.post('/wordpress/test-connection')
async def test_connection():
    client=WordPressClient(get_settings())
    try:return await client.test_connection()
    except WordPressError as exc:raise HTTPException(503,{'code':exc.code}) from None
    finally:await client.close()
