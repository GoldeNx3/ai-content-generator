# Rola pliku: Zadanie `classify`: cztery oceny, kategoria i uzasadnienie tematu oraz wynik łączny.

from datetime import datetime

from pydantic import BaseModel

from ai.context import TaskContext
from app.schemas.editorial import EditorialProfile
from app.services.llm.base import CandidateInput
from app.services.scoring import compute_total_score


class CoveredBy(BaseModel):
    title: str
    article_id: int
    similarity: float


class CandidatePayload(BaseModel):
    title: str
    summary: str | None = None
    source: str
    published_at: datetime | None = None
    already_covered: CoveredBy | None = None


class ClassifyInput(BaseModel):
    candidate: CandidatePayload
    editorial: EditorialProfile | None = None


async def run(data: dict, ctx: TaskContext) -> dict:
    request = ClassifyInput.model_validate(data)
    payload = request.candidate
    candidate = CandidateInput(payload.title, payload.summary, payload.source, payload.published_at)
    classifier = ctx.providers["classify"]
    classification = await ctx.call("classifying", lambda: classifier.classify_candidate(candidate, request.editorial))
    if payload.already_covered is not None:
        # Temat bardzo podobny do już napisanego artykułu: świeżość dla bloga niska, decyzja zostaje u redaktora.
        covered = payload.already_covered
        classification = classification.model_copy(update={
            "freshness": min(classification.freshness, 20),
            "reason": f"Uwaga: podobny temat już opisany w artykule #{covered.article_id} „{covered.title}” "
                      f"(podobieństwo {covered.similarity:.2f}). {classification.reason}",
        })
    return {
        "relevance": classification.relevance,
        "freshness": classification.freshness,
        "search_potential": classification.search_potential,
        "commercial_potential": classification.commercial_potential,
        "total_score": compute_total_score(classification),
        "category": classification.category,
        "reason": classification.reason,
    }
