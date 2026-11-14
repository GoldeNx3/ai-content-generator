# Rola pliku: Testy mocniejszego researchu i QA: rodzaj podstawy faktu (deklaracja producenta) dociera do pisarza
# i QA, deterministyczny test oryginalności (wspólne 8-gramy ze źródłem) oraz głębokość wyszukiwania Tavily.

import json

import httpx

from app.core.config import Settings
from app.services.llm.base import ArticleContext, FactInput
from app.services.llm.qa import QA_SYSTEM_PROMPT
from app.services.llm.writer_prompt import WRITER_SYSTEM_PROMPT, build_writer_prompt
from app.services.qa.originality import source_overlap_issues
from app.services.research.search import TavilySearchProvider
from tests.article_fakes import make_brief

SOURCE = ('Firma Acme ogłosiła dziś nowy procesor Turbo X, który według producenta jest trzy razy szybszy od '
          'poprzedniej generacji i zużywa o połowę mniej energii w typowych zadaniach biurowych oraz w grach.')


def context(facts) -> ArticleContext:
    return ArticleContext(candidate_title='Turbo X', candidate_source='Acme', published_at=None, research_summary='s',
        why_it_matters='w', suggested_angle='a', facts=facts, sources=[], uncertainties=[], conflicts=[], article_type='news',
        type_guide='g', length_hint='l', angle=None, instructions=None, article_format='news')


def test_vendor_claims_reach_the_writer_with_an_attribution_rule():
    fact = FactInput(1, 'Turbo X jest 3x szybszy', 'high', 60, [2], basis='vendor_claim')
    prompt = build_writer_prompt(context([fact]), make_brief([1]))
    assert 'Basis: vendor_claim' in prompt
    assert 'Basis: vendor_claim' in WRITER_SYSTEM_PROMPT and 'według producenta' in WRITER_SYSTEM_PROMPT
    assert 'Basis:' not in build_writer_prompt(context([FactInput(1, 'c', 'high', 90, [2])]), make_brief([1]))


def test_qa_checks_attribution_of_vendor_claims():
    assert 'vendor_claim' in QA_SYSTEM_PROMPT


def snapshot(content: str) -> dict:
    return {'article': {'lead': 'Acme pokazała procesor.', 'content': content},
            'research': {'sources': [{'id': 7, 'content': SOURCE}, {'id': 8, 'content': None}]}}


def test_copied_paragraph_is_flagged_as_too_close_to_source():
    issues = source_overlap_issues(snapshot(f'## Co wiemy\n\n{SOURCE}\n\n## Dalej\n\nInny akapit własny.'), 0.15)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.type == 'too_close_to_source'
    assert issue.source_ids == [7]
    assert issue.excerpt == SOURCE
    assert issue.section_heading == 'Co wiemy'
    assert issue.auto_fixable is True


def test_own_wording_and_quotes_are_not_flagged():
    own = ('Turbo X to odpowiedź Acme na rosnącą konkurencję. Producent obiecuje trzykrotny wzrost szybkości, ale '
           'niezależnych testów jeszcze nie ma, więc warto poczekać na pierwsze recenzje.')
    assert source_overlap_issues(snapshot(f'## Co wiemy\n\n{own}'), 0.15) == []
    assert source_overlap_issues(snapshot(f'## Cytat\n\n> {SOURCE}\n\n{own}'), 0.15) == []


async def test_tavily_uses_the_configured_search_depth():
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(lambda request: captured.append(request) or httpx.Response(200, json={'results': []}))
    provider = TavilySearchProvider('tvly-test', client=httpx.AsyncClient(transport=transport), search_depth='advanced')
    await provider.search('turbo x', limit=8)
    assert json.loads(captured[0].content)['search_depth'] == 'advanced'


def test_research_defaults_are_stronger():
    settings = Settings(_env_file=None)
    assert settings.research_max_extra_sources == 8
    assert settings.tavily_search_depth == 'advanced'
    assert settings.qa_max_source_overlap == 0.15


async def test_fact_basis_survives_research_and_the_article_snapshot():
    from ai.runtime import run
    source = {'id': 3, 'url': 'https://demo.content-engine.invalid/a', 'origin': 'original', 'fetch_status': 'success',
              'extracted_content': 'Treść źródła o nowym modelu.'}
    analysed = await run({'task': 'research.analyse', 'demo': True, 'input': {
        'candidate': {'title': 'Nowy model', 'summary': 'Opis', 'source': 'Blog'}, 'original_url': source['url'],
        'sources': [source]}})
    assert analysed['ok'], analysed
    assert {fact['basis'] for fact in analysed['result']['facts']} == {'verifiable'}

    from ai.tasks.article import FactPayload, _snapshot
    from app.services.llm.base import FactInput
    assert FactPayload(id=1, claim='c', importance='high', confidence=60, basis='vendor_claim').basis == 'vendor_claim'
    snapshot = _snapshot(context([FactInput(1, 'c', 'high', 60, [3], basis='vendor_claim')]))
    assert snapshot['facts'][0]['basis'] == 'vendor_claim'


