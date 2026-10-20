# Rola pliku: Wspólne fixtures pytest: przygotowują bazę testową, sesję, źródło RSS i klienta API. Pytest
# odkrywa ten plik automatycznie.

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import Base, get_session, get_session_factory
from app.main import create_app
from app.api.deps import get_current_user
from app.models import Source
from app.models.enums import WorkspaceRole
from app.services.auth.service import CurrentUser


# Fixture odtwarza tabele w test_database_url; dlatego musi wskazywać wydzieloną bazę testową.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
# Fixture przygotowuje zależność testu; pytest przekazuje ją według nazwy argumentu funkcji testowej.
@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    test_engine = create_async_engine(get_settings().test_database_url)
    async with test_engine.begin() as connection:
        # Testowa baza jest odtwarzana także przy dodaniu cyklicznych FK.
        # drop_all nie potrafi usunąć nowej nazwanej FK ze starego schematu.
        assert get_settings().test_database_url != get_settings().database_url
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


# Przed testem czyścimy dane; fabryka pozwala otwierać osobne sesje także dla zadań w tle.
@pytest.fixture
async def session_factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE auth_attempts, user_sessions, workspace_members, workspaces, users, job_batches, research_fact_sources, research_facts, research_sources, researches, candidates, sources RESTART IDENTITY CASCADE"))
        # Workspace 1 = TEST_USER (fixture client), 2 = obcy workspace do testów izolacji.
        await connection.execute(text("INSERT INTO workspaces (id, name) VALUES (1, 'test'), (2, 'obcy')"))
        await connection.execute(text("SELECT setval('workspaces_id_seq', 2)"))
    yield async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as db_session:
        yield db_session


@pytest.fixture
async def source(session: AsyncSession) -> Source:
    item = Source(workspace_id=1, name="Test Feed", url="https://example.com/feed.xml")
    session.add(item)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    return item


# Overrides zastępują produkcyjne zależności bazy; ASGITransport wywołuje API lokalnie w procesie testu.
TEST_USER = CurrentUser(user_id=1, email="test@example.com", workspace_id=1, workspace_name="test",
                        role=WorkspaceRole.OWNER)


# client działa jako zalogowany użytkownik (nadpisana zależność sesji), więc testy zasobów nie muszą się
# logować; anon_client sprawdza prawdziwe uwierzytelnianie przez ciasteczko.
@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    async for test_client in _client(session_factory, authenticated=True):
        yield test_client


@pytest.fixture
async def anon_client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    async for test_client in _client(session_factory, authenticated=False):
        yield test_client


async def _client(session_factory, *, authenticated: bool) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"openai_api_key": "sk-test"})

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
async def execute_job(session_factory):
    # Test uruchamia ten sam worker co kontener, ale podmienia wyłącznie
    # zewnętrznych dostawców. Nie ma LLM wewnątrz requestu API.
    from app.workers.worker import Worker
    async def execute(providers):
        return await Worker(session_factory, providers=providers).run_once()
    return execute
