"""QA endpoints only enqueue or read persisted reports; never call LLM."""
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from app.api.deps import JobServiceDep, SessionDep
from app.api.jobs import IdempotencyKey, enqueue_call
from app.models import Article, ArticleQA
from app.schemas.job import JobRead
from app.schemas.qa import ArticleQARead
from app.services.qa.context import matches_article

router = APIRouter(tags=['qa'])


@router.post('/articles/{article_id}/qa', response_model=JobRead, status_code=202)
async def run_qa(article_id: int, service: JobServiceDep, response: Response, key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.qa(article_id, key))


@router.get('/articles/{article_id}/qa', response_model=ArticleQARead)
async def get_qa(article_id: int, session: SessionDep):
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(404, 'Article not found')
    report = await session.scalar(select(ArticleQA).where(ArticleQA.article_id == article_id)
        .order_by(ArticleQA.created_at.desc(), ArticleQA.id.desc()).limit(1))
    if report is None:
        raise HTTPException(404, 'QA report not found')
    stale = not matches_article(report, article)
    return ArticleQARead.model_validate(report).model_copy(update={
        'is_stale': stale, 'qa_passed': bool(report.qa_passed and not stale and article.qa_passed)})


@router.post('/articles/{article_id}/qa/retry', response_model=JobRead, status_code=202)
async def retry_qa(article_id: int, service: JobServiceDep,
                   response: Response, key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.retry_qa(article_id, key))
