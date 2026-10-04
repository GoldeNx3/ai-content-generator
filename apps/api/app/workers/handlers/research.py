# Rola pliku: Przygotowanie lub wznowienie researchu bez resetu po każdej awarii.

from pydantic import TypeAdapter
from app.models import Research, ResearchStatus
from app.services.llm.base import CandidateInput
from app.services.llm.cost import LLMCostCalculator
from app.services.research.factory import build_content_extractor
from app.services.research.research import ResearchService
from app.services.research.search import get_search_provider
from app.workers.calls import TrackedResearcher


async def handle(job, session, execution, providers, recorder, settings):
    extractor = providers.get('extractor') or build_content_extractor(settings)
    search = providers.get('search') or get_search_provider(settings)
    service = ResearchService(session, extractor, search,
                              TrackedResearcher(providers['research'], recorder),
                              LLMCostCalculator(settings.llm_pricing), settings, execution)
    service.pipeline.candidate_input = TypeAdapter(CandidateInput).validate_python(job.payload['candidate_input'])
    research_id = execution.checkpoints.get('research_id')
    discover = job.payload['options'].get('discover', True)
    if research_id is None:
        research = await service.start(job.candidate_id, discover)
        research_id = research.id
    else:
        research = await session.get(Research, research_id)
        # Poprzednia próba mogła przygotować fakty, ale nie opublikować raportu.
        # Źródła zachowujemy. Dzierżawa chroni czyszczenie przed starym workerem.
        research.facts.clear()
        research.status = ResearchStatus.RUNNING
        await execution.commit(session)
    return await service.run(research_id, discover)
