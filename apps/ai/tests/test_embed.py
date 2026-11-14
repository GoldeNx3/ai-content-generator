# Rola pliku: Testy zadania `embed`: wektory znaczenia tematów do grupowania duplikatów (tryb demo i koszt).

import math

from ai.runtime import run
from app.services.llm.cost import LLMCostCalculator
from app.core.config import DEFAULT_LLM_PRICING


async def test_demo_embed_returns_unit_vectors_for_each_text_at_zero_cost():
    response = await run({"task": "embed", "demo": True, "input": {"texts": ["OpenAI wydało model", "Nowy model od OpenAI"]}})
    assert response["ok"] is True
    vectors = response["result"]["vectors"]
    assert len(vectors) == 2 and len(vectors[0]) == 1536
    assert math.isclose(math.sqrt(sum(v * v for v in vectors[0])), 1.0, rel_tol=1e-6)
    assert float(response["calls"][0]["estimated_cost_usd"]) == 0


async def test_demo_embed_is_deterministic_and_separates_different_texts():
    first = (await run({"task": "embed", "demo": True, "input": {"texts": ["Laravel 13 wydany"]}}))["result"]["vectors"][0]
    again = (await run({"task": "embed", "demo": True, "input": {"texts": ["Laravel 13 wydany"]}}))["result"]["vectors"][0]
    other = (await run({"task": "embed", "demo": True, "input": {"texts": ["Kubernetes 2.0 i nowe API"]}}))["result"]["vectors"][0]
    assert first == again
    assert sum(a * b for a, b in zip(first, other)) < 0.9


async def test_embed_rejects_empty_or_oversized_input():
    assert (await run({"task": "embed", "demo": True, "input": {"texts": []}}))["error"]["code"] == "invalid_input"
    assert (await run({"task": "embed", "demo": True, "input": {"texts": ["x" * 20001]}}))["error"]["code"] == "invalid_input"


def test_embedding_model_is_priced():
    cost = LLMCostCalculator(DEFAULT_LLM_PRICING).estimate("text-embedding-3-small", 1_000_000, 0)
    assert cost is not None and float(cost) == 0.02
