from sqlalchemy import select
from app.models import ArticleFix
from app.services.auto_fix.service import ArticleAutoFixService
from app.services.llm.auto_fix import FixResult
from app.services.llm.cost import LLMCostCalculator

class TrackedFix:
    def __init__(self,provider,recorder): self.provider,self.recorder=provider,recorder
    async def fix(self,payload):
        return await self.recorder.call('fixing_article',lambda:self.provider.fix(payload),FixResult)

async def handle(job,session,execution,providers,recorder,settings):
    report=await session.scalar(select(ArticleFix).where(ArticleFix.job_id==job.id))
    return await ArticleAutoFixService(session,TrackedFix(providers['auto_fix_article'],recorder),
        LLMCostCalculator(settings.llm_pricing),execution,settings,report).fix(job.article_id)

class AutoFixArticleHandler:
    async def handle(self, job, session, execution, providers, recorder, settings):
        return await handle(job, session, execution, providers, recorder, settings)
