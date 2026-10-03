# Rola pliku: Wybiera i konfiguruje dostawcę LLM dla klasyfikacji, researchu i artykułów.

from app.core.config import get_settings
from app.services.llm.base import ArticleLLMProvider, LLMProvider, ResearchLLMProvider
from app.services.llm.openai_provider import OpenAIProvider


def _openai_provider() -> OpenAIProvider:
    settings = get_settings()
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_classifier_model,
        research_model=settings.research_model,
        brief_model=settings.brief_model,
        writer_model=settings.writer_model,
        writer_timeout=settings.writer_timeout_seconds,
        research_timeout=settings.research_timeout_seconds,
        timeout=settings.llm_timeout_seconds,
    )


def get_llm_provider() -> LLMProvider:
    return _openai_provider()


def get_research_llm_provider() -> ResearchLLMProvider:
    return _openai_provider()


def get_article_llm_provider() -> ArticleLLMProvider:
    return _openai_provider()
