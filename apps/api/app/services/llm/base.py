from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.schemas.article import ArticleBrief, WriterOutput
from app.schemas.classification import CandidateClassification
from app.schemas.research import ResearchOutput, SearchQueries


class LLMError(Exception):
    """Raised when the LLM provider fails or returns unusable output."""


class LLMNotConfiguredError(LLMError):
    """Raised when the provider is missing required configuration (e.g. API key)."""


@dataclass(frozen=True, slots=True)
class CandidateInput:
    title: str
    summary: str | None
    source: str
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class LLMUsage:
    model: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class ResearchDocument:
    url: str
    title: str | None
    publisher: str | None
    source_type: str
    source_score: int
    published_at: datetime | None
    content: str


@dataclass(frozen=True, slots=True)
class QueriesResult:
    queries: SearchQueries
    usage: LLMUsage


@dataclass(frozen=True, slots=True)
class ResearchResult:
    output: ResearchOutput
    usage: LLMUsage


class LLMProvider(Protocol):
    async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification: ...


class ResearchLLMProvider(Protocol):
    async def generate_search_queries(self, candidate: CandidateInput) -> QueriesResult: ...

    async def research(
        self, candidate: CandidateInput, documents: list[ResearchDocument]
    ) -> ResearchResult: ...


# ---------- article writer ----------


@dataclass(frozen=True, slots=True)
class FactInput:
    id: int
    claim: str
    importance: str
    confidence: int
    source_ids: list[int]


@dataclass(frozen=True, slots=True)
class SourceInput:
    id: int
    publisher: str | None
    title: str | None
    url: str
    source_type: str
    source_score: int


@dataclass(frozen=True, slots=True)
class ArticleContext:
    """Everything the writer may use. Nothing outside this object is a valid source of facts."""

    candidate_title: str
    candidate_source: str
    published_at: datetime | None
    research_summary: str | None
    why_it_matters: str | None
    suggested_angle: str | None
    facts: list[FactInput]
    sources: list[SourceInput]
    uncertainties: list[dict[str, str]]
    conflicts: list[dict[str, object]]
    article_type: str
    type_guide: str
    length_hint: str
    angle: str | None
    instructions: str | None


@dataclass(frozen=True, slots=True)
class BriefResult:
    brief: ArticleBrief
    usage: LLMUsage


@dataclass(frozen=True, slots=True)
class WriterResult:
    output: WriterOutput
    usage: LLMUsage


class ArticleLLMProvider(Protocol):
    async def generate_brief(self, context: ArticleContext) -> BriefResult: ...

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult: ...
