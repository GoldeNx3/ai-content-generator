"""Pure editorial preparation: no new research and no changes to approved text."""
import hashlib
import re
import unicodedata
from html import escape
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from app.schemas.wordpress import SEOData

CATEGORIES=('AI','Modele AI','Programowanie','Narzędzia AI','Automatyzacja','Biznes','Newsy','Poradniki','Porównania')

def slugify(value):
    value=value.replace('ł','l').replace('Ł','L')
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    parts=[p for p in re.split('[^a-z0-9]+',value) if p]
    result=[]
    for part in parts:
        if len('-'.join(result+[part]))>100: break
        result.append(part)
    return '-'.join(result)

def category_name(article):
    return {'news':'Newsy','release':'Newsy','guide':'Poradniki','comparison':'Porównania','tool':'Narzędzia AI','pricing':'Biznes'}.get(str(article.article_type),'AI')

def plain(value):
    return BeautifulSoup(MarkdownIt('commonmark',{'html':False}).render(value or ''),'html.parser').get_text(' ',strip=True)

def plain_text(value):
    """Plain text for WordPress fields that themes may print unescaped (title, excerpt, tags, meta)."""
    value=BeautifulSoup(str(value or ''),'html.parser').get_text('')
    value=re.sub(r'<[^>]*>','',value).replace('<','').replace('>','')
    return re.sub(r'\s+',' ',value).strip()

TEXT_FIELDS=('title','seo_title','meta_description','excerpt','og_title','og_description','twitter_title','twitter_description','focus_keyword')

def seo_profile(article, overrides=None):
    data=SEOData.model_validate(getattr(article,'seo_data',None) or {}).model_dump()
    profile={**data,'title':article.title,'slug':article.slug,'seo_title':article.meta_title,'meta_description':article.meta_description}
    profile.update(overrides or {})
    profile['category']=profile.get('category') if profile.get('category') in CATEGORIES else category_name(article)
    profile['excerpt']=profile.get('excerpt') or plain(article.lead)
    for prefix in ('og','twitter'):
        profile[prefix+'_title']=profile.get(prefix+'_title') or profile['seo_title']
        profile[prefix+'_description']=profile.get(prefix+'_description') or profile['meta_description']
    default='NewsArticle' if str(article.article_type) in ('news','release') else 'Article'
    if not (getattr(article,'seo_data',None) or {}).get('schema_type') and not (overrides or {}).get('schema_type'):
        profile['schema_type']=default
    text=plain(article.content)
    faq=[entry for entry in profile.get('faq',[]) if entry.get('question') and entry.get('answer') and plain(entry['question']) in text and plain(entry['answer']) in text]
    steps=[entry for entry in profile.get('howto_steps',[]) if entry.get('text') and plain(entry['text']) in text]
    profile['faq']=faq;profile['howto_steps']=steps
    if profile['schema_type']=='FAQPage' and not faq or profile['schema_type']=='HowTo' and not steps:
        profile['schema_type']=default
    tags=[]
    for tag in profile.get('tags',[]):
        tag=plain_text(tag)
        if tag and len(tag)<=50 and len(tag.split())<=5 and not re.search(r'[.!?;\n]',tag) and tag.casefold() not in {t.casefold() for t in tags}:
            tags.append(tag)
    profile['tags']=tags[:8]
    for key in TEXT_FIELDS:
        if profile.get(key) is not None:
            profile[key]=plain_text(profile[key])
    return profile

def content_html(article, profile=None):
    profile=profile or seo_profile(article)
    md=MarkdownIt('commonmark',{'html':False}).enable('table')
    soup=BeautifulSoup(md.render(article.lead+'\n\n'+article.content),'html.parser')
    for h in soup.find_all('h1'): h.name='h2'
    for link in soup.find_all('a',href=True):
        if urlsplit(link['href']).scheme in ('http','https'): link['rel']=['noopener']
        elif urlsplit(link['href']).scheme: del link['href']
    # Links are only added after the service checks their existing WordPress URLs.
    for entry in profile.get('verified_internal_links',[]):
        anchor=entry.get('anchor','');url=entry.get('url','')
        for node in soup.find_all(string=True):
            if node.parent.name not in ('a','code','pre') and anchor and anchor in str(node):
                before,after=str(node).split(anchor,1)
                link=soup.new_tag('a',href=url);link.string=anchor
                node.replace_with(before,link,after);break
    if profile.get('include_sources') and not any(h.get_text(strip=True).casefold()=='źródła' for h in soup.find_all(['h2','h3'])):
        sources=article.research_snapshot.get('sources',[])
        used={sid for section in getattr(article,'sections',[]) for sid in section.get('source_ids',[])}
        ranked=sorted(sources,key=lambda s:(s.get('id') in used,s.get('source_score',0)),reverse=True)
        selected=[];urls=set()
        for source in ranked:
            url=source.get('url','')
            if urlsplit(url).scheme in ('http','https') and url not in urls:
                selected.append(source);urls.add(url)
            if len(selected)==8: break
        if selected:
            h=soup.new_tag('h2');h.string='Źródła';soup.append(h)
            ul=soup.new_tag('ul')
            for source in selected:
                li=soup.new_tag('li');a=soup.new_tag('a',href=source['url'],rel='noopener')
                a.string=source.get('title') or source.get('publisher') or urlsplit(source['url']).netloc
                li.append(a);ul.append(li)
            soup.append(ul)
    return str(soup)

def wp_content_hash(post):
    raw=post.get('content',{}).get('raw')
    if raw is None: raise ValueError('WordPress edit context did not return raw content')
    return hashlib.sha256(raw.replace('\r\n','\n').replace('\r','\n').encode()).hexdigest()

def readiness(article, profile, publication=None, qa_ok=False):
    checks=[{'name':key,'status':'ok' if profile.get(key) else 'missing'} for key in ('title','slug','seo_title','meta_description','excerpt')]
    checks += [{'name':'content','status':'ok' if article.content.strip() else 'missing'},
        {'name':'approved','status':'ok' if str(article.status)=='approved' else 'blocked'},
        {'name':'current_qa','status':'ok' if qa_ok else 'blocked'},
        {'name':'canonical','status':'ok' if profile.get('canonical_url') else 'pending'},
        {'name':'category','status':'ok' if profile.get('category') in CATEGORIES else 'blocked','value':profile.get('category')},
        {'name':'tags','status':'ok','value':len(profile.get('tags',[]))},
        {'name':'featured_image','status':'ok' if profile.get('featured_image_url') or profile.get('featured_image_asset') else 'optional_missing'},
        {'name':'schema','status':'ok','value':profile['schema_type']}]
    for key,low,high in [('seo_title',50,60),('meta_description',140,160)]:
        length=len(profile.get(key,'') or '')
        checks.append({'name':key+'_length','status':'ok' if low<=length<=high else 'warning','value':length})
    return checks
