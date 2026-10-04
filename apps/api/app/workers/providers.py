# Rola pliku: Dostawcy workera z wyłączonym retry SDK.
# Kolejka sama zarządza próbami; klucze pobieramy wyłącznie ze środowiska.

from app.core.config import Settings, get_settings
from app.services.llm.classify import OpenAIClassifier
from app.services.llm.client import OpenAIClient
from app.services.llm.research import OpenAIResearcher
from app.services.llm.write import OpenAIWriter
from app.services.llm.qa import OpenAIQA
from app.services.llm.auto_fix import OpenAIAutoFix


def settings_for(job):
    environment = get_settings()
    return Settings(**{**environment.model_dump(), **job.payload['settings']})


def providers_for(settings):
    client = OpenAIClient(settings.openai_api_key, settings.llm_timeout_seconds, max_retries=0)
    return {
        'classify': OpenAIClassifier(client, settings.openai_classifier_model),
        'research': OpenAIResearcher(client, settings.research_model, settings.research_timeout_seconds),
        'auto_fix_article': OpenAIAutoFix(client, settings.auto_fix_model, settings.auto_fix_timeout_seconds),
        'qa_article': OpenAIQA(client, settings.qa_model, settings.qa_timeout_seconds),
        'write': OpenAIWriter(client, settings.brief_model, settings.writer_model, settings.writer_timeout_seconds),
        '_client': client,
    }
