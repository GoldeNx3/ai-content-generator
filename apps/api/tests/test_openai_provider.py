# Rola pliku: Testy modułu openai_provider: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

"""OpenAIProvider tests with a mocked HTTP transport - no real requests to OpenAI."""

import json

import httpx
import pytest

from app.models import CandidateCategory
from app.services.llm.base import CandidateInput, LLMError, LLMNotConfiguredError
from app.services.llm.openai_provider import OpenAIProvider

CANDIDATE = CandidateInput(title="GPT-6 released", summary=None, source="OpenAI", published_at=None)


def responses_payload(output_text: str) -> dict[str, object]:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": "test-model",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output_text, "annotations": []}],
            }
        ],
    }


def provider_returning(response: httpx.Response, captured: list[httpx.Request]) -> OpenAIProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return response

    # MockTransport przechwytuje HTTP i zwraca odpowiedź z lokalnej funkcji; to wywołanie nie trafia do
    # Internetu.
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAIProvider(api_key="sk-test", model="test-model", http_client=client)


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_parses_structured_output() -> None:
    body = {
        "relevance": 95,
        "freshness": 90,
        "search_potential": 85,
        "commercial_potential": 40,
        "category": "release",
        "reason": "Nowy model OpenAI.",
    }
    captured: list[httpx.Request] = []
    provider = provider_returning(httpx.Response(200, json=responses_payload(json.dumps(body))), captured)

    result = await provider.classify_candidate(CANDIDATE)

    assert result.relevance == 95
    assert result.category == CandidateCategory.RELEASE
    sent = json.loads(captured[0].content)
    assert sent["model"] == "test-model"
    assert sent["text"]["format"]["type"] == "json_schema"
    assert "total_score" not in sent["text"]["format"]["schema"]["properties"]


async def test_out_of_range_score_raises_llm_error() -> None:
    body = {
        "relevance": 150,
        "freshness": 90,
        "search_potential": 85,
        "commercial_potential": 40,
        "category": "release",
        "reason": "x",
    }
    provider = provider_returning(httpx.Response(200, json=responses_payload(json.dumps(body))), [])

    with pytest.raises(LLMError):
        await provider.classify_candidate(CANDIDATE)


async def test_api_error_raises_llm_error() -> None:
    provider = provider_returning(httpx.Response(401, json={"error": {"message": "bad key"}}), [])

    with pytest.raises(LLMError):
        await provider.classify_candidate(CANDIDATE)


def test_missing_api_key() -> None:
    with pytest.raises(LLMNotConfiguredError):
        OpenAIProvider(api_key="", model="test-model")

async def test_classification_preserves_usage_without_adding_it_to_llm_schema() -> None:
    body = dict(relevance=90, freshness=80, search_potential=70, commercial_potential=60, category="news", reason="test")
    payload = responses_payload(json.dumps(body))
    payload["usage"] = {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200}
    captured = []
    provider = provider_returning(httpx.Response(200, json=payload), captured)
    result = await provider.classify_candidate(CANDIDATE)
    assert result._usage == {"model": "test-model", "input_tokens": 1000, "output_tokens": 200}
    schema = json.loads(captured[0].content)["text"]["format"]["schema"]["properties"]
    assert "_usage" not in schema

async def test_missing_classification_usage_stays_unknown() -> None:
    body = dict(relevance=90, freshness=80, search_potential=70, commercial_potential=60, category="news", reason="test")
    provider = provider_returning(httpx.Response(200, json=responses_payload(json.dumps(body))), [])
    result = await provider.classify_candidate(CANDIDATE)
    assert result._usage is None
