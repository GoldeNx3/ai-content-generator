import logging
import time
from typing import TypeVar

import httpx
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.schemas.article import ArticleBrief, WriterOutput
from app.schemas.classification import CandidateClassification
from app.schemas.research import ResearchOutput, SearchQueries
from app.services.llm.base import (
    ArticleContext,
    BriefResult,
    CandidateInput,
    LLMError,
    LLMNotConfiguredError,
    LLMUsage,
    QueriesResult,
    ResearchDocument,
    ResearchResult,
    WriterResult,
)
from app.services.llm.prompt import CLASSIFIER_SYSTEM_PROMPT, build_user_prompt
from app.services.llm.research_prompt import (
    QUERY_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    build_query_prompt,
    build_research_prompt,
)
from app.services.llm.writer_prompt import (
    BRIEF_SYSTEM_PROMPT,
    WRITER_SYSTEM_PROMPT,
    build_brief_prompt,
    build_writer_prompt,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
        research_model: str | None = None,
        brief_model: str | None = None,
        writer_model: str | None = None,
        writer_timeout: float = 300.0,
        research_timeout: float = 300.0,
    ) -> None:
        if not api_key:
            raise LLMNotConfiguredError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(
            api_key=api_key, timeout=timeout, max_retries=2, http_client=http_client
        )
        self._model = model
        self._research_model = research_model or model
        self._brief_model = brief_model or self._research_model
        self._writer_model = writer_model or self._research_model
        self._writer_timeout = writer_timeout
        self._research_timeout = research_timeout

    async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification:
        parsed, _ = await self._parse(
            self._model, CLASSIFIER_SYSTEM_PROMPT, build_user_prompt(candidate), CandidateClassification
        )
        return parsed

    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult:
        parsed, usage = await self._parse(
            self._research_model, QUERY_SYSTEM_PROMPT, build_query_prompt(candidate), SearchQueries
        )
        return QueriesResult(queries=parsed, usage=usage)

    async def research(
        self, candidate: CandidateInput, documents: list[ResearchDocument]
    ) -> ResearchResult:
        parsed, usage = await self._parse(
            self._research_model,
            RESEARCH_SYSTEM_PROMPT,
            build_research_prompt(candidate, documents),
            ResearchOutput,
            timeout=self._research_timeout,
        )
        return ResearchResult(output=parsed, usage=usage)

    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        parsed, usage = await self._parse(
            self._brief_model, BRIEF_SYSTEM_PROMPT, build_brief_prompt(context), ArticleBrief
        )
        return BriefResult(brief=parsed, usage=usage)

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        parsed, usage = await self._parse(
            self._writer_model,
            WRITER_SYSTEM_PROMPT,
            build_writer_prompt(context, brief),
            WriterOutput,
            timeout=self._writer_timeout,
        )
        return WriterResult(output=parsed, usage=usage)

    async def _parse(
        self, model: str, system: str, user: str, text_format: type[T], timeout: float | None = None
    ) -> tuple[T, LLMUsage]:
        started = time.perf_counter()
        # Long calls: generous timeout and at most one retry - a timed-out generation restarted
        # from scratch only multiplies waiting time and cost.
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
        except ValueError as exc:  # pydantic validation of the structured output
            raise LLMError(f"Invalid structured output: {exc}") from exc

        usage = LLMUsage(
            model=response.model or model,
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
