# Rola pliku: Eksportuje modele ORM i rejestruje ich tabele w metadanych SQLAlchemy.

from app.models.article import Article
from app.models.candidate import Candidate
from app.models.enums import (
    ArticleStatus,
    CandidateCategory,
    CandidateStatus,
    FactBasis,
    FactImportance,
    FetchStatus,
    ResearchSourceOrigin,
    ResearchSourceType,
    ResearchStatus,
    SourceType,
)
from app.models.research import Research, ResearchFact, ResearchSource, research_fact_sources
from app.models.source import Source

__all__ = [
    "Article",
    "ArticleStatus",
    "Candidate",
    "CandidateCategory",
    "CandidateStatus",
    "FactBasis",
    "FactImportance",
    "FetchStatus",
    "Research",
    "ResearchFact",
    "ResearchSource",
    "ResearchSourceOrigin",
    "ResearchSourceType",
    "ResearchStatus",
    "Source",
    "SourceType",
    "research_fact_sources",
]

# Import rejestruje nowe tabele w metadanych ORM i Alembic.
from app.models.job import Job, JobAttempt, JobBatch

from app.models.qa import ArticleQA, ArticleQAIssue

from app.models.auto_fix import ArticleFix, ArticleFixIssue

from app.models.wordpress import WordPressPublication
