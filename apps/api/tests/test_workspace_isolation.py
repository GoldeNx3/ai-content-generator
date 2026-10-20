# Rola pliku: Testy izolacji danych między workspace'ami: każda chroniona trasa z ID w ścieżce zwraca 404
# dla zasobu obcego workspace'u i niczego nie zapisuje, listy/agregaty widzą tylko własne dane, a złożone
# FK nie pozwalają rozjechać workspace'u kandydata, źródła i joba.

import re

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.access import OWNERSHIP
from app.jobs.seed_demo import seed_demo
from app.main import create_app
from app.models import Article, ArticleFix, Candidate, Source
from app.models.job import Job
from app.services.ingestion_service import IngestionService
from tests.test_ingestion import make_fetcher

OWN, FOREIGN = 1, 2  # TEST_USER należy do workspace'u 1 (conftest)
PARAM = re.compile(r"{(\w+)}")


def protected_routes():
    for route in create_app().routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/") and not path.startswith("/api/auth"):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield method, path


ID_ROUTES = [(method, path) for method, path in protected_routes() if PARAM.search(path)]


def test_every_path_parameter_is_covered_by_ownership_check():
    # Nowa trasa z nieobsłużonym ID w ścieżce ominęłaby enforce_workspace: dopisz ją do OWNERSHIP.
    missing = {(path, name) for _, path in ID_ROUTES for name in PARAM.findall(path) if name not in OWNERSHIP}
    assert not missing, missing
    assert len(ID_ROUTES) > 20


@pytest.fixture
async def foreign(session):
    # Pełne łańcuchy (źródło, kandydaci, research, wersje, QA, fixy, joby) w obcym workspace'ie.
    await seed_demo(session, FOREIGN)
    article = await session.scalar(select(Article).join(Candidate).where(Candidate.workspace_id == FOREIGN).limit(1))
    fix = await session.scalar(select(ArticleFix).join(Article, ArticleFix.source_article_version_id == Article.id)
                               .join(Candidate).where(Candidate.workspace_id == FOREIGN).limit(1))
    ids = {
        "candidate_id": article.candidate_id,
        "source_id": await session.scalar(select(Source.id).where(Source.workspace_id == FOREIGN)),
        "article_id": article.id,
        "version_id": article.id,
        "fix_id": fix.id,
        "job_id": await session.scalar(select(Job.id).where(Job.workspace_id == FOREIGN).limit(1)),
    }
    assert all(ids.values()), ids
    return ids


async def _row_counts(session):
    return [await session.scalar(select(func.count()).select_from(model)) for model in (Job, Article, Source, Candidate)]


@pytest.mark.parametrize(("method", "path"), ID_ROUTES, ids=[f"{m} {p}" for m, p in ID_ROUTES])
async def test_foreign_resource_is_not_found_and_unchanged(client, session, foreign, method, path):
    before = await _row_counts(session)
    url = PARAM.sub(lambda match: str(foreign[match.group(1)]), path)
    response = await client.request(method, url, json={} if method in {"POST", "PATCH", "PUT"} else None)
    assert response.status_code == 404, (url, response.status_code, response.text)
    assert response.json()["detail"] == {"code": "not_found"}
    session.expire_all()
    assert await _row_counts(session) == before


async def test_lists_and_aggregates_show_only_own_workspace(client, session, source, foreign):
    sources = (await client.get("/api/sources")).json()
    assert [item["id"] for item in sources] == [source.id]
    assert (await client.get("/api/candidates")).json()["total"] == 0
    assert (await client.get("/api/jobs", params={"status": "all"})).json()["total"] == 0
    assert (await client.get("/api/jobs/stats")).json()["total"] == 0
    stats = (await client.get("/api/stats")).json()
    assert stats["candidates_today"] == 0 and stats["approved"] == 0
    # Kandydaci obcego workspace'u bez oceny nie mogą trafić do partii klasyfikacji.
    batch = (await client.post("/api/candidates/classify-pending")).json()
    assert batch["enqueued"] == 0 and batch["job_ids"] == []


async def test_fetch_all_active_only_touches_given_workspace(session, source):
    other = Source(workspace_id=FOREIGN, name="Obcy", url="https://example.com/atom.xml")
    session.add(other)
    await session.commit()
    result = await IngestionService(session, make_fetcher()).fetch_all_active(workspace_id=OWN)
    assert result.sources_processed == 1
    owners = set((await session.scalars(select(Candidate.workspace_id))).all())
    assert owners == {OWN}


async def test_same_urls_allowed_in_different_workspaces(client, session, source):
    other = Source(workspace_id=FOREIGN, name="Ten sam feed", url=source.url)
    session.add(other)
    await session.commit()
    for owner, feed in ((OWN, source), (FOREIGN, other)):
        await IngestionService(session, make_fetcher()).fetch_source(feed)
    urls = {ws: set((await session.scalars(select(Candidate.external_url).where(Candidate.workspace_id == ws))).all())
            for ws in (OWN, FOREIGN)}
    assert urls[OWN] and urls[OWN] == urls[FOREIGN]
    # Duplikat URL źródła w obrębie własnego workspace'u nadal jest odrzucany.
    assert (await client.post("/api/sources", json={"name": "Dup", "url": source.url})).status_code == 409


async def test_composite_keys_reject_mismatched_workspace(session, session_factory, source):
    async with session_factory() as db:
        db.add(Candidate(workspace_id=FOREIGN, source_id=source.id, external_url="https://x.example/a", title="X"))
        with pytest.raises(IntegrityError):
            await db.commit()
    candidate = Candidate(workspace_id=OWN, source_id=source.id, external_url="https://x.example/b", title="Y")
    session.add(candidate)
    await session.commit()
    async with session_factory() as db:
        db.add(Job(workspace_id=FOREIGN, candidate_id=candidate.id, kind="classify", payload={}, request_hash="x"))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_batch_key_from_another_workspace_is_conflict(session, source):
    from uuid import uuid4

    from app.core.config import Settings
    from app.services.jobs.errors import JobConflict
    from app.services.jobs.service import JobService

    service = JobService(session, Settings(openai_api_key="test"))
    key = uuid4()
    await service.batch(1, key, workspace_id=OWN)
    with pytest.raises(JobConflict):
        await service.batch(1, key, workspace_id=FOREIGN)
