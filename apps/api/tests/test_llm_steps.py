# Rola pliku: Sprawdza, czy każdy etap wybiera właściwy model i zwraca
# zwalidowane dane oraz zużycie tokenów. HTTP jest lokalne i bezpłatne.

import json

import httpx
import pytest

from app.services.llm.base import ArticleContext, ResearchDocument
from app.services.llm.openai_provider import OpenAIProvider
from tests.article_fakes import make_brief, make_output
from tests.research_fakes import default_output
from tests.test_openai_provider import CANDIDATE, responses_payload


def context() -> ArticleContext:
    # Dane bez bazy: ten test dotyczy granicy serwis → dostawca LLM → HTTP.
    return ArticleContext(
        candidate_title="Test", candidate_source="Example", published_at=None,
        research_summary="Test", why_it_matters=None, suggested_angle=None,
        facts=[], sources=[], uncertainties=[], conflicts=[], article_type="news",
        type_guide="news", length_hint="krótki", angle=None, instructions=None,
    )


@pytest.mark.parametrize("step, expected_model", [
    ("queries", "research-model"), ("research", "research-model"),
    ("brief", "brief-model"), ("write", "writer-model"),
])
async def test_each_step_uses_its_model_and_preserves_tokens(step: str, expected_model: str) -> None:
    document = ResearchDocument(
        url="https://example.com/news", title="Test", publisher="Example",
        source_type="official", source_score=100, published_at=None, content="Treść",
    )
    outputs = {
        "queries": {"queries": ["test official"]},
        "research": default_output([document]).model_dump(mode="json"),
        "brief": make_brief([1, 2]).model_dump(mode="json"),
        "write": make_output([1, 2], [1]).model_dump(mode="json"),
    }
    requests: list[dict] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        payload = responses_payload(json.dumps(outputs[step]))
        payload["model"] = expected_model
        payload["usage"] = {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAIProvider(
            api_key="sk-test", model="classifier-model", research_model="research-model",
            brief_model="brief-model", writer_model="writer-model", http_client=client,
        )
        if step == "queries":
            result = await provider.generate_search_queries(CANDIDATE)
            assert result.queries.queries == ["test official"]
        elif step == "research":
            result = await provider.research(CANDIDATE, [document])
            assert result.output.summary == "OpenAI udostępniło API GPT-6."
        elif step == "brief":
            result = await provider.generate_brief(context())
            assert result.brief.required_facts == [1, 2]
        else:
            result = await provider.write_article(context(), make_brief([1, 2]))
            assert result.output.lead_fact_ids == [1]

    assert requests[0]["model"] == expected_model
    assert result.usage.model == expected_model
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 30


async def test_unset_step_models_fall_back_to_classifier_model() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        # Odpowiedź modelu jest prawdziwie parsowana przez SDK, a nie udawana
        # na poziomie metody serwisu.
        sent = json.loads(request.content)
        assert sent["model"] == "fallback-model"
        return httpx.Response(200, json=responses_payload('{"queries": ["test"]}'))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAIProvider(api_key="sk-test", model="fallback-model", http_client=client)
        result = await provider.generate_search_queries(CANDIDATE)
    assert result.queries.queries == ["test"]