async def test_sources_from_the_same_topic_group_are_accepted_by_analysis():
    from ai.runtime import run
    original = {'id': 3, 'url': 'https://demo.content-engine.invalid/a', 'origin': 'original', 'fetch_status': 'success',
                'extracted_content': 'Treść źródła o nowym modelu.'}
    sibling = {**original, 'id': 4, 'url': 'https://b.example/x', 'origin': 'sibling'}
    analysed = await run({'task': 'research.analyse', 'demo': True, 'input': {
        'candidate': {'title': 'Nowy model', 'summary': 'Opis', 'source': 'Blog'}, 'original_url': original['url'],
        'sources': [original, sibling]}})
    assert analysed['ok'], analysed


CODE = 'php artisan queue:work redis --queue=pipeline --tries=3 --timeout=300 --sleep=1 --max-jobs=1000 --max-time=3600 --memory=512 --rest=0 --backoff=15 --name=worker'


def test_prose_after_a_code_block_with_blank_lines_is_still_checked():
    content = f'## Kod\n\n```bash\necho start\n\necho koniec\n```\n\n## Co wiemy\n\n{SOURCE}'
    issues = source_overlap_issues(snapshot(content), 0.15)
    assert [issue.excerpt for issue in issues] == [SOURCE]


def test_code_glued_to_a_paragraph_is_not_counted_as_prose():
    data = snapshot(f'## Uruchomienie\n\nWorker startujemy jednym poleceniem:\n```bash\n{CODE}\n```')
    data['research']['sources'][0]['content'] = CODE
    assert source_overlap_issues(data, 0.15) == []


BLOG = 'https://wp.example/blog'
ALLOWED = [{'title': 'Kolejki', 'url': 'https://wp.example/blog/kolejki/'}]


def test_allowed_blog_links_survive_small_url_differences():
    from app.services.article.validation import enforce_internal_links
    text = '[a](https://wp.example/blog/kolejki) [b](https://www.wp.example/blog/kolejki/?utm_source=x)'
    assert enforce_internal_links(text, ALLOWED, BLOG) == (text, [])


def test_relative_html_and_unlisted_blog_links_are_unlinked_even_without_a_list():
    from app.services.article.validation import enforce_internal_links
    text = ('[rel](/blog/nie-ma/) <a href="https://wp.example/blog/nie-ma/">html</a> '
            '[www](https://www.wp.example/blog/inny/) [zewn](https://laravel.com/docs)')
    cleaned, removed = enforce_internal_links(text, [], BLOG)
    assert cleaned == 'rel html www [zewn](https://laravel.com/docs)'
    assert len(removed) == 3
    assert enforce_internal_links('[rel](/x/)', [], None)[0] == 'rel'


def test_blog_links_are_checked_even_when_no_post_matched_the_topic():
    from ai.tasks.article import _enforce_links
    from tests.article_fakes import make_output
    output = make_output([1, 2], [2, 3])
    output = output.model_copy(update={'lead': 'Zobacz [stary](https://wp.example/blog/zmyslony/).'})
    cleaned, removed = _enforce_links(output, [], BLOG)
    assert cleaned.lead == 'Zobacz stary.'
    assert removed == ['https://wp.example/blog/zmyslony/']


async def test_tavily_searches_are_recorded_with_their_credit_cost(monkeypatch):
    from decimal import Decimal

    from ai.context import TaskContext
    from ai.runtime import run
    from tests.research_fakes import FakeResearchLLM

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'results': []}))
    provider = TavilySearchProvider('tvly-test', client=httpx.AsyncClient(transport=transport), search_depth='advanced')
    settings = Settings(search_provider='tavily', tavily_api_key='tvly-test', tavily_search_depth='advanced', tavily_credit_usd=0.008)
    ctx = TaskContext(settings=settings)
    ctx._providers = {'research': FakeResearchLLM(queries=['turbo x', 'turbo x cena'])}
    monkeypatch.setattr(TaskContext, 'search', property(lambda self: provider))

    response = await run({'task': 'research.discover', 'input': {
        'candidate': {'title': 'Turbo X', 'source': 'Acme'}, 'original_url': 'https://acme.example/turbo'}}, ctx)

    searches = [call for call in response['calls'] if call['stage'] == 'searching_sources']
    assert [call['usage']['search_credits'] for call in searches] == [2, 2]
    assert [call['estimated_cost_usd'] for call in searches] == ['0.016000', '0.016000']
    assert 'model' not in searches[0]['usage']
    assert ctx.total_cost() == Decimal('0.032') + Decimal(response['calls'][0]['estimated_cost_usd'])


def test_basic_tavily_search_costs_one_credit():
    assert TavilySearchProvider('k', search_depth='basic').credits_per_query == 1
    assert TavilySearchProvider('k', search_depth='advanced').credits_per_query == 2
