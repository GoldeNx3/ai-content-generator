"""Append-only content versions, shared identity/hash, and guarded human approval."""
import hashlib
import json
import re
from difflib import SequenceMatcher
from copy import deepcopy
from datetime import datetime, timezone
from sqlalchemy import func, select, update
from app.models import Article, ArticleQA, ArticleStatus, Candidate
from app.services.jobs.errors import JobInputError
from app.services.qa.context import matches_article

CONTENT_FIELDS = ('title','lead','content','slug','meta_title','meta_description')
from app.services.article.sections import rebuild_sections  # noqa: E402,F401 (re-eksport)

def content_hash(values):
    fields={name:(values.get(name,'') if isinstance(values,dict) else getattr(values,name)).replace('\r\n','\n').replace('\r','\n') for name in CONTENT_FIELDS}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

async def child_version(session, parent, changes, created_by, iteration=None):
    await session.scalar(select(Candidate.id).where(Candidate.id==parent.candidate_id).with_for_update())
    number=await session.scalar(select(func.max(Article.version)).where(Article.candidate_id==parent.candidate_id))
    data={column.name:deepcopy(getattr(parent,column.name)) for column in Article.__table__.columns
        if column.name not in {'id','created_at','updated_at','generation_job_id','approved_at','approved_by','rejection_reason'}}
    if not parent.seo_data:
        from app.services.article.seo import preview_seo
        resolved,origin=await preview_seo(session,parent)
        if origin=='publication_profile':
            resolved['canonical_url']=None
            data['seo_data']=resolved
    data.update(changes)
    if iteration is None:
        from app.services.auto_fix.context import iterations_used
        iteration = await iterations_used(session, parent)
    data.update(version=(number or 0)+1,is_current=True,status=ArticleStatus.DRAFT,qa_passed=False,
        parent_version_id=parent.id,created_by=created_by,creation_reason='QA auto fix' if created_by=='auto_fix' else 'Manual edit',
        auto_fix_iteration=parent.auto_fix_iteration if iteration is None else iteration,
        is_edited=created_by=='manual_edit')
    data['content_hash']=content_hash(data)
    data['sections']=rebuild_sections(data['content'],data['sections'],data['research_snapshot'])
    data['sections_count']=len(data['sections'])
    used=set(data['lead_fact_ids'])|{i for section in data['sections'] for i in section['used_fact_ids']}
    data['facts_used_count']=len(used)
    data['source_count']=len({i for section in data['sections'] for i in section['source_ids']})
    if created_by=='auto_fix': data['generated_content']=data['content']
    # These costs belong to prior generation, not this edit. Fix costs live on ArticleFix.
    for field in ('llm_model','brief_llm_model','estimated_cost_usd','brief_cost_usd','writer_cost_usd'):
        data[field]=None
    data['estimated_cost_usd']=0
    data['brief_cost_usd']=0
    data['writer_cost_usd']=0
    for field in ('llm_input_tokens','llm_output_tokens','brief_input_tokens','brief_output_tokens','writer_input_tokens','writer_output_tokens'):
        data[field]=0
    from app.services.article.composition import count_words
    data['word_count']=count_words(data['lead'],data['content'])
    await session.execute(update(Article).where(Article.candidate_id==parent.candidate_id,Article.is_current.is_(True)).values(is_current=False))
    child=Article(**data);session.add(child);await session.flush()
    return child

async def latest_qa(session, article, completed=False):
    query=select(ArticleQA).where(ArticleQA.article_id==article.id)
    if completed: query=query.where(ArticleQA.status=='completed')
    return await session.scalar(query.order_by(ArticleQA.created_at.desc(),ArticleQA.id.desc()).limit(1))

async def approve_version(session,article_id,settings):
    original=await session.get(Article,article_id)
    if not original: raise JobInputError('Article version not found',404)
    await session.scalar(select(Candidate.id).where(Candidate.id==original.candidate_id).with_for_update())
    article=await session.scalar(select(Article).where(Article.id==article_id).with_for_update().execution_options(populate_existing=True))
    qa=await latest_qa(session,article)
    if article.status not in (ArticleStatus.READY_FOR_APPROVAL, ArticleStatus.APPROVED) or qa is None or qa.status!='completed' or not matches_article(qa,article) or (qa.overall_score or 0)<settings.qa_pass_score or qa.critical_issue_count or qa.unsupported_claims_count:
        raise JobInputError('Zatwierdzenie wymaga aktualnego, zaliczonego QA i statusu ready_for_approval.')
    if article.status==ArticleStatus.APPROVED: return article
    await session.execute(update(Article).where(Article.candidate_id==article.candidate_id,Article.status==ArticleStatus.APPROVED).values(status=ArticleStatus.SUPERSEDED))
    article.status=ArticleStatus.APPROVED;article.approved_at=datetime.now(timezone.utc);article.approved_by=None
    await session.commit();await session.refresh(article);return article

async def reject_version(session,article_id,reason):
    article=await session.get(Article,article_id)
    if not article: raise JobInputError('Article version not found',404)
    await session.scalar(select(Candidate.id).where(Candidate.id==article.candidate_id).with_for_update())
    article=await session.scalar(select(Article).where(Article.id==article_id).with_for_update().execution_options(populate_existing=True))
    if article.status==ArticleStatus.SUPERSEDED: raise JobInputError('Wersja została zastąpiona.')
    article.status=ArticleStatus.REJECTED;article.rejection_reason=reason
    await session.commit();await session.refresh(article);return article
