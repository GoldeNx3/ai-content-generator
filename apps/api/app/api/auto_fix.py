from fastapi import APIRouter,HTTPException,Response
from sqlalchemy import select,or_
from app.api.deps import SessionDep,SettingsDep,JobServiceDep
from app.api.jobs import IdempotencyKey,enqueue_call
from app.schemas.job import JobRead
from app.schemas.article import ArticleRead
from app.schemas.auto_fix import ArticleFixRead,FixRequest,RejectRequest
from app.models import Article,ArticleFix
from app.services.article.versions import approve_version,reject_version
from app.services.jobs.errors import JobInputError
router=APIRouter(tags=['article-versions'])

@router.post('/article-versions/{version_id}/auto-fix',response_model=JobRead,status_code=202)
async def auto_fix(version_id:int,service:JobServiceDep,response:Response,payload:FixRequest|None=None,key:IdempotencyKey=None):
    return await enqueue_call(response,lambda:service.auto_fix(version_id,(payload or FixRequest()).issue_ids,key))

@router.get('/article-fixes/{fix_id}',response_model=ArticleFixRead)
async def get_fix(fix_id:int,session:SessionDep):
    result=await session.get(ArticleFix,fix_id)
    if result is None: raise HTTPException(404,'Article fix not found')
    return result

@router.get('/article-versions/{version_id}/fixes',response_model=list[ArticleFixRead])
async def fix_history(version_id:int,session:SessionDep):
    if await session.get(Article,version_id) is None: raise HTTPException(404,'Article version not found')
    return (await session.scalars(select(ArticleFix).where(or_(ArticleFix.source_article_version_id==version_id,ArticleFix.result_article_version_id==version_id))
        .order_by(ArticleFix.created_at.desc(),ArticleFix.id.desc()))).all()

@router.post('/article-versions/{version_id}/approve',response_model=ArticleRead)
async def approve(version_id:int,session:SessionDep,settings:SettingsDep):
    try: return await approve_version(session,version_id,settings)
    except JobInputError as exc: raise HTTPException(exc.status_code,str(exc)) from exc

@router.post('/article-versions/{version_id}/reject',response_model=ArticleRead)
async def reject(version_id:int,session:SessionDep,payload:RejectRequest|None=None):
    try: return await reject_version(session,version_id,(payload or RejectRequest()).reason)
    except JobInputError as exc: raise HTTPException(exc.status_code,str(exc)) from exc
