# Rola pliku: Testy trybu aktualizacji starego wpisu: stara treść trafia do briefu i pisarza z zasadami odświeżenia,
# a link do starego wpisu jest dozwolony mimo kontroli linków wewnętrznych.

from app.services.llm.base import ArticleContext
from app.services.llm.writer_prompt import build_brief_prompt, build_writer_prompt
from tests.article_fakes import make_brief, make_output

BLOG = 'https://wp.example/blog'
OLD = {'title': 'Kolejki w Laravel 12', 'url': 'https://wp.example/blog/kolejki-laravel-12/',
       'content': 'Laravel 12 wprowadził kolejki z priorytetami. Horizon pokazuje metryki.'}


def context(refresh=None) -> ArticleContext:
    return ArticleContext(candidate_title='Laravel 13: kolejki', candidate_source='Laravel News', published_at=None,
        research_summary='s', why_it_matters='w', suggested_angle='a', facts=[], sources=[], uncertainties=[],
        conflicts=[], article_type='news', type_guide='g', length_hint='l', angle=None, instructions=None,
        article_format='news', blog_url=BLOG, refresh_of=refresh)


def test_brief_and_writer_get_the_old_post_and_refresh_rules():
    for prompt in (build_brief_prompt(context(OLD)), build_writer_prompt(context(OLD), make_brief([1]))):
        assert 'AKTUALIZACJA WPISU' in prompt
        assert 'Kolejki w Laravel 12' in prompt
        assert 'Horizon pokazuje metryki.' in prompt
        assert OLD['url'] in prompt
    assert 'AKTUALIZACJA WPISU' not in build_writer_prompt(context(None), make_brief([1]))


def test_the_link_to_the_refreshed_post_survives_link_checks():
    from ai.tasks.article import _enforce_links, allowed_links
    output = make_output([1, 2], [2, 3]).model_copy(update={
        'lead': f'Wcześniej pisaliśmy [o kolejkach]({OLD["url"]}) i [o czymś]({BLOG}/inny/).'})

    cleaned, removed = _enforce_links(output, allowed_links(context(OLD)), BLOG)

    assert f'[o kolejkach]({OLD["url"]})' in cleaned.lead
    assert removed == [f'{BLOG}/inny/']


def test_refresh_input_is_limited():
    import pytest
    from pydantic import ValidationError

    from ai.tasks.article import RefreshOf
    with pytest.raises(ValidationError):
        RefreshOf(title='t', url='https://wp.example/x', content='a' * 20001)
    with pytest.raises(ValidationError):
        RefreshOf(title='t', url='ftp://wp.example/x', content='a')
