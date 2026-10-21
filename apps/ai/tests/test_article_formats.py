import pytest

from app.enums import CandidateCategory
from app.schemas.article import ArticleBrief, GenerateArticleRequest
from app.services.article.article_types import resolve_length
from app.schemas.article import ArticleLength
from app.services.llm.cost import LLMCostCalculator
from tests.article_fakes import FakeArticleLLM, make_brief


def test_brief_accepts_a_complete_short_news_budget():
    brief = ArticleBrief.model_validate({**make_brief([1, 2]).model_dump(), 'desired_length_words': 70})
    assert brief.desired_length_words == 70


@pytest.mark.parametrize('format_name', ['news', 'explainer', 'case_study', 'guide', 'comparison'])
def test_auto_length_does_not_pad_short_material_to_a_format_minimum(format_name):
    assert resolve_length(format_name, ArticleLength.AUTO, 180, 20) == 180


def test_short_length_does_not_expand_a_short_brief():
    assert resolve_length('case_study', ArticleLength.SHORT, 180, 20) == 180


