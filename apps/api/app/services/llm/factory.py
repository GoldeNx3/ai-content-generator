# Rola pliku: Składa osobnego dostawcę dla każdego etapu.
# Fabryka to zwykła funkcja tworząca obiekt; serwis widzi kontrakt z base.py,
# dzięki czemu może też dostać innego dostawcę lub fake używany w testach.

from app.core.config import Settings, get_settings
from app.services.llm.base import ArticleLLMProvider, LLMProvider, ResearchLLMProvider
from app.services.llm.classify import OpenAIClassifier
from app.services.llm.client import OpenAIClient
from app.services.llm.research import OpenAIResearcher
from app.services.llm.write import OpenAIWriter


def _client(settings: Settings) -> OpenAIClient:
    return OpenAIClient(settings.openai_api_key, timeout=settings.llm_timeout_seconds)


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    return OpenAIClassifier(_client(settings), settings.openai_classifier_model)


def get_research_llm_provider() -> ResearchLLMProvider:
    settings = get_settings()
    return OpenAIResearcher(_client(settings), settings.research_model, settings.research_timeout_seconds)


def get_article_llm_provider() -> ArticleLLMProvider:
    settings = get_settings()
    return OpenAIWriter(
        _client(settings), settings.brief_model, settings.writer_model, settings.writer_timeout_seconds,
    )
