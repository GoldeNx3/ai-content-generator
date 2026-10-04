# Rola pliku: Endpointy HTTP zasobu articles: przekazują pracę serwisom/repozytoriom i wystawiają wyniki
# oraz błędy przez FastAPI.

from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import ArticleServiceDep, JobServiceDep
from app.api.jobs import IdempotencyKey, enqueue_call
from app.schemas.job import JobRead
from app.models import Article
from app.schemas.article import (
    ArticleRead,
    ArticleStatusUpdate,
    ArticleSummary,
    ArticleUpdate,
    GenerateArticleRequest,
)
from app.services.article.write import (
    ArticleError,
    ArticleNotFoundError,
    CandidateNotFoundError,
    ResearchNotReadyError,
)
from app.services.jobs.errors import JobInputError
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


# Wspólna granica API: wyjątki domenowe z serwisu są tłumaczone na odpowiedzi HTTP dla klienta.
# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def _call(fn: Callable[[], Awaitable[T]]) -> T:
    try:
        return await fn()
    except JobInputError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc
    except (ArticleError, LLMError) as exc:
        code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        raise HTTPException(code, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/article", response_model=JobRead, status_code=202)
async def generate_article(candidate_id: int, service: JobServiceDep, response: Response,
                           payload: GenerateArticleRequest | None = None, key: IdempotencyKey = None):
    options = (payload or GenerateArticleRequest()).model_dump(mode='json')
    return await enqueue_call(response, lambda: service.enqueue('write', candidate_id, options, key))


@router.get("/candidates/{candidate_id}/articles", response_model=list[ArticleSummary])
async def list_article_versions(candidate_id: int, service: ArticleServiceDep) -> Sequence[Article]:
    return await _call(lambda: service.list_versions(candidate_id))


@router.get("/articles/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, service: ArticleServiceDep) -> Article:
    return await _call(lambda: service.get(article_id))


@router.post("/articles/{article_id}/regenerate", response_model=JobRead, status_code=202)
async def regenerate_article(article_id: int, service: JobServiceDep, response: Response,
                             payload: GenerateArticleRequest | None = None, key: IdempotencyKey = None):
    return await enqueue_call(response, lambda: service.regenerate(article_id, payload, key))


@router.patch("/articles/{article_id}", response_model=ArticleRead)
async def update_article(article_id: int, payload: ArticleUpdate, service: ArticleServiceDep) -> Article:
    return await _call(lambda: service.update(article_id, payload))


@router.patch("/articles/{article_id}/status", response_model=ArticleRead)
async def update_article_status(
    article_id: int, payload: ArticleStatusUpdate, service: ArticleServiceDep
) -> Article:
    return await _call(lambda: service.set_status(article_id, payload.status))
