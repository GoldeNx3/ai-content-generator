# Rola pliku: Generacja nowej wersji z wejścia zamrożonego podczas enqueue.

from pydantic import TypeAdapter
from app.schemas.article import GenerateArticleRequest
from app.services.article.write import ArticleService
from app.services.llm.base import ArticleContext
from app.services.llm.cost import LLMCostCalculator
from app.workers.calls import TrackedWriter


async def handle(job, session, execution, providers, recorder, settings):
    service = ArticleService(session, TrackedWriter(providers['write'], recorder),
                             LLMCostCalculator(settings.llm_pricing), execution)
    context = TypeAdapter(ArticleContext).validate_python(job.payload['context'])
    request = GenerateArticleRequest.model_validate(job.payload['options'])
    return await service.generate(job.candidate_id, request, context=context)
