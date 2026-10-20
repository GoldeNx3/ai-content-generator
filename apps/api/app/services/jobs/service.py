# Rola pliku: Walidacja enqueue i snapshot wejścia. API zapisuje zadanie,
# ale nie wywołuje LLM. Idempotency-Key identyfikuje jedno żądanie użytkownika.

import hashlib
import json
from dataclasses import asdict, replace
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.demo import is_demo_candidate, demo_settings
from app.models import Article, Candidate, CandidateCategory, Research, ResearchStatus
from app.models.job import ACTIVE_STATUSES, Job
from app.schemas.article import GenerateArticleRequest
from app.services.article.context import build_article_context
from app.services.article.editorial import recent_structures
from app.services.jobs.errors import JobConflict, JobInputError
from app.services.llm.base import CandidateInput


class JobService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def qa(self, article_id, key=None, retry_of=None):
        article = await self.session.get(Article, article_id)
        if article is None:
            raise JobInputError('Article not found', 404)
        return await self.enqueue('qa_article', article.candidate_id, {'article_id': article_id}, key, retry_of)

    async def auto_fix(self, article_id, issue_ids=None, key=None):
        article = await self.session.get(Article, article_id)
        if article is None: raise JobInputError('Article version not found', 404)
        return await self.enqueue('auto_fix_article', article.candidate_id,
            {'article_id': article_id, 'issue_ids': sorted(issue_ids) if issue_ids is not None else None}, key)

    async def _qa_retry_replay(self, article_id, key):
        if not key:
            return None
        replay = await self.session.scalar(select(Job).where(Job.idempotency_key == key))
        if replay:
            if replay.kind != 'qa_article' or replay.article_id != article_id or not replay.retry_of_job_id:
                raise JobConflict('idempotency_conflict', replay.id)
        return replay

    async def retry_qa(self, article_id, key=None):
        from app.models import ArticleQA
        replay = await self._qa_retry_replay(article_id, key)
        if replay:
            return replay
        report = await self.session.scalar(select(ArticleQA).where(ArticleQA.article_id == article_id)
            .order_by(ArticleQA.created_at.desc(), ArticleQA.id.desc()).limit(1))
        # A concurrent same-key request may have committed a new pending report
        # between the first replay lookup and the latest-report read.
        replay = await self._qa_retry_replay(article_id, key)
        if replay:
            return replay
        if report is None or report.job_id is None:
            raise JobInputError('QA report not found', 404)
        return await self.retry(report.job_id, key)

    async def enqueue(self, kind: str, candidate_id: int, options: dict | None = None,
                      key: UUID | None = None, retry_of=None, commit=True) -> Job:
        if kind not in ('classify', 'research', 'write', 'qa_article', 'auto_fix_article', 'prepare_wordpress', 'publish_wordpress'):
            raise JobInputError('Nieznany etap.', 422)
        options = options or {}
        if kind == 'write':
            parent = options.get('parent_version_id')
            options = GenerateArticleRequest.model_validate(options).model_dump(mode='json')
            if parent: options['parent_version_id'] = parent
        key = key or uuid4()
        encoded = json.dumps([kind, candidate_id, options], sort_keys=True, separators=(',', ':'))
        request_hash = hashlib.sha256(encoded.encode()).hexdigest()
        previous = await self._by_key(key, request_hash)
        if previous:
            return previous
        candidate = await self.session.scalar(select(Candidate).where(Candidate.id == candidate_id)
                                              .with_for_update(of=Candidate))
        if candidate is None:
            raise JobInputError('Candidate not found', 404)
        previous = await self._by_key(key, request_hash)
        if previous:
            return previous
        active = await self.session.scalar(select(Job).where(
            Job.candidate_id == candidate_id, Job.status.in_(ACTIVE_STATUSES)))
        if active:
            code = 'job_already_active' if active.request_hash == request_hash else 'candidate_busy'
            raise JobConflict(code, active.id)
        if kind not in ('publish_wordpress','prepare_wordpress') and not self.settings.openai_api_key and not is_demo_candidate(candidate):
            raise JobInputError('OPENAI_API_KEY is not set', 503)
        payload = await self._payload(kind, candidate, options)
        job = Job(id=uuid4(), kind=kind, candidate_id=candidate_id, workspace_id=candidate.workspace_id, payload=payload,
                  idempotency_key=key, request_hash=request_hash,
                  max_attempts=self.settings.job_max_attempts, retry_of_job_id=retry_of)
        self.session.add(job)
        try:
            await self.session.flush([job])
            if kind == 'qa_article':
                from app.models import ArticleQA
                from app.services.qa.context import input_hash
                article = await self.session.scalar(select(Article).where(Article.id == options['article_id'])
                    .with_for_update().execution_options(populate_existing=True))
                job.article_id = article.id
                article.qa_passed = False
                self.session.add(ArticleQA(article_id=article.id, article_version=article.version,
                    job_id=job.id, input_snapshot=payload['qa_context'], input_hash=input_hash(payload['qa_context']),
                    status='pending', pass_score=self.settings.qa_pass_score, issues=[]))
            if kind in ('prepare_wordpress', 'publish_wordpress'):
                job.article_id = options['article_id']
            if kind == 'auto_fix_article':
                from app.models import ArticleFix
                from app.services.qa.context import input_hash
                context = payload['fix_context']
                job.article_id = options['article_id']
                self.session.add(ArticleFix(source_article_version_id=job.article_id, qa_id=context['qa_id'],
                    job_id=job.id, input_snapshot=context, input_hash=input_hash(context), iteration=context['iteration'],
                    issues_requested=len(context['issues']), status='pending', issues=[]))
            if not commit:
                await self.session.flush()
                return job
            await self.session.commit()
        except IntegrityError as exc:
            # Inny kandydat może użyć globalnie tego samego klucza w tym czasie.
            await self.session.rollback()
            previous = await self._by_key(key, request_hash)
            if previous:
                return previous
            if 'uq_jobs_active_candidate' not in str(exc.orig):
                raise
            raise JobConflict('candidate_busy')
        await self.session.refresh(job)
        return job

    async def _by_key(self, key, request_hash) -> Job | None:
        job = await self.session.scalar(select(Job).where(Job.idempotency_key == key))
        if job and job.request_hash != request_hash:
            raise JobConflict('idempotency_conflict', job.id)
        return job

    async def _payload(self, kind, candidate, options) -> dict:
        # Snapshot zawiera ustawienia wykonania, ale nigdy klucze ani URL bazy.
        settings = self.settings.model_dump(exclude={
            'wordpress_username', 'wordpress_app_password', 'secrets_key', 'openai_api_key', 'tavily_api_key', 'database_url', 'test_database_url', 'cors_origins',
        })
        if is_demo_candidate(candidate):
            settings = demo_settings(settings)
        payload = {'payload_version': 1, 'options': options, 'settings': settings,
                   'candidate_input': jsonable_encoder(asdict(CandidateInput(
                       candidate.title, candidate.summary, candidate.source.name,
                       candidate.original_published_at))), 'original_url': candidate.external_url}
        if is_demo_candidate(candidate):
            payload['demo'] = True
        research = await self.session.scalar(select(Research).where(Research.candidate_id == candidate.id))
        if kind == 'research' and not options.get('discover', True) and research is None:
            raise JobInputError('Research not found - start a research first', 404)
        if kind in ('prepare_wordpress', 'publish_wordpress'):
            from app.services.wordpress.api_helpers import approved_version
            await approved_version(self.session, options['article_id'], self.settings)
        if kind == 'qa_article':
            from app.services.qa.context import build_qa_payload
            article = await self.session.scalar(select(Article).where(Article.id == options.get('article_id'))
                .with_for_update().execution_options(populate_existing=True))
            if article is None:
                raise JobInputError('Article not found', 404)
            if article.candidate_id != candidate.id:
                raise JobInputError('Article belongs to another candidate', 409)
            if research is not None and article.research_id is not None and research.id != article.research_id:
                raise JobInputError('Article research does not belong to candidate', 409)
            payload['qa_context'] = build_qa_payload(article)
        if kind == 'auto_fix_article':
            from app.services.auto_fix.context import prepare_fix
            article = await self.session.scalar(select(Article).where(Article.id == options['article_id'])
                .with_for_update().execution_options(populate_existing=True))
            if article is None or article.candidate_id != candidate.id:
                raise JobInputError('Article version not found', 404)
            _, payload['fix_context'] = await prepare_fix(self.session, article, options.get('issue_ids'), self.settings)
        if kind == 'write':
            if research is None or research.status != ResearchStatus.COMPLETED or not research.facts:
                raise JobInputError('Complete research before generating an article.')
            request = GenerateArticleRequest.model_validate(options)
            article_type = request.article_type or candidate.category or CandidateCategory.NEWS
            context = build_article_context(candidate, research, article_type, request, self.settings)
            context = replace(context, recent_structures=await recent_structures(self.session))
            payload['context'] = jsonable_encoder(asdict(context))
            payload['research_id'] = research.id
        return payload

    async def retry(self, job_id, key=None) -> Job:
        previous = await self.session.get(Job, job_id)
        if previous is None:
            raise JobInputError('Job not found', 404)
        if previous.status != 'failed':
            raise JobConflict('job_not_failed', previous.id)
        if previous.kind in ('publish_wordpress','prepare_wordpress'):
            from app.services.wordpress.api_helpers import enqueue_wordpress
            return await enqueue_wordpress(self, previous.article_id, previous.payload['options'], key, previous.kind, previous.id)
        return await self.enqueue(previous.kind, previous.candidate_id,
                                  previous.payload['options'], key, previous.id)

    async def regenerate(self, article_id, request, key=None) -> Job:
        article = await self.session.get(Article, article_id)
        if article is None:
            raise JobInputError('Article not found', 404)
        options = GenerateArticleRequest.model_validate(article.generation_options)
        if request:
            options = GenerateArticleRequest.model_validate({
                **options.model_dump(), **request.model_dump(exclude_unset=True),
            })
        return await self.enqueue('write', article.candidate_id, {**options.model_dump(mode='json'), 'parent_version_id': article.id}, key)

    async def batch(self, limit: int, key: UUID | None = None, *, workspace_id: int) -> dict:
        from app.services.jobs.batch import enqueue_batch
        return await enqueue_batch(self, limit, key, workspace_id=workspace_id)
