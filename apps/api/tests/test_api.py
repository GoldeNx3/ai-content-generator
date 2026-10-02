import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_provider
from app.models import Candidate, CandidateCategory, CandidateStatus, Source
from tests.test_classification import FakeProvider


async def test_source_crud(client: httpx.AsyncClient) -> None:
    created = await client.post("/api/sources", json={"name": "Feed", "url": "https://example.com/rss"})
    assert created.status_code == 201
    source_id = created.json()["id"]

    duplicate = await client.post("/api/sources", json={"name": "Feed", "url": "https://example.com/rss"})
    assert duplicate.status_code == 409

    invalid = await client.post("/api/sources", json={"name": "Feed", "url": "not-a-url"})
    assert invalid.status_code == 422

    patched = await client.patch(f"/api/sources/{source_id}", json={"active": False})
    assert patched.json()["active"] is False

    assert len((await client.get("/api/sources")).json()) == 1
    assert (await client.delete(f"/api/sources/{source_id}")).status_code == 204
    assert (await client.get("/api/sources")).json() == []


async def test_candidate_list_filters_sorting_and_status(
    client: httpx.AsyncClient, session: AsyncSession, source: Source
) -> None:
    session.add_all(
        [
            Candidate(source_id=source.id, external_url="https://e.com/a", title="A", total_score=90,
                      category=CandidateCategory.RELEASE),
            Candidate(source_id=source.id, external_url="https://e.com/b", title="B", total_score=40,
                      category=CandidateCategory.NEWS),
            Candidate(source_id=source.id, external_url="https://e.com/c", title="C"),
        ]
    )
    await session.commit()

    page = (await client.get("/api/candidates")).json()
    assert page["total"] == 3
    assert [item["title"] for item in page["items"]] == ["A", "B", "C"]  # score desc, nulls last
    assert page["items"][0]["source_name"] == "Test Feed"

    filtered = (await client.get("/api/candidates", params={"min_score": 50})).json()
    assert [item["title"] for item in filtered["items"]] == ["A"]

    by_category = (await client.get("/api/candidates", params={"category": "news"})).json()
    assert [item["title"] for item in by_category["items"]] == ["B"]

    paged = (await client.get("/api/candidates", params={"page": 2, "page_size": 2})).json()
    assert [item["title"] for item in paged["items"]] == ["C"]

    candidate_id = page["items"][0]["id"]
    updated = await client.patch(f"/api/candidates/{candidate_id}/status", json={"status": "approved"})
    assert updated.json()["status"] == CandidateStatus.APPROVED

    stats = (await client.get("/api/stats")).json()
    assert stats["approved"] == 1
    assert stats["candidates_today"] == 3
    assert stats["average_score"] == 65.0

    assert (await client.get("/api/candidates/99999")).status_code == 404


async def test_classify_endpoint_uses_provider(
    client: httpx.AsyncClient, session: AsyncSession, source: Source
) -> None:
    candidate = Candidate(source_id=source.id, external_url="https://e.com/x", title="X")
    session.add(candidate)
    await session.commit()

    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_provider] = lambda: FakeProvider()

    response = await client.post(f"/api/candidates/{candidate.id}/classify")
    assert response.status_code == 200
    assert response.json()["total_score"] == 79

    batch = (await client.post("/api/candidates/classify-pending")).json()
    assert batch == {"processed": 0, "classified": 0, "errors": 0}
