import pytest

from app.models import CandidateCategory
from app.schemas.article import ArticleBrief, GenerateArticleRequest
from app.services.article.article_service import ArticleService
from app.services.article.article_types import resolve_length
from app.schemas.article import ArticleLength
from app.services.llm.cost import LLMCostCalculator
from tests.article_fakes import FakeArticleLLM, make_brief, research_fixture


def test_brief_accepts_a_complete_short_news_budget():
    brief = ArticleBrief.model_validate({**make_brief([1, 2]).model_dump(), 'desired_length_words': 70})
    assert brief.desired_length_words == 70


async def test_old_frozen_queue_context_preserves_manual_format(session):
    from dataclasses import asdict
    from pydantic import TypeAdapter
    from app.services.article.context import build_article_context
    from app.services.llm.base import ArticleContext

    candidate, research = await research_fixture(session)
    await session.refresh(candidate, ['source'])
    request = GenerateArticleRequest(article_type=CandidateCategory.GUIDE)
    payload = asdict(build_article_context(candidate, research, CandidateCategory.GUIDE, request))
    payload.pop('article_format')  # Serialized before the new field existed.
    context = TypeAdapter(ArticleContext).validate_python(payload)
    article = await ArticleService(session, FakeArticleLLM(), LLMCostCalculator({})).generate(
        candidate.id, request, context=context,
    )
    assert article.article_format == 'guide'


async def test_draft_far_below_planned_length_is_flagged(session):
    candidate, _ = await research_fixture(session)
    article = await ArticleService(session, FakeArticleLLM(), LLMCostCalculator({})).generate(
        candidate.id, GenerateArticleRequest(),
    )
    assert article.word_count < article.brief['desired_length_words'] * 0.6
    assert any('za krótki' in w for w in article.validation_warnings)


async def test_auto_format_uses_research_brief_instead_of_rss_category(session):
    candidate, _ = await research_fixture(session)
    candidate.category = CandidateCategory.GUIDE
    await session.commit()

    def brief(context):
        return ArticleBrief.model_validate({
            **make_brief([f.id for f in context.facts]).model_dump(),
            'article_format': 'case_study', 'desired_length_words': 180,
        })

    llm = FakeArticleLLM(brief=brief)
    article = await ArticleService(session, llm, LLMCostCalculator({})).generate(
        candidate.id, GenerateArticleRequest(),
    )
    assert llm.contexts[0].article_format == 'auto'
    assert article.article_type == CandidateCategory.GUIDE
    assert article.article_format == 'case_study'
    assert article.brief['desired_length_words'] == 180
    assert llm.briefs[0].article_format == 'case_study'


async def test_explicit_format_and_angle_override_brief_and_survive_regeneration(session):
    candidate, _ = await research_fixture(session)
    llm = FakeArticleLLM()
    service = ArticleService(session, llm, LLMCostCalculator({}))
    first = await service.generate(candidate.id, GenerateArticleRequest.model_validate({
        'article_format': 'case_study', 'angle': 'Dlaczego migracja trwała tak długo?',
        'instructions': 'Skup się na przeszkodach.',
    }))
    second = await service.regenerate(first.id, GenerateArticleRequest(length=ArticleLength.SHORT))
    assert first.article_format == second.article_format == 'case_study'
    assert second.angle == 'Dlaczego migracja trwała tak długo?'
    assert llm.briefs[-1].primary_angle == second.angle
    assert second.generation_options['article_format'] == 'case_study'
    assert second.generation_options['instructions'] == 'Skup się na przeszkodach.'


@pytest.mark.parametrize('format_name', ['news', 'explainer', 'case_study', 'guide', 'comparison'])
def test_auto_length_does_not_pad_short_material_to_a_format_minimum(format_name):
    assert resolve_length(format_name, ArticleLength.AUTO, 180, 20) == 180


def test_short_length_does_not_expand_a_short_brief():
    assert resolve_length('case_study', ArticleLength.SHORT, 180, 20) == 180


async def test_required_fact_count_does_not_shrink_editorial_budget(session):
    candidate, _ = await research_fixture(session)

    def brief(context):
        return make_brief([f.id for f in context.facts]).model_copy(update={
            'required_facts': [context.facts[0].id],
            'optional_facts': [f.id for f in context.facts[1:]],
        })

    article = await ArticleService(session, FakeArticleLLM(brief=brief), LLMCostCalculator({})).generate(
        candidate.id, GenerateArticleRequest(),
    )
    assert article.brief['desired_length_words'] == 1200
