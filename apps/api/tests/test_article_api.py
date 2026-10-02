import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_article_llm
from tests.article_fakes import FakeArticleLLM, research_fixture


async def test_article_endpoints(client: httpx.AsyncClient, session: AsyncSession) -> None:
    candidate, _ = await research_fixture(session)
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_article_llm] = lambda: FakeArticleLLM()

    created = await client.post(f"/api/candidates/{candidate.id}/article", json={"article_type": "news"})
    assert created.status_code == 201
    article = created.json()
    assert article["version"] == 1 and article["status"] == "draft"
    assert article["facts_used_count"] == 2 and article["source_count"] == 2

    regenerated = await client.post(f"/api/articles/{article['id']}/regenerate")
    assert regenerated.status_code == 201
    versions = (await client.get(f"/api/candidates/{candidate.id}/articles")).json()
    assert [(v["version"], v["is_current"]) for v in versions] == [(2, True), (1, False)]

    patched = await client.patch(f"/api/articles/{article['id']}", json={"title": "Nowy tytuł"})
    assert patched.json()["title"] == "Nowy tytuł" and patched.json()["is_edited"]
    assert (await client.patch(f"/api/articles/{article['id']}", json={"title": ""})).status_code == 422

    status = await client.patch(f"/api/articles/{article['id']}/status", json={"status": "review"})
    assert status.json()["status"] == "review"
    assert (await client.get(f"/api/articles/{article['id']}")).json()["title"] == "Nowy tytuł"
    assert (await client.get("/api/articles/99999")).status_code == 404


async def test_generate_requires_completed_research(client: httpx.AsyncClient, session: AsyncSession) -> None:
    from app.models import ResearchStatus

    candidate, _ = await research_fixture(session, status=ResearchStatus.RUNNING)
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_article_llm] = lambda: FakeArticleLLM()

    response = await client.post(f"/api/candidates/{candidate.id}/article")
    assert response.status_code == 409
    assert response.json()["detail"] == "Complete research before generating an article."
