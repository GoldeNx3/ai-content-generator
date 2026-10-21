# Rola pliku: Testy kontraktu CLI `python -m ai`: JSON na wejściu, JSON z wynikiem lub kodem błędu na wyjściu.

import json
import subprocess
import sys
from pathlib import Path

from ai.runtime import run

API_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = {"title": "Nowy model językowy", "summary": "Opis", "source": "Blog", "published_at": None}


def cli(payload: str) -> dict:
    process = subprocess.run([sys.executable, "-m", "ai"], input=payload, capture_output=True, text=True,
                             cwd=API_ROOT, timeout=60, check=True)
    return json.loads(process.stdout)


async def test_unknown_task_is_not_retryable():
    response = await run({"task": "nope"})
    assert response["ok"] is False
    assert response["error"]["code"] == "unknown_task"
    assert response["error"]["retryable"] is False
    assert response["calls"] == []


async def test_invalid_input_returns_validation_error():
    response = await run({"task": "classify", "demo": True, "input": {"candidate": {"title": "x"}}})
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_input"


async def test_demo_classify_records_zero_cost_call():
    response = await run({"task": "classify", "demo": True, "input": {"candidate": CANDIDATE}})
    assert response["ok"] is True
    result = response["result"]
    assert 0 <= result["total_score"] <= 100
    assert result["category"]
    assert len(response["calls"]) == 1
    assert response["calls"][0]["finished"] is True
    assert float(response["calls"][0]["estimated_cost_usd"]) == 0


def test_cli_reads_stdin_and_writes_single_json_document():
    response = cli(json.dumps({"task": "classify", "demo": True, "input": {"candidate": CANDIDATE}}))
    assert response["ok"] is True
    assert set(response["result"]) >= {"relevance", "freshness", "search_potential", "commercial_potential"}


def test_cli_rejects_malformed_json():
    response = cli("{not json")
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_input"
