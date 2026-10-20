# Rola pliku: Testy budżetu AI per workspace: zużycie z zapisów płatnych wywołań (bieżący miesiąc,
# nieznane koszty), blokada nowych płatnych zadań, wyjątki (powtórzenie klucza, demo, inny workspace,
# brak limitu), klasyfikacja zbiorcza, scheduler i endpoint /api/usage.

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.demo import DEMO_PREFIX
from app.models import Candidate, Source, Workspace
from app.models.job import Job, JobAttempt
from app.services.jobs.errors import JobInputError
from app.services.jobs.service import JobService
from app.services.usage import period_start, usage_for

SETTINGS = Settings(openai_api_key="test", default_monthly_budget_usd=1.0)


async def make_candidate(session, workspace_id=1, url="https://example.com/budget"):
    source = await session.scalar(select(Source).where(Source.workspace_id == workspace_id))
    if source is None:
        source = Source(workspace_id=workspace_id, name=f"Feed {workspace_id}", url=f"https://example.com/{workspace_id}.xml")
        session.add(source)
        await session.flush()
    candidate = Candidate(workspace_id=workspace_id, source_id=source.id, external_url=url, title="Temat")
    session.add(candidate)
    await session.commit()
    return candidate


async def spend(session, candidate, *costs, started_at=None, status="succeeded"):
    """Zapisuje zakończony job z próbą i płatnymi wywołaniami (jak CallRecorder)."""
    job = Job(id=uuid4(), workspace_id=candidate.workspace_id, candidate_id=candidate.id, kind="classify",
              status=status, payload={}, request_hash="x")
    session.add(job)
    await session.flush()
    calls = [{"stage": "classifying", "finished": cost is not None,
              "estimated_cost_usd": None if cost is None else str(cost)} for cost in costs]
    session.add(JobAttempt(job_id=job.id, number=1, worker_id="test", llm_calls=calls,
                           started_at=started_at or datetime.now(UTC)))
    await session.commit()
    return job


async def test_usage_counts_current_month_and_unknown_calls(session):
    candidate = await make_candidate(session)
    await spend(session, candidate, Decimal("0.25"), Decimal("0.10"), None)
    await spend(session, await make_candidate(session, url="https://example.com/old"), Decimal("5"),
                started_at=period_start() - timedelta(days=1))
    other = await make_candidate(session, workspace_id=2, url="https://example.com/b")
    await spend(session, other, Decimal("3"))
    usage = await usage_for(session, 1, SETTINGS)
    assert usage.spent_usd == Decimal("0.35") and usage.unknown_cost_calls == 1
    assert usage.budget_usd == Decimal("1.0") and usage.remaining_usd == Decimal("0.65") and not usage.exceeded


async def test_exceeded_budget_blocks_new_paid_jobs_only(session):
    candidate = await make_candidate(session)
    key = uuid4()
    first = await JobService(session, SETTINGS).enqueue("classify", candidate.id, key=key)
    first.status = "succeeded"
    await session.commit()
    await spend(session, candidate, Decimal("1.20"))
    service = JobService(session, SETTINGS)
    # Powtórzenie z tym samym kluczem zwraca istniejący job mimo przekroczenia.
    assert (await service.enqueue("classify", candidate.id, key=key)).id == first.id
    with pytest.raises(JobInputError) as blocked:
        await service.enqueue("research", candidate.id)
    assert blocked.value.status_code == 402 and str(blocked.value) == "budget_exceeded"
    # Inny workspace ma własny budżet.
    other = await make_candidate(session, workspace_id=2, url="https://example.com/other")
    assert (await service.enqueue("classify", other.id)).workspace_id == 2


async def test_demo_candidates_are_free(session):
    candidate = await make_candidate(session)
    await spend(session, candidate, Decimal("2"))
    demo = await make_candidate(session, url=DEMO_PREFIX + "checks/budget")
    assert (await JobService(session, Settings(openai_api_key="", default_monthly_budget_usd=1.0))
            .enqueue("classify", demo.id)).status == "queued"


async def test_workspace_override_and_unlimited(session):
    candidate = await make_candidate(session)
    await spend(session, candidate, Decimal("2"))
    workspace = await session.get(Workspace, 1)
    workspace.monthly_budget_usd = Decimal("50")
    await session.commit()
    assert (await JobService(session, SETTINGS).enqueue("classify", candidate.id)).status == "queued"
    workspace.monthly_budget_usd = None
    await session.commit()
    unlimited = Settings(openai_api_key="test", default_monthly_budget_usd=None)
    usage = await usage_for(session, 1, unlimited)
    assert usage.budget_usd is None and usage.remaining_usd is None and not usage.exceeded


async def test_classify_pending_and_endpoint_report_budget(client, session):
    candidate = await make_candidate(session)
    await spend(session, candidate, Decimal("11"))  # domyślny budżet .env = 10 USD
    await make_candidate(session, url="https://example.com/unclassified")
    response = await client.post("/api/candidates/classify-pending")
    assert response.status_code == 402 and response.json()["detail"] == "budget_exceeded"
    usage = (await client.get("/api/usage")).json()
    assert usage["exceeded"] is True and Decimal(usage["spent_usd"]) == Decimal("11")
    assert Decimal(usage["remaining_usd"]) == 0


async def test_scheduler_skips_workspace_over_budget(session, session_factory, engine, monkeypatch):
    from app.jobs import scheduler
    spent = await make_candidate(session, url="https://example.com/spent")
    await spend(session, spent, Decimal("2"))
    blocked = await make_candidate(session, url="https://example.com/a1")
    allowed = await make_candidate(session, workspace_id=2, url="https://example.com/b1")

    async def fake_fetch(*_, **__):
        return SimpleNamespace(model_dump=lambda: {"new_candidates": 0})
    monkeypatch.setattr(scheduler, "engine", engine)
    monkeypatch.setattr(scheduler, "SessionLocal", session_factory)
    monkeypatch.setattr(scheduler, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(scheduler.IngestionService, "fetch_all_active", fake_fetch)
    await scheduler.run_pipeline_once()
    queued = {job.candidate_id for job in (await session.scalars(select(Job).where(Job.status == "queued"))).all()}
    assert allowed.id in queued and blocked.id not in queued
