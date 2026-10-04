# Rola pliku: Jeden krok klasyfikacji. Wynik i sukces są zapisywane razem.

from pydantic import TypeAdapter
from app.models import Candidate
from app.services.classification_service import ClassificationService
from app.services.llm.base import CandidateInput
from app.workers.calls import TrackedClassifier


async def handle(job, session, execution, providers, recorder, settings):
    candidate = await session.get(Candidate, job.candidate_id)
    provider = TrackedClassifier(providers['classify'], recorder)
    snapshot = TypeAdapter(CandidateInput).validate_python(job.payload['candidate_input'])
    return await ClassificationService(session, provider, execution, settings.llm_pricing).classify(candidate, snapshot)
