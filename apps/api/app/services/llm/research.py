# Rola pliku: Etap research — zapytania wyszukiwania i analiza źródeł.
# Wynik zawiera raport oraz tokeny, aby backend mógł zapisać koszty.

from app.schemas.research import ResearchOutput, SearchQueries
from app.services.llm.base import CandidateInput, QueriesResult, ResearchDocument, ResearchResult
from app.services.llm.client import OpenAIClient
from app.services.llm.research_prompt import (
    QUERY_SYSTEM_PROMPT, RESEARCH_SYSTEM_PROMPT, build_query_prompt, build_research_prompt,
)


class OpenAIResearcher:
    """Dostawca spełniający kontrakt ResearchLLMProvider z base.py."""

    def __init__(self, client: OpenAIClient, model: str, timeout: float = 300.0) -> None:
        self.client = client
        self.model = model
        self.timeout = timeout

    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult:
        parsed, usage = await self.client.parse(
            self.model, QUERY_SYSTEM_PROMPT, build_query_prompt(candidate), SearchQueries
        )
        return QueriesResult(queries=parsed, usage=usage)

    async def research(
        self, candidate: CandidateInput, documents: list[ResearchDocument]
    ) -> ResearchResult:
        parsed, usage = await self.client.parse(
            self.model,
            RESEARCH_SYSTEM_PROMPT,
            build_research_prompt(candidate, documents),
            ResearchOutput,
            timeout=self.timeout,
        )
        return ResearchResult(output=parsed, usage=usage)
