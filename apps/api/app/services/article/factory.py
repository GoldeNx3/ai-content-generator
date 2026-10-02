from app.schemas.article import ArticleBrief
from app.services.llm.base import (
    ArticleContext,
    ArticleLLMProvider,
    BriefResult,
    LLMNotConfiguredError,
    WriterResult,
)
from app.services.llm.factory import get_article_llm_provider


class UnconfiguredArticleLLM:
    """Lets non-LLM endpoints (edit, status, list) work without an API key."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        raise LLMNotConfiguredError(self.reason)

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        raise LLMNotConfiguredError(self.reason)


def article_llm_or_placeholder() -> ArticleLLMProvider:
    try:
        return get_article_llm_provider()
    except LLMNotConfiguredError as exc:
        return UnconfiguredArticleLLM(str(exc))
