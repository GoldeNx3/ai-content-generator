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


def test_text_fields_sent_to_wordpress_are_plain_text():
    xss='</title><script>alert(1)</script>Tytuł'
    p=seo_profile(article(title=xss,meta_title=xss,meta_description='<img src=x onerror=alert(1)>Opis',lead='&lt;script&gt;x&lt;/script&gt; Lead',
        seo_data={'tags':['<img src=x onerror=alert(1)>','AI','C++','<b>Laravel</b>'],'focus_keyword':'<b>klucz</b>'}))
    for key in ('title','seo_title','meta_description','excerpt','og_title','og_description','twitter_title','twitter_description','focus_keyword'):
        assert '<' not in p[key] and '>' not in p[key], (key,p[key])
    assert p['title']=='Tytuł' and p['meta_description']=='Opis'
    assert p['tags']==['AI','C++','Laravel']


def test_profile_overrides_are_validated_against_the_seo_schema():
    with pytest.raises(Exception):
        seo_profile(article(),{'internal_links':['tekst']})
    with pytest.raises(Exception):
        seo_profile(article(),{'faq':[{'question':'q'}]})


def test_verified_internal_links_must_be_http():
    html=content_html(article(content='Zobacz Laravel tutaj.'),{'verified_internal_links':[{'anchor':'Laravel','url':'javascript://wp/a%0aalert(1)'}]})
    assert 'javascript' not in html


def test_llm_cannot_choose_image_author_links_or_indexing():
    from ai.tasks.wordpress import merge_prepared
    current={'featured_image_url':None,'author_id':None,'internal_links':[],'robots_index':True,'seo_title':''}
    generated={'featured_image_url':'https://evil.example/x.png','author_id':7,'internal_links':[{'anchor':'a','url':'https://x'}],
        'robots_index':False,'seo_title':'Nowy tytuł','slug':'x'}
    merged=merge_prepared(current,generated)
    assert merged['featured_image_url'] is None and merged['author_id'] is None and merged['internal_links']==[]
    assert merged['robots_index'] is True and merged['seo_title']=='Nowy tytuł'


def test_article_update_lengths_match_the_api():
    from app.schemas.article import ArticleUpdate
    with pytest.raises(Exception):
        ArticleUpdate(lead='a'*2001)
    with pytest.raises(Exception):
        ArticleUpdate(content='a'*100001)
    assert ArticleUpdate(lead='a'*2000, content='a'*100000).lead
