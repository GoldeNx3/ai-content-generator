from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import httpx
import pytest
from app.core.config import Settings
from app.services.wordpress.preparation import slugify, content_html, seo_profile, category_name
from app.schemas.wordpress import PublishRequest


def article(**changes):
    values=dict(title='Claude Code w Barclays: wdrożenie AI', slug='claude-code-barclays',
        meta_title='Claude Code w Barclays – zastosowania AI w banku',meta_description='Barclays wdraża Claude Code. Artykuł omawia zastosowania narzędzia w programowaniu, dostępne informacje o wdrożeniu i ograniczenia danych.',
        lead='Barclays korzysta z Claude Code.',content='## Zastosowanie\n\nTekst.',
        article_type='news',article_format='news',seo_data={},brief={},research_snapshot={'sources':[]})
    return SimpleNamespace(**(values|changes))


def test_slug_generation():
    assert slugify('Żółć: Claude Code — wdrożenie w Barclays 2026') == 'zolc-claude-code-wdrozenie-w-barclays-2026'


def test_markdown_html_and_no_h1():
    rendered=content_html(article(content='# Tytuł\n\n## Sekcja\n\n### Detale\n\n**Mocne** i *kursywa*.\n\n> Cytat\n\n- Lista\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n[Źródło](https://example.org)'))
    for tag in ('<h2>','<h3>','<strong>','<em>','<blockquote>','<ul>','<table>','rel="noopener"'):
        assert tag in rendered
    assert '<h1' not in rendered


def test_seo_title_description_og_and_schema():
    a=article(); p=seo_profile(a)
    assert p['seo_title']==a.meta_title and p['meta_description']==a.meta_description
    assert p['og_title']==p['twitter_title']==p['seo_title']
    assert p['og_description']==p['meta_description']
    assert p['canonical_url'] is None and p['schema_type']=='NewsArticle'
    assert p['robots_index'] and p['robots_follow']


def test_schema_cannot_invent_faq_or_howto():
    assert seo_profile(article(seo_data={'schema_type':'FAQPage'}))['schema_type']=='NewsArticle'
    assert seo_profile(article(seo_data={'schema_type':'HowTo'}))['schema_type']=='NewsArticle'


@pytest.mark.parametrize('kind,expected',[('news','Newsy'),('release','Newsy'),('guide','Poradniki'),('comparison','Porównania'),('tool','Narzędzia AI'),('pricing','Biznes'),('other','AI')])
def test_category_mapping(kind,expected):
    assert category_name(article(article_type=kind))==expected


def test_schedule_requires_timezone_and_future():
    with pytest.raises(ValueError): PublishRequest(status='future',scheduled_at='2026-10-05T08:00:00')
    with pytest.raises(ValueError): PublishRequest(status='future')
    with pytest.raises(ValueError): PublishRequest(status='future',scheduled_at=datetime.now(timezone.utc)-timedelta(days=1))
    value=PublishRequest(status='future',scheduled_at=datetime.now(timezone.utc)+timedelta(days=1))
    assert value.scheduled_at.utcoffset()==timedelta(0)
    assert PublishRequest().status=='draft'


def test_generated_category_is_restricted_to_allowlist():
    assert seo_profile(article(),{'category':'Sztuczna inteligencja'})['category']=='Newsy'


def test_writer_requires_nonempty_extended_seo_when_supplied():
    from app.schemas.article import WriterSEOData
    with pytest.raises(ValueError):WriterSEOData.model_validate({'excerpt':'','focus_keyword':'','secondary_keywords':[],'tags':[],'category':None,'og_title':'','og_description':'','twitter_title':'','twitter_description':''})
    from openai.lib._pydantic import to_strict_json_schema
    from app.schemas.article import WriterOutput
    schema=to_strict_json_schema(WriterOutput)
    seo=schema['$defs']['WriterSEOData']
    assert seo['properties']['focus_keyword']['minLength']==1
    assert seo['properties']['tags']['minItems']==3
    assert 'seo_data' in schema['required']
