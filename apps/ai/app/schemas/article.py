# Rola pliku: Schematy danych article: Pydantic waliduje dane wejścia/wyjścia; te klasy nie tworzą tabel SQL.

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums import ArticleStatus, CandidateCategory

# ---------- LLM structured output ----------


class ArticleFormat(StrEnum):
    NEWS = "news"
    EXPLAINER = "explainer"
    CASE_STUDY = "case_study"
    GUIDE = "guide"
    COMPARISON = "comparison"


class BriefSection(BaseModel):
    heading: str
    purpose: str = Field(description="Pytanie sekcji i konkretne wyjaśnienie, przykład lub porównanie")
    fact_ids: list[int]
    target_words: int = Field(gt=0, le=4000)
    presentation: Literal["prose", "table", "code", "steps", "mixed"] = "prose"


class ArticleBrief(BaseModel):
    article_type: CandidateCategory
    article_format: ArticleFormat = ArticleFormat.NEWS
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
    desired_length_words: int = Field(gt=0, le=4000)
    section_plan: list[BriefSection] = Field(default_factory=list)
    research_gaps: list[str] = Field(default_factory=list,
        description="Konkretne braki dowodów uniemożliwiające pogłębione opracowanie")


class WriterSection(BaseModel):
    heading: str
    content: str = Field(description="Treść sekcji w Markdown, bez powtarzania jej H2; dopuszczalne konkretne H3 dla podtematów")
    used_fact_ids: list[int]
    source_ids: list[int]


from app.schemas.wordpress import SEOData


class WriterSEOData(SEOData):
    excerpt: str = Field(default='', min_length=1)
    focus_keyword: str = Field(default='', min_length=1)
    secondary_keywords: list[str] = Field(default_factory=list, min_length=1)
    tags: list[str] = Field(default_factory=list, min_length=3, max_length=8)
    category: Literal['AI','Modele AI','Programowanie','Narzędzia AI','Automatyzacja','Biznes','Newsy','Poradniki','Porównania'] = 'AI'
    og_title: str = Field(default='', min_length=1)
    og_description: str = Field(default='', min_length=1)
    twitter_title: str = Field(default='', min_length=1)
    twitter_description: str = Field(default='', min_length=1)

    @field_validator('excerpt','focus_keyword','og_title','og_description','twitter_title','twitter_description', mode='before')
    @classmethod
    def nonblank(cls,value):
        return value.strip() if isinstance(value,str) else value

    @field_validator('tags','secondary_keywords', mode='before')
    @classmethod
    def distinct_terms(cls,value):
        if not isinstance(value,list):return value
        terms=[];seen=set()
        for term in value:
            if not isinstance(term,str):return value
            term=term.strip()
            if term and term.casefold() not in seen:terms.append(term);seen.add(term.casefold())
        return terms


class WriterOutput(BaseModel):
    title: str
    slug: str
    lead: str
    lead_fact_ids: list[int]
    sections: list[WriterSection]
    conclusion: str
    conclusion_fact_ids: list[int]
    seo_data: WriterSEOData = Field(default_factory=WriterSEOData)

    @field_validator("seo_data", mode="before")
    @classmethod
    def seo_model(cls,value):
        return value.model_dump() if isinstance(value,BaseModel) else value
    meta_title: str
    meta_description: str


# ---------- API ----------


class ArticleLength(StrEnum):
    AUTO = "auto"
    SHORT = "short"
    STANDARD = "standard"
    LONG = "long"


class GenerateArticleRequest(BaseModel):
    # None supports saved legacy requests; new clients explicitly send auto.
    article_format: ArticleFormat | Literal["auto"] | None = None
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
    article_format: ArticleFormat
    word_count: int
    parent_version_id: int | None
    created_by: str
    creation_reason: str | None
    content_hash: str
    auto_fix_iterations_remaining: int = 0
    auto_fix_iteration: int
    approved_at: datetime | None
    approved_by: str | None
    rejection_reason: str | None
    qa_score: int | None = None
    qa_status: str | None = None
    qa_passed: bool
    is_edited: bool
    estimated_cost_usd: Decimal | None
    llm_model: str | None
    created_at: datetime
    updated_at: datetime


class ArticleRead(ArticleSummary):
    seo_title: str
    seo_data: dict[str, Any] = Field(default_factory=dict)
    seo_preview: dict[str, Any] = Field(default_factory=dict)
    seo_origin: str = "article"
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
