# Rola pliku: Rejestruje płatne wywołania i ich checkpointy.
# Udana odpowiedź jest zapisywana przed kolejnym krokiem. Retry korzysta z
# zapisanego wyniku zamiast ponownie płacić za ukończony brief lub analizę.

from dataclasses import asdict, is_dataclass

from pydantic import TypeAdapter

from app.schemas.article import ArticleBrief
from app.schemas.classification import CandidateClassification
from app.services.llm.base import BriefResult, QueriesResult, ResearchResult, WriterResult
from app.services.llm.cost import LLMCostCalculator


class CallRecorder:
    def __init__(self, execution, pricing) -> None:
        self.execution = execution
        self.costs = LLMCostCalculator(pricing)

    async def call(self, stage, invoke, result_type):
        adapter = TypeAdapter(result_type)
        await self.execution.stage(stage)
        cached = self.execution.checkpoints.get(stage)
        if cached:
            result = adapter.validate_python(cached['data'])
            if isinstance(result, CandidateClassification):
                result._usage = cached.get('usage')
            return result
        await self.execution.record_call(stage, {'finished': False, 'estimated_cost_usd': None})
        result = await invoke()
        usage = getattr(result, 'usage', None) or getattr(result, '_usage', None)
        usage = asdict(usage) if is_dataclass(usage) else usage
        cost = None
        if usage and usage.get('recorded', True):
            cost = self.costs.estimate(usage['model'], usage['input_tokens'], usage['output_tokens'])
        data = adapter.dump_python(result, mode='json')
        await self.execution.record_call(stage, {
            'finished': True, 'usage': usage, 'response_id': usage.get('response_id') if usage else None, 'estimated_cost_usd': str(cost) if cost is not None else None,
        }, checkpoint={stage: {'data': data, 'usage': usage}})
        return result


class TrackedClassifier:
    def __init__(self, provider, recorder) -> None:
        self.provider = provider
        self.recorder = recorder

    async def classify_candidate(self, candidate):
        return await self.recorder.call('classifying', lambda: self.provider.classify_candidate(candidate), CandidateClassification)


class TrackedResearcher:
    def __init__(self, provider, recorder) -> None:
        self.provider = provider
        self.recorder = recorder

    async def generate_search_queries(self, candidate):
        return await self.recorder.call('discovering_sources', lambda: self.provider.generate_search_queries(candidate), QueriesResult)

    async def research(self, candidate, documents):
        return await self.recorder.call('analysing', lambda: self.provider.research(candidate, documents), ResearchResult)


class TrackedWriter:
    def __init__(self, provider, recorder) -> None:
        self.provider = provider
        self.recorder = recorder

    async def generate_brief(self, context):
        return await self.recorder.call('building_brief', lambda: self.provider.generate_brief(context), BriefResult)

    async def write_article(self, context, brief: ArticleBrief):
        return await self.recorder.call('writing', lambda: self.provider.write_article(context, brief), WriterResult)
