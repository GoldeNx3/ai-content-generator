"""QA handler shares queue leases, cost tracking and checkpoints."""
from sqlalchemy import select
from app.models import ArticleQA
from app.services.llm.qa import QAResult
from app.services.llm.cost import LLMCostCalculator
from app.services.qa.service import ArticleQAService


class TrackedQA:
    def __init__(self, provider, recorder):
        self.provider, self.recorder = provider, recorder

    async def evaluate(self, payload):
        return await self.recorder.call('fact_checking', lambda: self.provider.evaluate(payload), QAResult)


async def handle(job, session, execution, providers, recorder, settings):
    report = await session.scalar(select(ArticleQA).where(ArticleQA.job_id == job.id))
    service = ArticleQAService(session, TrackedQA(providers['qa_article'], recorder),
        LLMCostCalculator(settings.llm_pricing), execution, settings, report)
    return await service.evaluate(job.article_id)
