# Rola pliku: Testy modułu research_api: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_content_extractor, get_research_llm, get_search
from app.models import Candidate, Source
from tests.research_fakes import FakeResearchLLM, FakeSearch, extractor_for, html_response

ORIGINAL = "https://openai.com/index/gpt-6-api"
MANUAL = "https://techcrunch.com/gpt-6"


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_research_endpoints(client: httpx.AsyncClient, session: AsyncSession, execute_job) -> None:
    source = Source(workspace_id=1, name="OpenAI", url="https://openai.com/news/rss.xml")
    session.add(source)
    # flush wysyła zmiany do bazy (np. nadaje ID), ale nie zatwierdza jeszcze transakcji jak commit.
    await session.flush()
    candidate = Candidate(workspace_id=1, source_id=source.id, external_url=ORIGINAL, title="GPT-6 API")
    session.add(candidate)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()

    app = client._transport.app  # type: ignore[attr-defined]
    pages = {ORIGINAL: html_response("GPT-6"), MANUAL: html_response("TechCrunch on GPT-6")}
    app.dependency_overrides[get_content_extractor] = lambda: extractor_for(pages)
    app.dependency_overrides[get_search] = lambda: FakeSearch()
    app.dependency_overrides[get_research_llm] = lambda: FakeResearchLLM()
    base = f"/api/candidates/{candidate.id}/research"

    assert (await client.get(base)).status_code == 404
    assert (await client.post(f"{base}/retry")).status_code == 404

    started = await client.post(base)
    assert started.status_code == 202
    assert started.json()["status"] == "queued"
    assert (await client.get(base)).status_code == 404
    await execute_job({'research': FakeResearchLLM(), 'search': FakeSearch(), 'extractor': extractor_for(pages)})

    # Dopiero osobny worker tworzy raport, niezależnie od zamkniętego requestu API.
    report = (await client.get(base)).json()
    assert report["status"] == "completed"
    assert report["facts"][0]["source_ids"] == [report["sources"][0]["id"]]
    assert "raw_content" not in report["sources"][0]
    assert report["sources"][0]["extracted_content"]

    added = await client.post(f"{base}/sources", json={"url": MANUAL})
    assert added.status_code == 201
    assert added.json()["origin"] == "manual"
    assert (await client.post(f"{base}/sources", json={"url": MANUAL})).status_code == 409
    assert (await client.post(f"{base}/sources", json={"url": "not a url"})).status_code == 422

    retried = await client.post(f"{base}/retry")
    assert retried.status_code == 202
    await execute_job({'research': FakeResearchLLM(), 'search': FakeSearch(), 'extractor': extractor_for(pages)})
    report = (await client.get(base)).json()
    assert report["status"] == "completed"
    assert len(report["sources"]) == 2

    assert (await client.post("/api/candidates/99999/research")).status_code == 404
