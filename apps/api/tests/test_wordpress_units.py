from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import httpx
import pytest
from app.core.config import Settings
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.errors import WordPressError
from app.services.wordpress.preparation import slugify, content_html, seo_profile, category_name
from app.schemas.wordpress import PublishRequest
from app.services.jobs.retry import failure


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


@pytest.mark.parametrize('status,retryable',[(401,False),(403,False),(404,False),(429,True),(500,True)])
async def test_http_errors_retry_policy(status,retryable):
    transport=httpx.MockTransport(lambda r:httpx.Response(status,json={'code':'error'},headers={'Retry-After':'42'}))
    async with httpx.AsyncClient(transport=transport) as http:
        wp=WordPressClient(Settings(wordpress_url='https://wp.example',wordpress_username='user',wordpress_app_password='secret'),http)
        with pytest.raises(WordPressError) as raised: await wp.get_post(1)
    assert raised.value.retryable==retryable
    assert failure(raised.value,1)[1]==retryable
    assert 'secret' not in str(raised.value)


async def test_timeout_retry():
    def timeout(r): raise httpx.ReadTimeout('timeout',request=r)
    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as http:
        wp=WordPressClient(Settings(wordpress_url='https://wp.example'),http)
        with pytest.raises(WordPressError) as raised: await wp.get_post(1)
    assert raised.value.retryable


async def test_invalid_json():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='not JSON'))) as http:
        with pytest.raises(WordPressError) as raised:
            await WordPressClient(Settings(wordpress_url='https://wp.example'),http).get_post(1)
    assert raised.value.code=='wordpress_invalid_json'

def test_seo_output_schema_is_openai_strict():
    from openai.lib._pydantic import to_strict_json_schema
    from app.workers.handlers.wordpress import PreparedSEO
    schema=to_strict_json_schema(PreparedSEO)
    def check(node):
        if isinstance(node,dict):
            if node.get('type')=='object':assert node.get('additionalProperties') is False,node
            for value in node.values():check(value)
        elif isinstance(node,list):
            for value in node:check(value)
    check(schema)

def test_generated_category_is_restricted_to_allowlist():
    assert seo_profile(article(),{'category':'Sztuczna inteligencja'})['category']=='Newsy'

async def test_preparation_preserves_approved_extended_seo(monkeypatch):
    from app.workers.handlers.wordpress import prepare_profile,PreparedSEO
    from app.services.llm.base import LLMUsage
    original=seo_profile(article(seo_data={'og_title':'Zatwierdzony OG','og_description':'Zatwierdzony opis OG','excerpt':'Zatwierdzony excerpt','secondary_keywords':['approved'],'schema_type':'TechArticle'}))
    class LLM:
        def __init__(self,*a,**k):self._client=self
        async def close(self):pass
        async def parse(self,*a,**k):return PreparedSEO(seo_title='Nowy title',meta_description='Nowy opis',slug='nowy',og_title='Nowy OG',og_description='Nowy OG opis',excerpt='Nowy excerpt',secondary_keywords=['new'],focus_keyword='Claude',tags=['Claude','Anthropic','Barclays']),LLMUsage('test',1,1)
    class Recorder:
        async def call(self,stage,invoke,result_type):return await invoke()
    monkeypatch.setattr('app.workers.handlers.wordpress.OpenAIClient',LLM)
    result=await prepare_profile(article(),original,Recorder(),Settings())
    for key in ('seo_title','meta_description','slug','og_title','og_description','excerpt','secondary_keywords','schema_type'):
        assert result[key]==original[key],key
    assert result['tags']==['Claude','Anthropic','Barclays'] and result['focus_keyword']=='Claude'


def test_verification_checks_body_and_taxonomy():
    from app.services.wordpress.service import WordPressPublisherService
    payload={'title':'Title','content':'<p>Approved</p>','categories':[1],'tags':[2],'author':1}
    post={'title':{'raw':'Title'},'content':{'raw':'<p>Changed</p>'},'slug':'title','categories':[1],'tags':[2],'author':1}
    with pytest.raises(WordPressError):WordPressPublisherService.verify(post,payload,{'slug':'title'},None)
