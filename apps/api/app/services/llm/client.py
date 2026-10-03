# Rola pliku: Wspólny transport OpenAI: HTTP, błędy, parsowanie i tokeny.
# Nie zna kroków classify/research/write. Każdy krok przekazuje model, prompt
# i schemat odpowiedzi; tutaj odbywa się jedna operacja sieciowa.

import logging
import time
from typing import TypeVar

import httpx
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.services.llm.base import LLMError, LLMNotConfiguredError, LLMUsage

logger = logging.getLogger(__name__)
# T oznacza dowolny model Pydantic. Wynik parse ma ten sam typ, który
# przekazano jako text_format — np. ArticleBrief albo ResearchOutput.
T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    """Jedno miejsce na zasady komunikacji ze zewnętrznym API."""

    def __init__(
        self, api_key: str, timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise LLMNotConfiguredError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(
            api_key=api_key, timeout=timeout, max_retries=2, http_client=http_client,
        )

    # SDK parsuje odpowiedź do wskazanego modelu Pydantic; serwis dostaje typowane dane i informację o
    # tokenach.
    async def parse(
        self, model: str, system: str, user: str, text_format: type[T], timeout: float | None = None
    ) -> tuple[T, LLMUsage]:
        started = time.perf_counter()
        # Długie generacje mają osobny timeout i najwyżej jedną ponowną próbę.
        # Powtarzanie generacji od początku zwiększa czas oczekiwania i koszt.
        client = self._client.with_options(timeout=timeout, max_retries=1) if timeout else self._client
        try:
            response = await client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                text_format=text_format,
            )
        except OpenAIError as exc:
            logger.warning(
                "LLM call failed model=%s schema=%s duration=%.2fs error=%s",
                model, text_format.__name__, time.perf_counter() - started, exc.__class__.__name__,
            )
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        except ValueError as exc:  # walidacja structured output przez Pydantic
            raise LLMError(f"Invalid structured output: {exc}") from exc

        usage = LLMUsage(
            model=response.model or model,
            recorded=response.usage is not None,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
        )
        logger.info(
            "LLM call model=%s schema=%s duration=%.2fs input_tokens=%d output_tokens=%d",
            usage.model, text_format.__name__, time.perf_counter() - started,
            usage.input_tokens, usage.output_tokens,
        )
        if response.output_parsed is None:
            raise LLMError("OpenAI returned no parsed output (refusal or empty response)")
        return response.output_parsed, usage
