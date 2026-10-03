# Rola pliku: Dostarcza LLM artykułów lub placeholder zgłaszający brak klucza przy próbie generacji.

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

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, reason: str) -> None:
        self.reason = reason

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        raise LLMNotConfiguredError(self.reason)

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        raise LLMNotConfiguredError(self.reason)


def article_llm_or_placeholder() -> ArticleLLMProvider:
    try:
        return get_article_llm_provider()
    except LLMNotConfiguredError as exc:
        return UnconfiguredArticleLLM(str(exc))
