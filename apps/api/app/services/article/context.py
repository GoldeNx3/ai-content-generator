# Rola pliku: Buduje niezmienny kontekst writera z ukończonego researchu.
# Ta funkcja nie zapisuje do bazy i nie wywołuje LLM. API używa jej przy enqueue,
# aby worker i wszystkie ponowienia korzystały z tych samych faktów.

from app.models import Candidate, CandidateCategory, FetchStatus, Research
from app.core.config import Settings, get_settings
from app.schemas.article import GenerateArticleRequest
from app.services.article.article_types import guide_for, length_hint, requested_format
from app.services.llm.base import ArticleContext, FactInput, SourceInput
from app.services.research.content_budget import fit_documents


def build_article_context(
    candidate: Candidate,
    research: Research,
    article_type: CandidateCategory,
    request: GenerateArticleRequest,
    settings: Settings | None = None,
) -> ArticleContext:
    settings = settings or get_settings()
    sources = sorted(
        [s for s in research.sources if s.fetch_status == FetchStatus.SUCCESS],
        key=lambda s: (s.origin != "original", -s.source_score, s.id or 0),
    )
    contents = fit_documents(
        [s.extracted_content or "" for s in sources],
        [settings.research_max_chars_original if s.origin == "original"
         else settings.research_max_chars_per_source for s in sources],
        settings.research_max_total_chars,
    )
    source_contents = {s.id: content for s, content in zip(sources, contents)}
    article_format = requested_format(request)
    return ArticleContext(
        candidate_title=candidate.title,
        candidate_source=candidate.source.name,
        published_at=candidate.original_published_at,
        research_summary=research.summary,
        why_it_matters=research.why_it_matters,
        suggested_angle=research.suggested_angle,
        facts=[
            FactInput(
                id=fact.id,
                claim=fact.claim,
                importance=fact.importance.value,
                confidence=fact.confidence,
                source_ids=fact.source_ids,
            )
            for fact in research.facts
        ],
        sources=[
            SourceInput(
                id=s.id,
                publisher=s.publisher,
                title=s.title,
                url=s.url,
                source_type=s.source_type.value,
                source_score=s.source_score,
                content=source_contents.get(s.id, ""),
            )
            for s in sources
        ],
        uncertainties=list(research.uncertainties),
        conflicts=list(research.conflicts),
        article_type=article_type.value,
        type_guide=guide_for(article_format).describe(),
        length_hint=length_hint(article_format, request.length, len(research.facts)),
        angle=(request.angle or "").strip() or None,
        instructions=(request.instructions or "").strip() or None,
        article_format=article_format,
    )
