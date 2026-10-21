# Rola pliku: Etap write — plan artykułu (brief), następnie jego tekst.
# To jeden etap redakcyjny z dwoma wywołaniami; każde może użyć innego modelu.

from app.schemas.article import ArticleBrief, WriterOutput
from app.services.llm.base import ArticleContext, BriefResult, WriterResult
from app.services.llm.client import OpenAIClient
from app.services.llm.writer_prompt import (
    BRIEF_SYSTEM_PROMPT, WRITER_SYSTEM_PROMPT, build_brief_prompt, build_writer_prompt,
)


class OpenAIWriter:
    """Dostawca spełniający kontrakt ArticleLLMProvider z base.py."""

    def __init__(
        self, client: OpenAIClient, brief_model: str, writer_model: str,
        timeout: float = 300.0,
    ) -> None:
        self.client = client
        self.brief_model = brief_model
        self.writer_model = writer_model
        self.timeout = timeout

    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        parsed, usage = await self.client.parse(
            self.brief_model, BRIEF_SYSTEM_PROMPT, build_brief_prompt(context), ArticleBrief
        )
        return BriefResult(brief=parsed, usage=usage)

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        parsed, usage = await self.client.parse(
            self.writer_model,
            WRITER_SYSTEM_PROMPT,
            build_writer_prompt(context, brief),
            WriterOutput,
            timeout=self.timeout,
        )
        return WriterResult(output=parsed, usage=usage)
