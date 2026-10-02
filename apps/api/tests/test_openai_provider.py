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

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAIProvider(api_key="sk-test", model="test-model", http_client=client)


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
