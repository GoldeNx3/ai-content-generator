"""Contract regression for the single evidence-only OpenAI request."""
import json

from app.services.llm.qa import OpenAIQA, QA_SYSTEM_PROMPT
from app.services.llm.base import LLMUsage
from app.schemas.qa import QAOutput
from tests.test_qa_units import output, payload


async def test_provider_uses_one_structured_request_without_search_tools():
    calls = []
    class Client:
        async def parse(self, model, system, user, schema, timeout=None):
            calls.append((model, system, json.loads(user), schema, timeout))
            return output(), LLMUsage('configured-model', 10, 20)
    provider = OpenAIQA(Client(), 'configured-model', 90)
    result = await provider.evaluate(payload())
    assert len(calls) == 1
    assert calls[0][0] == 'configured-model' and calls[0][3] is QAOutput
    assert calls[0][2] == payload() and calls[0][4] == 90
    assert result.usage.input_tokens == 10
    for rule in ['Nie oceniaj artykułu względem własnej wiedzy', 'Nie wykonuj nowego researchu',
                 'Nie zgaduj', 'unsupported_quote critical', 'ignored_conflict', 'missing_uncertainty',
                 'nie wymagaj dosłownego', 'Nie dopisuj własnych słów']:
        assert rule in QA_SYSTEM_PROMPT
