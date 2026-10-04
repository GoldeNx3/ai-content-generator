from dataclasses import asdict

import httpx
import pytest
from pydantic import TypeAdapter

from app.core.config import get_settings
from app.models import Candidate, CandidateCategory, Source
from app.schemas.article import ArticleBrief, ArticleLength, GenerateArticleRequest
from app.services.article.article_types import resolve_length
from app.services.article.context import build_article_context
from app.services.article.validation import validate_brief
from app.services.article.write import ArticleService
from app.services.llm.base import ArticleContext
from app.services.llm.cost import LLMCostCalculator
from app.services.llm.writer_prompt import build_brief_prompt, build_writer_prompt
from app.services.research.research import ResearchService
from app.services.research.search import ManualSearchProvider
from tests.article_fakes import FakeArticleLLM, make_brief, research_fixture
from tests.research_fakes import FakeResearchLLM, extractor_for, html_response


def test_rich_brief_is_not_capped_by_eight_required_facts():
    assert resolve_length('explainer', ArticleLength.AUTO, 1800, 8) == 1800


@pytest.mark.parametrize('format_name,target', [
    ('news', 1000), ('explainer', 1800), ('case_study', 2200),
    ('guide', 2500), ('comparison', 2500),
])
def test_long_has_a_real_target_even_when_brief_is_short(format_name, target):
    assert resolve_length(format_name, ArticleLength.LONG, 400, 8) >= target


async def test_sources_and_section_plan_reach_writer_and_frozen_context(session):
    candidate, research = await research_fixture(session)
    research.sources[0].extracted_content = 'Udokumentowany mechanizm: proces składa się z dwóch etapów.'
    await session.commit()
    await session.refresh(candidate, ['source'])
    context = build_article_context(candidate, research, candidate.category, GenerateArticleRequest())
    restored = TypeAdapter(ArticleContext).validate_python(asdict(context))
    assert restored.sources[0].content == research.sources[0].extracted_content
    brief = ArticleBrief.model_validate({**make_brief([f.id for f in context.facts]).model_dump(),
        'section_plan': [{'heading': 'Mechanizm', 'purpose': 'Wyjaśnić dwa etapy',
                          'fact_ids': [context.facts[0].id], 'target_words': 350}],
        'research_gaps': ['Brak warunków wdrożenia'],
    })
    assert 'Udokumentowany mechanizm' in build_brief_prompt(restored)
    assert 'Udokumentowany mechanizm' in build_writer_prompt(restored, brief)
    assert 'Wyjaśnić dwa etapy' in build_writer_prompt(restored, brief)
    assert brief.research_gaps == ['Brak warunków wdrożenia']


async def test_section_plan_rejects_unknown_fact_ids(session):
    _, research = await research_fixture(session)
    from app.services.llm.base import FactInput
    facts = [FactInput(f.id, f.claim, f.importance, f.confidence, f.source_ids) for f in research.facts]
    brief = ArticleBrief.model_validate({**make_brief([f.id for f in facts]).model_dump(),
        'section_plan': [{'heading': 'Mechanizm', 'purpose': 'Wyjaśnić',
                          'fact_ids': [facts[0].id, 99999], 'target_words': 350}],
    })
    validated, warnings = validate_brief(brief, facts)
    assert validated.section_plan[0].fact_ids == [facts[0].id]
    assert any('99999' in w for w in warnings)


async def test_long_shortfall_and_research_gaps_are_visible(session):
    candidate, _ = await research_fixture(session)
    def brief(context):
        return ArticleBrief.model_validate({**make_brief([f.id for f in context.facts]).model_dump(),
            'article_format': 'explainer', 'desired_length_words': 1100,
            'research_gaps': ['Brak szczegółów konfiguracji'],
        })
    article = await ArticleService(session, FakeArticleLLM(brief=brief), LLMCostCalculator({})).generate(
        candidate.id, GenerateArticleRequest(length=ArticleLength.LONG))
    assert article.brief['desired_length_words'] >= 1800
    assert any('za krótki' in w.lower() for w in article.validation_warnings)
    assert any('Brak szczegółów konfiguracji' in w for w in article.validation_warnings)


def test_link_discovery_only_uses_public_editorial_links():
    from app.services.research.link_discovery import discover_article_links
    html = '''<nav><a href="/pricing">Pricing</a></nav><article>
      <a href="/docs/migration">Migration guide</a>
      <a href="/docs/migration#step2">Migration guide</a>
      <a href="https://github.com/sveltejs/kit/releases">Release notes</a>
      <a href="/privacy">Privacy</a><a href="mailto:x@example.com">Email</a>
      <a href="http://127.0.0.1/admin">Migration guide</a>
      <a href="/">Home</a>
    </article><aside><a href="/unrelated">Other story</a></aside>'''
    links = discover_article_links(html, 'https://svelte.dev/blog/kit')
    assert [link.url for link in links] == [
        'https://svelte.dev/docs/migration', 'https://github.com/sveltejs/kit/releases']


