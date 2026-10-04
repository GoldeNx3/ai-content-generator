"""WordPress jobs use the same lease fencing and paid-call checkpoints as editorial jobs."""
import json
from dataclasses import dataclass
from datetime import datetime
from app.core.config import get_settings
from app.schemas.wordpress import SEOData
from app.services.llm.base import LLMUsage
from app.services.llm.client import OpenAIClient
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.service import WordPressPublisherService
from app.services.wordpress.preparation import seo_profile,slugify
from app.services.wordpress.api_helpers import approved_version,publication_for

class PreparedSEO(SEOData):
    seo_title: str
    meta_description: str
    slug: str

@dataclass
class PreparedResult:
    output: PreparedSEO
    usage: LLMUsage

async def prepare_profile(article,profile,recorder,settings):
    """Fill missing SEO from frozen evidence; preserve all approved QA-covered values."""
    if all(profile.get(key) for key in ('seo_title','meta_description','slug','focus_keyword')) and profile.get('tags'):
        return profile
    llm=OpenAIClient(settings.openai_api_key,settings.llm_timeout_seconds,max_retries=0)
    async def generate():
        output,usage=await llm.parse(settings.writer_model,
            'Przygotuj polskie metadane SEO wyłącznie na podstawie zatwierdzonego artykułu, briefu i research snapshotu. Nie dodawaj faktów ani FAQ. SEO title naturalny około 50–60 znaków, description 140–160. Tagi 3–8 krótkich nazw. Canonical null; robots true; NewsArticle dla newsów. OG/Twitter korzystają z SEO title/opisu. Nie wybieraj obrazka, użytkownika ani linków bez danych. include_sources zachowaj zgodnie z profilem, nie zmieniaj konwencji artykułu.',
            json.dumps({'article':{'title':article.title,'lead':article.lead,'content':article.content},'brief':article.brief,'profile':profile,
                'research':{'facts':article.research_snapshot.get('facts',[]),'sources':[{k:s.get(k) for k in ('id','url','title','publisher')} for s in article.research_snapshot.get('sources',[])]}},ensure_ascii=False),PreparedSEO)
        return PreparedResult(output,usage)
    try:result=await recorder.call('preparing_seo',generate,PreparedResult)
    finally:await llm._client.close()
    generated=result.output.model_dump()
    # Every existing value is approved or explicitly chosen by the user. Generate only gaps.
    for key,value in profile.items():
        if value is not None and value != '' and value != []:
            generated[key]=value
    generated['slug']=slugify(generated['slug']);generated['canonical_url']=profile.get('canonical_url')
    return seo_profile(article,generated)

async def handle(job,session,execution,providers,recorder,settings):
    environment=get_settings()
    client=WordPressClient(environment)
    service=WordPressPublisherService(session,client,execution,environment)
    try:
        article=await approved_version(session,job.article_id,settings)
        publication=await publication_for(session,article)
        overrides=publication.profile if publication and publication.profile.get('version_id',article.id)==article.id else {}
        from app.services.article.seo import preview_seo
        resolved,_=await preview_seo(session,article)
        profile=seo_profile(article,{**resolved,**overrides})
        if job.kind=='prepare_wordpress' or not all(profile.get(k) for k in ('seo_title','meta_description','slug','excerpt','og_title','og_description')):
            profile=await prepare_profile(article,profile,recorder,settings)
            publication=await service.prepare(article.id,profile)
            if job.kind=='prepare_wordpress':
                publication.status='draft_created' if publication.wordpress_post_id and publication.wp_status=='draft' else 'scheduled' if publication.wp_status=='future' else 'published' if publication.wp_status=='publish' else 'not_sent'
                await execution.commit(session,result=publication)
                return
        options=job.payload['options']
        await execution.checkpoint('wp_request',options)
        scheduled=datetime.fromisoformat(options['scheduled_at']) if options.get('scheduled_at') else None
        await execution.stage('publishing_wordpress')
        await service.publish(job.article_id,options['status'],scheduled)
    finally:await client.close()
