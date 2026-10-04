"""Shared gates and atomic publication/job preparation."""
from sqlalchemy import select
from app.core.config import get_settings
from app.models import Article, ArticleStatus, Candidate, WordPressPublication
from app.services.article.versions import latest_qa, content_hash
from app.services.qa.context import matches_article
from app.services.jobs.errors import JobInputError
from app.services.wordpress.preparation import seo_profile, CATEGORIES

async def approved_version(session, version_id, settings=None, lock=False):
    settings=settings or get_settings()
    article=await session.get(Article,version_id)
    if not article:raise JobInputError('Article version not found',404)
    if lock:
        await session.scalar(select(Candidate.id).where(Candidate.id==article.candidate_id).with_for_update())
        article=await session.scalar(select(Article).where(Article.id==version_id).with_for_update().execution_options(populate_existing=True))
    report=await latest_qa(session,article)
    if article.status!=ArticleStatus.APPROVED:raise JobInputError('WordPress wymaga zatwierdzonej wersji.')
    if not report or report.status!='completed' or not report.qa_passed or not matches_article(report,article) or (report.overall_score or 0)<settings.qa_pass_score or report.critical_issue_count or report.unsupported_claims_count:
        raise JobInputError('Publikacja wymaga aktualnego, zaliczonego QA.')
    if article.content_hash!=content_hash(article):raise JobInputError('Zmieniona treść wymaga nowego QA i approval.')
    return article

async def publication_for(session, article, create=False):
    publication=await session.scalar(select(WordPressPublication).where(WordPressPublication.candidate_id==article.candidate_id))
    if not publication and create:
        publication=WordPressPublication(candidate_id=article.candidate_id,article_version_id=article.id,
            title=article.title,slug=article.slug,profile=seo_profile(article),warnings=[])
        session.add(publication);await session.flush()
    return publication

async def enqueue_wordpress(service, version_id, options, key=None, kind='publish_wordpress', retry_of=None):
    from app.services.wordpress.client import WordPressClient
    settings=get_settings()
    client=WordPressClient(settings)
    try:client.configured()
    except Exception as exc:
        from app.services.wordpress.errors import WordPressError
        if isinstance(exc,WordPressError):raise JobInputError(exc.code,503) from None
        raise
    finally:await client.close()
    # JobService's candidate lock serializes the active job and publication row.
    article=await approved_version(service.session,version_id,settings,lock=True)
    options={'article_id':version_id,**options}
    job=await service.enqueue(kind,article.candidate_id,options,key,retry_of=retry_of,commit=False)
    if job.status not in ('queued','running','retrying'):
        await service.session.commit();return job
    publication=await publication_for(service.session,article,create=True)
    if options.get('sync') and not publication.wordpress_post_id:
        raise JobInputError('Najpierw utwórz draft WordPress.',409)
    publication.job_id=job.id;publication.status='queued';publication.error_code=None;publication.conflict=None
    await service.session.commit();await service.session.refresh(job)
    return job
