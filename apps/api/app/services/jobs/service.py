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

    async def enqueue(self, kind: str, candidate_id: int, options: dict | None = None,
                      key: UUID | None = None, retry_of=None) -> Job:
        if kind not in ('classify', 'research', 'write'):
            raise JobInputError('Nieznany etap.', 422)
        options = options or {}
        if kind == 'write':
            options = GenerateArticleRequest.model_validate(options).model_dump(mode='json')
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
        if not self.settings.openai_api_key:
            raise JobInputError('OPENAI_API_KEY is not set', 503)
        payload = await self._payload(kind, candidate, options)
        job = Job(kind=kind, candidate_id=candidate_id, payload=payload,
                  idempotency_key=key, request_hash=request_hash,
                  max_attempts=self.settings.job_max_attempts, retry_of_job_id=retry_of)
        self.session.add(job)
        try:
            await self.session.commit()
        except IntegrityError:
            # Inny kandydat może użyć globalnie tego samego klucza w tym czasie.
            await self.session.rollback()
            previous = await self._by_key(key, request_hash)
            if previous:
                return previous
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
            'openai_api_key', 'tavily_api_key', 'database_url', 'test_database_url', 'cors_origins',
        })
        payload = {'payload_version': 1, 'options': options, 'settings': settings,
                   'candidate_input': jsonable_encoder(asdict(CandidateInput(
                       candidate.title, candidate.summary, candidate.source.name,
                       candidate.original_published_at))), 'original_url': candidate.external_url}
        research = await self.session.scalar(select(Research).where(Research.candidate_id == candidate.id))
        if kind == 'research' and not options.get('discover', True) and research is None:
            raise JobInputError('Research not found - start a research first', 404)
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
        return await self.enqueue('write', article.candidate_id, options.model_dump(mode='json'), key)

    async def batch(self, limit: int, key: UUID | None = None) -> dict:
        from app.services.jobs.batch import enqueue_batch
        return await enqueue_batch(self, limit, key)
