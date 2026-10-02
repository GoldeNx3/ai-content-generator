import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.classification import ClassifyBatchResult
from app.services.llm.base import CandidateInput, LLMNotConfiguredError, LLMProvider
from app.services.scoring import compute_total_score

logger = logging.getLogger(__name__)


class ClassificationService:
    def __init__(self, session: AsyncSession, provider: LLMProvider) -> None:
        self.session = session
        self.provider = provider
        self.candidates = CandidateRepository(session)

    async def classify(self, candidate: Candidate) -> Candidate:
        """Classify one candidate. On LLM failure raises LLMError and leaves the row untouched."""
        classification = await self.provider.classify_candidate(
            CandidateInput(
                title=candidate.title,
                summary=candidate.summary,
                source=candidate.source.name,
                published_at=candidate.original_published_at,
            )
        )
        candidate.relevance_score = classification.relevance
        candidate.freshness_score = classification.freshness
        candidate.search_potential_score = classification.search_potential
        candidate.commercial_potential_score = classification.commercial_potential
        candidate.total_score = compute_total_score(classification)
        candidate.category = classification.category
        candidate.llm_reason = classification.reason
        candidate.classified_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def classify_pending(self, limit: int | None = None) -> ClassifyBatchResult:
        """Sequentially classifies unclassified candidates (newest first); one failure doesn't stop the batch."""
        result = ClassifyBatchResult()
        for candidate_id in await self.candidates.list_unclassified_ids(limit):
            candidate = await self.candidates.get(candidate_id)
            if candidate is None:
                continue
            result.processed += 1
            try:
                await self.classify(candidate)
                result.classified += 1
            except LLMNotConfiguredError:
                raise
            except Exception:
                logger.exception("Classification of candidate %s failed", candidate_id)
                await self.session.rollback()
                result.errors += 1
        return result
