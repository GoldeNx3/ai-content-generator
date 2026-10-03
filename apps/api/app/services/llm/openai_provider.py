# Rola pliku: Zgodność ze starszym kodem używającym jednego OpenAIProvider.
# Właściwe implementacje są w classify.py, research.py i write.py.
# Delegowanie to przekazanie pracy mniejszym obiektom — bez dziedziczenia.

import httpx

from app.schemas.article import ArticleBrief
from app.schemas.classification import CandidateClassification
from app.services.llm.base import (
    ArticleContext, BriefResult, CandidateInput, QueriesResult,
    ResearchDocument, ResearchResult, WriterResult,
)
from app.services.llm.classify import OpenAIClassifier
from app.services.llm.client import OpenAIClient
from app.services.llm.research import OpenAIResearcher
from app.services.llm.write import OpenAIWriter


class OpenAIProvider:
    """Zachowuje dotychczasowy konstruktor i metody dla istniejących integracji."""

    def __init__(
        self, api_key: str, model: str, timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
        research_model: str | None = None, brief_model: str | None = None,
        writer_model: str | None = None, writer_timeout: float = 300.0,
        research_timeout: float = 300.0,
    ) -> None:
        client = OpenAIClient(api_key, timeout, http_client)
        research_model = research_model or model
        self.classifier = OpenAIClassifier(client, model)
        self.researcher = OpenAIResearcher(client, research_model, research_timeout)
        self.writer = OpenAIWriter(
            client, brief_model or research_model, writer_model or research_model, writer_timeout,
        )

    async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification:
        return await self.classifier.classify_candidate(candidate)

    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult:
        return await self.researcher.generate_search_queries(candidate)

    async def research(self, candidate: CandidateInput, documents: list[ResearchDocument]) -> ResearchResult:
        return await self.researcher.research(candidate, documents)

    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        return await self.writer.generate_brief(context)

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        return await self.writer.write_article(context, brief)
