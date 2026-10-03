# Rola pliku: Konfiguracja aplikacji: Pydantic odczytuje zmienne środowiskowe i .env, sprawdza typy oraz
# stosuje wartości domyślne.

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CLASSIFIER_MODEL = "gpt-4.1-mini"

# USD per 1M tokens. Override with LLM_PRICING (JSON) in .env - keep in sync with provider pricing.
DEFAULT_LLM_PRICING: dict[str, dict[str, float]] = {
    "gpt-6.1-sol": {"input": 2.00, "cached_input": 0.10, "output": 10.00, "long_context_threshold": 272000, "long_input": 4.00, "long_output": 15.00, "long_cached_input": 0.20},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5": {"input": 1.25, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://content:content@localhost:5432/content"
    test_database_url: str = "postgresql+psycopg://content:content@localhost:5432/content_test"

    openai_api_key: str = ""
    openai_classifier_model: str = ""
    # Empty = same model as the classifier.
    openai_research_model: str = ""
    # Article writer: brief can use a cheaper model than the writer. Empty = research model.
    openai_brief_model: str = ""
    openai_writer_model: str = ""
    writer_timeout_seconds: float = 300.0
    llm_pricing: dict[str, dict[str, float]] = DEFAULT_LLM_PRICING
    llm_timeout_seconds: float = 60.0
    # Long generations (research analysis, article writing) on large/reasoning models can take minutes.
    research_timeout_seconds: float = 300.0

    cors_origins: str = "http://localhost:3000"

    http_timeout_seconds: float = 15.0
    fetch_interval_minutes: int = 30
    # Entries published earlier than this are skipped (0 = no limit). Entries without a date are kept.
    fetch_max_age_days: int = 14
    # Max candidates classified by one classify-pending call (protects LLM budget).
    classify_batch_limit: int = 50

    # Research engine
    search_provider: str = "manual"  # manual | tavily
    tavily_api_key: str = ""
    page_fetch_timeout_seconds: float = 20.0
    page_max_bytes: int = 5_000_000
    raw_content_max_chars: int = 300_000
    research_max_extra_sources: int = 5
    research_max_chars_per_source: int = 12_000
    research_max_chars_original: int = 20_000
    research_max_total_chars: int = 60_000
    # Hard cap on stored facts (most important first) - protects writer prompt size and UI.
    research_max_facts: int = 60

    @field_validator("openai_classifier_model")
    @classmethod
    def default_model(cls, value: str) -> str:
        return value.strip() or DEFAULT_CLASSIFIER_MODEL

    # property pozwala odczytywać wynik metody jak pole: obj.nazwa zamiast obj.nazwa().
    @property
    def research_model(self) -> str:
        return self.openai_research_model.strip() or self.openai_classifier_model

    @property
    def brief_model(self) -> str:
        return self.openai_brief_model.strip() or self.research_model

    @property
    def writer_model(self) -> str:
        return self.openai_writer_model.strip() or self.research_model

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# lru_cache zachowuje wynik wywołania; konfiguracja jest współdzielona, zamiast czytana od nowa przy
# każdym żądaniu.
@lru_cache
def get_settings() -> Settings:
    return Settings()
