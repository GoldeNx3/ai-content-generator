# Rola pliku: Testy modułu article_api: scenariusze poprawnego działania i błędów. Funkcje test_* odkrywa
# i uruchamia pytest.

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_article_llm
from tests.article_fakes import FakeArticleLLM, research_fixture


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_article_endpoints(client: httpx.AsyncClient, session: AsyncSession, execute_job) -> None:
    candidate, _ = await research_fixture(session)
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_article_llm] = lambda: FakeArticleLLM()

    created = await client.post(f"/api/candidates/{candidate.id}/article", json={"article_type": "news"})
    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert (await client.get(f"/api/candidates/{candidate.id}/articles")).json() == []
    await execute_job({'write': FakeArticleLLM()})
    finished = (await client.get(f"/api/jobs/{created.json()['id']}")).json()
    assert finished['status'] == 'succeeded'
    article = (await client.get(f"/api/articles/{finished['result_id']}")).json()
    assert article["version"] == 1 and article["status"] == "draft"
    assert article["facts_used_count"] == 2 and article["source_count"] == 2

    regenerated = await client.post(f"/api/articles/{article['id']}/regenerate")
    assert regenerated.status_code == 202
    await execute_job({'write': FakeArticleLLM()})
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


async def test_queue_preserves_format_and_angle_on_partial_regeneration(client, session, execute_job):
    candidate, _ = await research_fixture(session)
    options = {'article_format': 'case_study', 'angle': 'Dlaczego zmiana była trudna?', 'length': 'short'}
    created = await client.post(f'/api/candidates/{candidate.id}/article', json=options)
    assert created.status_code == 202
    await execute_job({'write': FakeArticleLLM()})
    job = (await client.get(f"/api/jobs/{created.json()['id']}")).json()
    article = (await client.get(f"/api/articles/{job['result_id']}")).json()
    assert article['article_format'] == 'case_study'
    assert article['angle'] == options['angle']
    retried = await client.post(f"/api/articles/{article['id']}/regenerate", json={'length': 'long'})
    assert retried.status_code == 202
    await execute_job({'write': FakeArticleLLM()})
    job = (await client.get(f"/api/jobs/{retried.json()['id']}")).json()
    version = (await client.get(f"/api/articles/{job['result_id']}")).json()
    assert version['article_format'] == 'case_study'
    assert version['angle'] == options['angle']
    assert version['generation_options']['length'] == 'long'
    versions = (await client.get(f'/api/candidates/{candidate.id}/articles')).json()
    assert [item['article_format'] for item in versions] == ['case_study', 'case_study']
