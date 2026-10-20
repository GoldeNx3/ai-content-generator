"""Approved version -> idempotent WordPress draft/update -> SEO -> verified status."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes
import httpx
from app.core.config import get_settings
from app.schemas.wordpress import PublishRequest, SEOData
from app.services.article.versions import content_hash
from app.services.wordpress.api_helpers import approved_version,publication_for
from app.services.wordpress.preparation import seo_profile,content_html,wp_content_hash,CATEGORIES,slugify
from app.services.wordpress.adapters import adapter_for
from app.services.wordpress.errors import WordPressError
from app.services.jobs.errors import JobInputError
from app.services.research.public_http import PublicHTTPTransport

class WordPressPublisherService:
    def __init__(self,session,client,execution=None,settings=None):
        self.session,self.client,self.execution=session,client,execution
        self.settings=settings or get_settings()
    async def save(self,publication,checkpoint=None,complete=False):
        if self.execution:
            await self.execution.commit(self.session,result=publication if complete else None,checkpoint=checkpoint)
        else:await self.session.commit()
    def cached(self,key):return self.execution.checkpoints.get(key) if self.execution else None
    async def prepare(self,article_version_id,profile=None):
        article=await approved_version(self.session,article_version_id,self.settings,lock=True)
        p=await publication_for(self.session,article,True)
        # A new version starts with its own generated SEO, not the old version's copy.
        previous=p.profile if p.profile.get('version_id',article.id)==article.id else {}
        p.profile={**seo_profile(article,previous),**(profile or {}),'version_id':article.id}
        await self.save(p)
        return p
    async def taxonomy(self,profile):
        category=profile['category']
        if category not in CATEGORIES:raise JobInputError('Kategoria nie należy do dozwolonej listy.',422)
        if self.settings.wordpress_default_category_id and not profile.get('category_override'):
            category_id=self.settings.wordpress_default_category_id
        else:
            term=await self.client.find_category(category)
            try:term=term or await self.client.create_category(category)
            except WordPressError as exc:
                if exc.code!='wordpress_http_400':raise
                term=await self.client.find_category(category)
                if not term:raise
            category_id=term['id']
        tags=[]
        for name in profile.get('tags',[]):
            term=await self.client.find_tag(name)
            try:term=term or await self.client.create_tag(name)
            except WordPressError as exc:
                if exc.code!='wordpress_http_400':raise
                term=await self.client.find_tag(name)
                if not term:raise
            tags.append(term['id'])
        return [category_id],tags
    async def media(self,p,profile):
        image=profile.get('featured_image_url') or profile.get('featured_image_asset')
        if not image:return p.media_id
        fingerprint=sha256(image.encode()).hexdigest()
        if p.media_id and p.media_fingerprint==fingerprint:return p.media_id
        if profile.get('featured_image_asset'):
            root=Path(self.settings.wordpress_asset_root).resolve();path=(root/image).resolve()
            if not path.is_relative_to(root) or not path.is_file():raise JobInputError('Nieprawidłowy lokalny asset obrazka.',422)
            data=path.read_bytes();mime=mimetypes.guess_type(path.name)[0];filename=path.name
        else:
            async with httpx.AsyncClient(transport=PublicHTTPTransport(),follow_redirects=False,timeout=20) as http:
                async with http.stream('GET',image) as response:
                    response.raise_for_status();data=bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data)>self.settings.wordpress_max_image_bytes:raise JobInputError('Obraz przekracza limit rozmiaru.',422)
                    mime=response.headers.get('Content-Type','').split(';')[0]
            filename='featured'+(mimetypes.guess_extension(mime) or '')
        if mime not in ('image/jpeg','image/png','image/webp','image/gif') or len(data)>self.settings.wordpress_max_image_bytes:
            raise JobInputError('Nieobsługiwany format lub rozmiar obrazka.',422)
        # Remote Bridge deduplicates uploads by content hash via the HTTP header.
        media=await self.client.upload_media(bytes(data),filename,mime)
        p.media_id=media['id'];p.media_fingerprint=fingerprint
        await self.save(p,{'wp_media':p.media_id})
        return p.media_id
    async def publish(self,article_version_id:int,target_status:str='draft',scheduled_at:datetime|None=None):
        options=self.execution.checkpoints.get('wp_request',{}) if self.execution else {}
        request=PublishRequest.model_validate({'status':target_status,'scheduled_at':scheduled_at},context={'check_time':False})
        article=await approved_version(self.session,article_version_id,self.settings,lock=True)
        p=await publication_for(self.session,article,True)
        from app.services.article.seo import preview_seo
        resolved,_=await preview_seo(self.session,article)
        overrides=p.profile if p.profile.get('version_id',article.id)==article.id else {}
        profile=seo_profile(article,{**resolved,**overrides});profile['version_id']=article.id
        for key in ('title','slug','seo_title','meta_description'):
            if not profile.get(key):raise JobInputError(f'Brak wymaganego pola {key}. Przygotuj SEO przed wysłaniem.',422)
        if not article.content.strip():raise JobInputError('Brak treści.',422)
        if profile['slug']!=slugify(profile['slug']):
            # Legacy approved slugs are not silently rewritten; publication uses normalized slug.
            profile['slug']=slugify(profile['slug'])
        p.status='sending';p.warnings=[];p.error_code=None
        await self.save(p)
        caps=await self.client.capabilities()
        actual=caps.get('seo_plugin','none')
        if actual!=self.settings.wordpress_seo_plugin:
            raise WordPressError('wordpress_seo_plugin_mismatch')
        if not caps.get('bridge_version'):raise WordPressError('wordpress_bridge_required')
        if target_status in ('future','publish') and not caps.get('can_publish',True):raise WordPressError('wordpress_publish_forbidden')
        category_ids,tag_ids=await self.taxonomy(profile)
        media_id=await self.media(p,profile)
        author=profile.get('author_id') or self.settings.wordpress_default_author_id or caps.get('author_id')
        if author:await self.client.get_user(author)
        verified=[]
        for link in profile.get('internal_links',[]):
            url=link.get('url','')
            if urlsplit(url).netloc!=urlsplit(self.client.base).netloc:
                p.warnings=[*p.warnings,'Internal link pominięty: URL nie należy do WordPressa.'];continue
            exists=await self.client.request('GET','content-engine/v1/resolve',params={'url':url})
            if exists.get('exists'):verified.append(link)
            else:p.warnings=[*p.warnings,f'Internal link pominięty: {url}']
        profile['verified_internal_links']=verified
        html=content_html(article,profile)
        payload={'title':article.title,'slug':profile['slug'],'content':html,'excerpt':profile['excerpt'],
            'categories':category_ids,'tags':tag_ids}
        if author:payload['author']=author
        if media_id:payload['featured_media']=media_id
        identity=f'{self.settings.wordpress_instance_id}:{article.candidate_id}'
        prepared=self.cached('wp_payload')
        if prepared:
            payload=prepared['payload'];profile=prepared['profile'];media_id=prepared['media_id']
        else:
            await self.save(p,{'wp_payload':{'payload':payload,'profile':profile,'media_id':media_id}})
        operation=str(self.execution.job_id) if self.execution else sha256((identity+str(article.id)+html+str(target_status)).encode()).hexdigest()
        # Preserve initial expectations across retries after partial remote updates.
        original=self.cached('wp_original')
        current=None
        if p.wordpress_post_id and p.wordpress_instance_id!=self.settings.wordpress_instance_id:
            # Post istnieje na innej stronie (zmiana połączenia workspace'u): tutaj powstaje nowy draft.
            p.wordpress_post_id=None;p.wordpress_instance_id=None;p.last_synced_content_hash=None;p.conflict=None
            original=None
            await self.save(p,{'wp_original':None})
        if p.wordpress_post_id:
            try:current=await self.client.get_post(p.wordpress_post_id)
            except WordPressError as exc:
                if exc.code!='wordpress_http_404':raise
                # Only a confirmed missing post permits CREATE; the Bridge retires its mapping atomically.
                p.wordpress_post_id=None;p.last_synced_content_hash=None;p.conflict=None
                original=None
                await self.save(p,{'wp_original':None})
        if current is not None and current['status']=='trash':
            # A deleted publication stays in Trash; an explicit send creates a new draft.
            p.wordpress_post_id=None;p.last_synced_content_hash=None;p.conflict=None
            current=None;original=None
            await self.save(p,{'wp_original':None})
        if current is not None:
            digest=wp_content_hash(current)
            expected=original.get('expected_hash') if original else options.get('expected_wp_hash') or p.last_synced_content_hash
            allowable={expected}
            if original:allowable.add(sha256(payload['content'].replace('\r\n','\n').replace('\r','\n').encode()).hexdigest())
            if expected and digest not in allowable:
                p.conflict={'current_hash':digest,'post_id':p.wordpress_post_id};p.error_code='wordpress_conflict'
                await self.save(p)
                raise WordPressError('wordpress_conflict')
            if not original:
                original={'expected_hash':digest,'post_id':p.wordpress_post_id}
                await self.save(p,{'wp_original':original})
        # Re-check approval/QA under the same candidate lock as approval immediately before mutation.
        await approved_version(self.session,article_version_id,self.settings,lock=True)
        if not p.wordpress_post_id:
            # A replacement/recovered mapping has not completed our content,
            # SEO and status verification. An older post's sync cannot certify it.
            p.last_synced_at=None
            try:
                current=await self.client.create_post({**payload,'status':'draft'},identity=identity,operation=operation+':create')
            except WordPressError as exc:
                # The Bridge still owns the identity when a local mapping was lost.
                # Recover the link, but require explicit consent before replacing its content.
                if exc.code=='wordpress_conflict' and isinstance(exc.details,dict) and isinstance(exc.details.get('post_id'),int):
                    remote=await self.client.get_post(exc.details['post_id'])
                    p.wordpress_post_id=remote['id'];p.wp_status=remote['status'];p.wordpress_instance_id=self.settings.wordpress_instance_id
                    p.wordpress_url=remote.get('ce_permalink') or remote.get('link')
                    p.conflict={'current_hash':wp_content_hash(remote),'post_id':remote['id']}
                    p.error_code='wordpress_conflict'
                    await self.save(p)
                raise
            p.wordpress_post_id=current['id'];p.wp_status=current['status'];p.wordpress_instance_id=self.settings.wordpress_instance_id
            p.wordpress_url=current.get('ce_permalink') or current['link']
            await self.save(p,{'wp_created':p.wordpress_post_id})
        else:
            content_payload=self.cached('wp_content_payload')
            if content_payload is None:
                content_payload=payload
                await self.save(p,{'wp_content_payload':content_payload})
            current=await self.client.update_post(p.wordpress_post_id,content_payload,identity=identity,
                operation=operation+':content',expected_hash=original['expected_hash'] if original else None)
            await self.save(p,{'wp_content_written':True})
        # The permalink is resolved by WP, including slug collision resolution.
        profile['slug']=current['slug'];profile['canonical_url']=current.get('ce_permalink') or current['link']
        if not profile['canonical_url']:raise WordPressError('wordpress_permalink_missing')
        adapter=adapter_for(self.settings.wordpress_seo_plugin)
        metadata,warnings=adapter.metadata(profile,caps)
        p.warnings=list(dict.fromkeys([*p.warnings,*warnings]))
        expected=wp_content_hash(current)
        await approved_version(self.session,article_version_id,self.settings,lock=True)
        current=await self.client.update_post(p.wordpress_post_id,{'meta':metadata},identity=identity,
            operation=operation+':seo',expected_hash=expected)
        p.profile=profile;p.wordpress_url=profile['canonical_url']
        await self.save(p,{'wp_seo_written':True})
        verify=await self.client.get_post(p.wordpress_post_id)
        self.verify(verify,payload,profile,media_id)
        p.warnings=list(dict.fromkeys([*p.warnings,*adapter.verify(metadata,verify)]))
        # Explicit status change only after content/SEO preparation and verification.
        await approved_version(self.session,article_version_id,self.settings,lock=True)
        final={'status':target_status}
        effective_status=target_status
        if target_status=='future' and request.scheduled_at<=datetime.now(timezone.utc):
            recovered=await self.client.operation(operation+':status')
            if not recovered.get('exists'):
                raise WordPressError('wordpress_schedule_elapsed')
            remote=await self.client.get_post(p.wordpress_post_id)
            if remote['status'] not in ('future','publish'):raise WordPressError('wordpress_schedule_changed')
            effective_status=remote['status']
            final=None
        if target_status=='future' and final is not None:final['date_gmt']=request.scheduled_at.strftime('%Y-%m-%dT%H:%M:%S')
        if final is not None:
            await self.client.update_post(p.wordpress_post_id,final,identity=identity,
                operation=operation+':status',expected_hash=wp_content_hash(verify))
        await self.save(p,{'wp_status_sent':True})
        verify=await self.client.get_post(p.wordpress_post_id)
        self.verify(verify,payload,profile,media_id,effective_status)
        p.article_version_id=article.id;p.title=article.title;p.slug=profile['slug']
        p.wp_status=verify['status'];p.status={'draft':'draft_created','future':'scheduled','publish':'published'}[effective_status]
        p.scheduled_at=request.scheduled_at;p.published_at=datetime.now(timezone.utc) if effective_status=='publish' else None
        p.last_synced_at=datetime.now(timezone.utc);p.last_synced_content_hash=wp_content_hash(verify)
        p.error_code=None;p.conflict=None
        # Confirm the topic only after the remote content and final status were
        # verified. Persist the decision together with the fenced job result.
        from sqlalchemy import select
        from app.models import Candidate, CandidateStatus
        if self.execution:
            await self.execution.lock(self.session)
        with self.session.no_autoflush:
            candidate=await self.session.scalar(select(Candidate).where(Candidate.id==article.candidate_id)
                .with_for_update(of=Candidate).execution_options(populate_existing=True))
        candidate.status=CandidateStatus.APPROVED
        await self.save(p,complete=True)
        return p
    @staticmethod
    def verify(post,payload,profile,media_id,status=None):
        from html import unescape
        title=post.get('title',{}).get('raw',post.get('title',{}).get('rendered',''))
        content_matches=wp_content_hash(post)==sha256(payload['content'].replace('\r\n','\n').replace('\r','\n').encode()).hexdigest()
        taxonomy_matches=all(set(post.get(key,[]))==set(payload[key]) for key in ('categories','tags'))
        author_matches=not payload.get('author') or post.get('author')==payload['author']
        if not content_matches or not taxonomy_matches or not author_matches or unescape(title)!=payload['title'] or post.get('slug')!=profile['slug'] or (status and post.get('status')!=status) or (media_id and post.get('featured_media')!=media_id):
            raise WordPressError('wordpress_verification_failed')
