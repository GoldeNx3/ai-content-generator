# Rola pliku: Błędy dostawcy są klasyfikowane jawnie; SDK nie mnoży prób kolejki.

import httpx
import pytest

from app.schemas.research import SearchQueries
from app.services.llm.base import LLMError
from app.services.llm.client import OpenAIClient
from tests.test_openai_provider import responses_payload


@pytest.mark.parametrize('status,retryable', [(401, False), (429, True), (500, True), (503, True)])
async def test_worker_transport_has_no_hidden_retries(status, retryable):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(status, json={'error': {'message': 'test', 'type': 'test'}},
                              headers={'Retry-After': '45'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = OpenAIClient('test', http_client=http, max_retries=0)
        with pytest.raises(LLMError) as raised:
            await client.parse('test', 'system', 'user', SearchQueries, timeout=0.5)
    assert len(requests) == 1
    assert raised.value.retryable is retryable
    assert raised.value.retry_after == 45
    assert raised.value.code == f'llm_http_{status}'


async def test_response_id_is_preserved_for_attempt_ledger():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=responses_payload('{"queries":["test"]}')),
    )) as http:
        client = OpenAIClient('test', http_client=http, max_retries=0)
        result, usage = await client.parse('test', 'system', 'user', SearchQueries)
    assert result.queries == ['test']
    assert usage.response_id == 'resp_1'
