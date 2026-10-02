from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from fastapi import APIRouter, HTTPException, status

from app.api.deps import ArticleServiceDep
from app.models import Article
from app.schemas.article import (
    ArticleRead,
    ArticleStatusUpdate,
    ArticleSummary,
    ArticleUpdate,
    GenerateArticleRequest,
)
from app.services.article.article_service import (
    ArticleError,
    ArticleNotFoundError,
    CandidateNotFoundError,
    ResearchNotReadyError,
)
from app.services.llm.base import LLMError, LLMNotConfiguredError

router = APIRouter(tags=["articles"])

T = TypeVar("T")

_ERROR_STATUS: dict[type[Exception], int] = {
    CandidateNotFoundError: status.HTTP_404_NOT_FOUND,
    ArticleNotFoundError: status.HTTP_404_NOT_FOUND,
    ResearchNotReadyError: status.HTTP_409_CONFLICT,
    LLMNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
    LLMError: status.HTTP_502_BAD_GATEWAY,
}


async def _call(fn: Callable[[], Awaitable[T]]) -> T:
    try:
        return await fn()
    except (ArticleError, LLMError) as exc:
        code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        raise HTTPException(code, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/article", response_model=ArticleRead, status_code=status.HTTP_201_CREATED
)
async def generate_article(
    candidate_id: int, service: ArticleServiceDep, payload: GenerateArticleRequest | None = None
) -> Article:
    """Brief + writer (synchronous, ~20-90 s). Requires a completed research. Creates a new version."""
    return await _call(lambda: service.generate(candidate_id, payload or GenerateArticleRequest()))


@router.get("/candidates/{candidate_id}/articles", response_model=list[ArticleSummary])
async def list_article_versions(candidate_id: int, service: ArticleServiceDep) -> Sequence[Article]:
    return await _call(lambda: service.list_versions(candidate_id))


@router.get("/articles/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, service: ArticleServiceDep) -> Article:
    return await _call(lambda: service.get(article_id))


@router.post("/articles/{article_id}/regenerate", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
async def regenerate_article(
    article_id: int, service: ArticleServiceDep, payload: GenerateArticleRequest | None = None
) -> Article:
    """New version; options not given in the body are taken from this version."""
    return await _call(lambda: service.regenerate(article_id, payload))


@router.patch("/articles/{article_id}", response_model=ArticleRead)
async def update_article(article_id: int, payload: ArticleUpdate, service: ArticleServiceDep) -> Article:
    return await _call(lambda: service.update(article_id, payload))


@router.patch("/articles/{article_id}/status", response_model=ArticleRead)
async def update_article_status(
    article_id: int, payload: ArticleStatusUpdate, service: ArticleServiceDep
) -> Article:
    return await _call(lambda: service.set_status(article_id, payload.status))
