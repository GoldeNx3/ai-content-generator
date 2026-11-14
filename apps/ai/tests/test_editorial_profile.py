# Rola pliku: Testy profilu redakcyjnego konta: zakres tematów w ocenie, czytelnik/głos/wzorzec w briefie i pisarzu,
# zakazane zwroty jako ostrzeżenie oraz profil w danych dla QA.

from app.schemas.article import ArticleBrief
from app.schemas.editorial import EditorialProfile
from app.services.llm.base import ArticleContext
from app.services.llm.prompt import CLASSIFIER_SYSTEM_PROMPT, classifier_system_prompt
from app.services.llm.writer_prompt import build_brief_prompt, build_writer_prompt
from app.services.article.validation import banned_phrases_found
from tests.article_fakes import make_brief

PROFILE = EditorialProfile(audience='Programiści PHP i właściciele małych firm', voice='Rzeczowo, po koleżeńsku, bez korpomowy',
    topics_scope='Laravel, Symfony, DevOps, AI w programowaniu', banned_phrases=['rewolucja', 'game changer'],
    example_post='## Jak wdrożyliśmy kolejki\n\nKrótkie akapity, konkret.')


def context(editorial=None) -> ArticleContext:
    return ArticleContext(candidate_title='Laravel 13', candidate_source='Laravel News', published_at=None, research_summary='s',
        why_it_matters='w', suggested_angle='a', facts=[], sources=[], uncertainties=[], conflicts=[], article_type='news',
        type_guide='g', length_hint='l', angle=None, instructions=None, article_format='news',
        editorial=editorial.model_dump() if editorial else None)


def test_classifier_uses_the_account_topic_scope_and_audience():
    prompt = classifier_system_prompt(PROFILE)
    assert 'Laravel, Symfony, DevOps, AI w programowaniu' in prompt
    assert 'Programiści PHP' in prompt
    assert classifier_system_prompt(None) == CLASSIFIER_SYSTEM_PROMPT


def test_brief_and_writer_get_reader_voice_banned_phrases_and_style_example():
    brief: ArticleBrief = make_brief([1])
    for prompt in (build_brief_prompt(context(PROFILE)), build_writer_prompt(context(PROFILE), brief)):
        assert 'Programiści PHP i właściciele małych firm' in prompt
        assert 'Rzeczowo, po koleżeńsku' in prompt
        assert '„rewolucja”' in prompt and '„game changer”' in prompt
        assert 'Jak wdrożyliśmy kolejki' in prompt
    assert 'PROFIL REDAKCJI' not in build_writer_prompt(context(None), brief)


def test_banned_phrases_are_found_case_insensitively():
    assert banned_phrases_found('To prawdziwa Rewolucja w PHP.', ['rewolucja', 'game changer']) == ['rewolucja']
    assert banned_phrases_found('Nic tu nie ma.', []) == []


def test_profile_limits_are_enforced():
    import pytest
    with pytest.raises(Exception):
        EditorialProfile(example_post='x' * 6001)
    with pytest.raises(Exception):
        EditorialProfile(banned_phrases=['x'] * 51)


def take_context(take=None) -> ArticleContext:
    return ArticleContext(candidate_title='Laravel 13', candidate_source='Laravel News', published_at=None, research_summary='s',
        why_it_matters='w', suggested_angle='a', facts=[], sources=[], uncertainties=[], conflicts=[], article_type='news',
        type_guide='g', length_hint='l', angle=None, instructions=None, article_format='news', editor_take=take)


def test_editor_take_is_the_only_place_for_opinion_and_must_be_labelled():
    brief = make_brief([1])
    take = 'Używamy kolejek Laravel w 3 projektach; największy problem to monitoring.'
    for prompt in (build_brief_prompt(take_context(take)), build_writer_prompt(take_context(take), brief)):
        assert 'NASZE ZDANIE' in prompt and take in prompt
        assert 'opinia redakcji' in prompt.lower()
    assert 'NASZE ZDANIE' not in build_writer_prompt(take_context(None), brief)


def test_qa_knows_editor_take_is_allowed_opinion():
    from app.services.llm.qa import QA_SYSTEM_PROMPT
    assert 'editor_take' in QA_SYSTEM_PROMPT


LINKS = [{'title': 'Kolejki w Laravel', 'url': 'https://wp.example/blog/kolejki/'}]


def links_context(links=None) -> ArticleContext:
    return ArticleContext(candidate_title='Laravel 13', candidate_source='Laravel News', published_at=None, research_summary='s',
        why_it_matters='w', suggested_angle='a', facts=[], sources=[], uncertainties=[], conflicts=[], article_type='news',
        type_guide='g', length_hint='l', angle=None, instructions=None, article_format='news', internal_links=links)


def test_writer_may_link_only_to_listed_blog_posts():
    prompt = build_writer_prompt(links_context(LINKS), make_brief([1]))
    assert 'LINKI WEWNĘTRZNE' in prompt and 'https://wp.example/blog/kolejki/' in prompt
    assert 'LINKI WEWNĘTRZNE' not in build_writer_prompt(links_context(None), make_brief([1]))


def test_links_to_the_blog_outside_the_list_are_unlinked():
    from app.services.article.validation import enforce_internal_links
    text = ('Zobacz [kolejki](https://wp.example/blog/kolejki/) i [stary wpis](https://wp.example/blog/nie-ma/) '
            'oraz [dokumentację](https://laravel.com/docs).')
    cleaned, removed = enforce_internal_links(text, LINKS)
    assert '[kolejki](https://wp.example/blog/kolejki/)' in cleaned
    assert 'stary wpis' in cleaned and 'blog/nie-ma' not in cleaned
    assert '[dokumentację](https://laravel.com/docs)' in cleaned
    assert removed == ['https://wp.example/blog/nie-ma/']


async def test_classifier_warns_about_a_similar_blog_post():
    from ai.runtime import run
    candidate = {'title': 'Kolejki w Laravel', 'summary': None, 'source': 'RSS', 'published_at': None,
                 'already_covered': {'title': 'Kolejki w Laravel – monitoring', 'url': 'https://wp.example/blog/kolejki/', 'similarity': 0.8}}
    result = (await run({'task': 'classify', 'demo': True, 'input': {'candidate': candidate}}))['result']
    assert 'https://wp.example/blog/kolejki/' in result['reason'] and result['freshness'] <= 20
