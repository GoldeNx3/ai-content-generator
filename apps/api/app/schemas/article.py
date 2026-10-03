# Rola pliku: Schematy danych article: Pydantic waliduje dane wejścia/wyjścia; te klasy nie tworzą tabel SQL.

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ArticleStatus, CandidateCategory

# ---------- LLM structured output ----------


class ArticleBrief(BaseModel):
    article_type: CandidateCategory
    primary_angle: str
    target_audience: str
    suggested_title: str
    key_points: list[str]
    # Field dodaje walidację Pydantic: ge/le to granice liczb, a default/default_factory określają
    # wartość domyślną.
    required_facts: list[int] = Field(description="ID faktów (FACT #id), które muszą znaleźć się w tekście")
    optional_facts: list[int] = Field(description="ID faktów, które można wykorzystać")
    uncertainties_to_avoid: list[str]
    conflicts_to_mention: list[str]
    desired_length_words: int = Field(ge=100, le=4000)


class WriterSection(BaseModel):
    heading: str
    content: str = Field(description="Treść sekcji w Markdown, bez nagłówka")
    used_fact_ids: list[int]
    source_ids: list[int]


class WriterOutput(BaseModel):
    title: str
    slug: str
    lead: str
    lead_fact_ids: list[int]
    sections: list[WriterSection]
    conclusion: str
    conclusion_fact_ids: list[int]
    meta_title: str
    meta_description: str


# ---------- API ----------


class ArticleLength(StrEnum):
    AUTO = "auto"
    SHORT = "short"
    STANDARD = "standard"
    LONG = "long"


class GenerateArticleRequest(BaseModel):
    article_type: CandidateCategory | None = Field(
        default=None, description="Default: candidate category, else news"
    )
    length: ArticleLength = ArticleLength.AUTO
    angle: str | None = Field(default=None, max_length=1000, description="Empty = research suggestion")
    instructions: str | None = Field(default=None, max_length=2000)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    lead: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    meta_title: str | None = Field(default=None, min_length=1, max_length=300)
    meta_description: str | None = Field(default=None, min_length=1, max_length=500)


class ArticleStatusUpdate(BaseModel):
    status: ArticleStatus


class ArticleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    version: int
    is_current: bool
    status: ArticleStatus
    title: str
    article_type: CandidateCategory
    word_count: int
    is_edited: bool
    estimated_cost_usd: Decimal | None
    llm_model: str | None
    created_at: datetime
    updated_at: datetime


class ArticleRead(ArticleSummary):
    research_id: int | None
    slug: str
    lead: str
    content: str
    generated_content: str
    meta_title: str
    meta_description: str
    angle: str | None
    brief: dict[str, Any]
    sections: list[dict[str, Any]]
    lead_fact_ids: list[int]
    generation_options: dict[str, Any]
    research_snapshot: dict[str, Any]
    validation_warnings: list[str]
    sections_count: int
    facts_used_count: int
    facts_available_count: int
    source_count: int
    llm_input_tokens: int
    llm_output_tokens: int
    brief_llm_model: str | None
    brief_input_tokens: int
    brief_output_tokens: int
    brief_cost_usd: Decimal | None
    writer_input_tokens: int
    writer_output_tokens: int
    writer_cost_usd: Decimal | None
