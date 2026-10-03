# Rola pliku: Przekazuje wpis do dostawcy LLM, zapisuje cztery oceny i kategorię oraz wylicza wynik
# łączny w backendzie.

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.llm.cost import LLMCostCalculator
from app.models import Candidate
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.classification import ClassifyBatchResult
from app.services.llm.base import CandidateInput, LLMNotConfiguredError, LLMProvider
from app.services.scoring import compute_total_score

logger = logging.getLogger(__name__)


class ClassificationService:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, session: AsyncSession, provider: LLMProvider) -> None:
        self.session = session
        self.provider = provider
        self.candidates = CandidateRepository(session)

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
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
        usage = classification._usage
        candidate.llm_model = str(usage["model"]) if usage else None
        candidate.llm_input_tokens = int(usage["input_tokens"]) if usage else None
        candidate.llm_output_tokens = int(usage["output_tokens"]) if usage else None
        candidate.estimated_cost_usd = (
            LLMCostCalculator(get_settings().llm_pricing).estimate(
                candidate.llm_model, candidate.llm_input_tokens, candidate.llm_output_tokens
            ) if usage else None
        )
        candidate.relevance_score = classification.relevance
        candidate.freshness_score = classification.freshness
        candidate.search_potential_score = classification.search_potential
        candidate.commercial_potential_score = classification.commercial_potential
        candidate.total_score = compute_total_score(classification)
        candidate.category = classification.category
        candidate.llm_reason = classification.reason
        candidate.classified_at = datetime.now(UTC)
        # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
        # trwałego zapisu.
        await self.session.commit()
        # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
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
                # rollback wycofuje niezakończoną transakcję po błędzie; wcześniejsze commity pozostają
                # zapisane.
                await self.session.rollback()
                result.errors += 1
        return result
