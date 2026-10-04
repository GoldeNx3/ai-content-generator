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
from app.models import Source


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
        await connection.execute(text("TRUNCATE job_batches, research_fact_sources, research_facts, research_sources, researches, candidates, sources RESTART IDENTITY CASCADE"))
    yield async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as db_session:
        yield db_session


@pytest.fixture
async def source(session: AsyncSession) -> Source:
    item = Source(name="Test Feed", url="https://example.com/feed.xml")
    session.add(item)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    return item


# Overrides zastępują produkcyjne zależności bazy; ASGITransport wywołuje API lokalnie w procesie testu.
@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
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
