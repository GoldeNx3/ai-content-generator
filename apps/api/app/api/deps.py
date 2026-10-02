from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import get_session, get_session_factory
from app.services.ingestion_service import IngestionService
from app.services.article.article_service import ArticleService
from app.services.article.factory import article_llm_or_placeholder
from app.services.llm.base import ArticleLLMProvider, LLMNotConfiguredError, LLMProvider, ResearchLLMProvider
from app.services.llm.cost import LLMCostCalculator
from app.services.llm.factory import get_llm_provider
from app.services.research.content_extractor import ContentExtractor
from app.services.research.factory import (
    ResearchRunner,
    build_content_extractor,
    build_research_service,
    make_research_runner,
    research_llm_or_placeholder,
)
from app.services.research.research_service import ResearchService
from app.services.research.search import SearchProvider, get_search_provider
from app.services.rss_fetcher import RssFetcher

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_rss_fetcher() -> RssFetcher:
    return RssFetcher(timeout=get_settings().http_timeout_seconds)


def get_ingestion_service(
    session: SessionDep, fetcher: Annotated[RssFetcher, Depends(get_rss_fetcher)]
) -> IngestionService:
    return IngestionService(session, fetcher, max_age_days=get_settings().fetch_max_age_days)


def get_provider() -> LLMProvider:
    try:
        return get_llm_provider()
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


IngestionDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ProviderDep = Annotated[LLMProvider, Depends(get_provider)]


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_content_extractor(settings: SettingsDep) -> ContentExtractor:
    return build_content_extractor(settings)


def get_search(settings: SettingsDep) -> SearchProvider:
    return get_search_provider(settings)


def get_research_llm() -> ResearchLLMProvider:
    return research_llm_or_placeholder()


ExtractorDep = Annotated[ContentExtractor, Depends(get_content_extractor)]
SearchDep = Annotated[SearchProvider, Depends(get_search)]
ResearchLLMDep = Annotated[ResearchLLMProvider, Depends(get_research_llm)]


def get_research_service(
    session: SessionDep, settings: SettingsDep, extractor: ExtractorDep, search: SearchDep, llm: ResearchLLMDep
) -> ResearchService:
    return build_research_service(session, settings, extractor, search, llm)


def get_research_runner(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    settings: SettingsDep,
    extractor: ExtractorDep,
    search: SearchDep,
    llm: ResearchLLMDep,
) -> ResearchRunner:
    return make_research_runner(session_factory, settings, extractor, search, llm)


ResearchServiceDep = Annotated[ResearchService, Depends(get_research_service)]
ResearchRunnerDep = Annotated[ResearchRunner, Depends(get_research_runner)]


def get_article_llm() -> ArticleLLMProvider:
    return article_llm_or_placeholder()


def get_article_service(
    session: SessionDep, settings: SettingsDep, llm: Annotated[ArticleLLMProvider, Depends(get_article_llm)]
) -> ArticleService:
    return ArticleService(session, llm, LLMCostCalculator(settings.llm_pricing))


ArticleServiceDep = Annotated[ArticleService, Depends(get_article_service)]