def test_link_discovery_handles_article_body_without_semantic_tags():
    from app.services.research.link_discovery import discover_article_links
    html = '''<body><div class="uni-nav-desktop"><a href="/other">Other</a></div>
      <div itemprop="articleBody"><p><a href="/docs/model">Model documentation</a></p></div>
      <div class="related-posts"><a href="/different">Unrelated</a></div></body>'''
    assert [r.url for r in discover_article_links(html, 'https://example.com/post')] == [
        'https://example.com/docs/model']


def test_retained_html_does_not_lose_article_links_to_large_scripts():
    from app.services.research.link_discovery import compact_source_html, discover_article_links
    html = '<html><script>' + 'x' * 400000 + '</script><body><article>' + (
        '<a href="/docs/migration">Migration guide</a></article></body></html>')
    retained = compact_source_html(html, 1000)
    assert len(retained) <= 1000
    assert [r.url for r in discover_article_links(retained, 'https://example.com/post')] == [
        'https://example.com/docs/migration']


def test_retained_links_use_final_redirect_url():
    from app.services.research.link_discovery import compact_source_html, discover_article_links
    html = '<article><a href="#section">Contents</a><a href="details">Details</a></article>'
    retained = compact_source_html(html, 1000, base_url='https://example.com/blog/new/')
    assert [r.url for r in discover_article_links(retained, 'https://example.com/old/post')] == [
        'https://example.com/blog/new/details']


def test_malformed_editorial_links_do_not_discard_valid_evidence():
    from app.services.research.link_discovery import discover_article_links
    html = '''<article><a href="https://[broken/docs">Bad URL</a>
      <a href="https://example.com:broken/docs">Bad port</a>
      <a href="/docs/migration">Migration guide</a></article>'''
    assert [r.url for r in discover_article_links(html, 'https://example.com/post')] == [
        'https://example.com/docs/migration']


async def test_writer_budget_preserves_original_after_manual_sources_on_rerun(session):
    from app.models import ResearchSource, ResearchSourceOrigin, FetchStatus
    candidate, research = await research_fixture(session)
    research.sources[0].origin = ResearchSourceOrigin.MANUAL
    research.sources[0].extracted_content = 'manual ' * 2000
    research.sources[1].extracted_content = 'manual ' * 2000
    research.sources.extend(ResearchSource(
        url=f'https://example.com/manual-{i}', origin=ResearchSourceOrigin.MANUAL,
        fetch_status=FetchStatus.SUCCESS, source_score=50, extracted_content='manual ' * 2000,
    ) for i in range(4))
    original = ResearchSource(url='https://example.com/original', origin=ResearchSourceOrigin.ORIGINAL,
        fetch_status=FetchStatus.SUCCESS, source_score=100, extracted_content='original evidence ' * 2000)
    research.sources.append(original)
    await session.commit()
    await session.refresh(candidate, ['source'])
    await session.refresh(research)
    context = build_article_context(candidate, research, candidate.category, GenerateArticleRequest())
    assert context.sources[0].id == original.id
    assert context.sources[0].content.startswith('original evidence')


async def test_manual_research_fetches_linked_documents_without_paid_query_generation(session):
    original = 'https://svelte.dev/blog/kit'
    docs = 'https://svelte.dev/docs/migration'
    feed = Source(name='Svelte', url='https://svelte.dev/rss.xml')
    session.add(feed)
    await session.flush()
    candidate = Candidate(source_id=feed.id, title='SvelteKit migration', external_url=original)
    session.add(candidate)
    await session.commit()
    page = html_response('SvelteKit migration')
    html = page.text.replace('</article>', '<a href="/docs/migration">Migration guide</a></article>')
    llm = FakeResearchLLM()
    async def unexpected_query(_):
        pytest.fail('Manual mode should not pay for unused search queries')
    llm.generate_search_queries = unexpected_query
    service = ResearchService(session, extractor_for({
        original: httpx.Response(200, text=html, headers={'content-type': 'text/html'}),
        docs: html_response('Migration guide'),
    }), ManualSearchProvider(), llm, LLMCostCalculator({}), get_settings())
    report = await service.research_candidate(candidate.id)
    assert report.status == 'completed'
    assert {d.url for d in llm.documents} == {original, docs}
    assert report.search_queries == []
