from dataclasses import asdict

import httpx
import pytest
from pydantic import TypeAdapter

from app.core.config import get_settings
from app.enums import CandidateCategory
from app.schemas.article import ArticleBrief, ArticleLength, GenerateArticleRequest
from app.services.article.article_types import resolve_length
from app.services.article.validation import validate_brief
from app.services.llm.base import ArticleContext
from app.services.llm.cost import LLMCostCalculator
from app.services.llm.writer_prompt import build_brief_prompt, build_writer_prompt
from app.services.research.search import ManualSearchProvider
from tests.article_fakes import FakeArticleLLM, make_brief
from tests.research_fakes import FakeResearchLLM, extractor_for, html_response


def test_rich_brief_is_not_capped_by_eight_required_facts():
    assert resolve_length('explainer', ArticleLength.AUTO, 1800, 8) == 1800


@pytest.mark.parametrize('format_name,target', [
    ('news', 1000), ('explainer', 1800), ('case_study', 2200),
    ('guide', 2500), ('comparison', 2500),
])
def test_long_has_a_real_target_even_when_brief_is_short(format_name, target):
    assert resolve_length(format_name, ArticleLength.LONG, 400, 8) >= target


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


