"""Version-owned SEO with a read-only legacy view of already prepared metadata."""
from sqlalchemy import select
from app.models import Article,WordPressPublication
from app.schemas.wordpress import SEOData
from app.services.wordpress.preparation import seo_profile,plain

async def preview_seo(session, article):
    publication=await session.scalar(select(WordPressPublication).where(WordPressPublication.candidate_id==article.candidate_id))
    profile=None;ancestor=article;seen=set()
    while publication and ancestor and ancestor.id not in seen:
        seen.add(ancestor.id)
        if publication.profile.get('version_id')==ancestor.id:
            profile=publication.profile;break
        # New generation has its own SEO and never inherits a separate generation's profile.
        if ancestor.created_by in ('generated','regenerated','legacy'):break
        ancestor=await session.get(Article,ancestor.parent_version_id) if ancestor.parent_version_id else None
        if ancestor and ancestor.candidate_id!=article.candidate_id:break
    raw=article.seo_data or {}
    missing=not all(raw.get(k) for k in ('excerpt','focus_keyword','secondary_keywords','tags','category','schema_type'))
    overrides={k:v for k,v in (profile or {}).items() if k in SEOData.model_fields} if missing else {}
    if profile and profile.get('version_id')!=article.id:
        # Metadata attached to edited prose uses current text, not an obsolete excerpt/title.
        overrides.update(excerpt=plain(article.lead),canonical_url=None,og_title=article.meta_title,
            og_description=article.meta_description,twitter_title=article.meta_title,twitter_description=article.meta_description)
    for k,v in raw.items():
        if v is not None and v!='' and v!=[]:overrides[k]=v
    resolved=seo_profile(article,overrides)
    origin='publication_profile' if missing and profile else 'article' if raw else 'fallback'
    return {k:resolved[k] for k in SEOData.model_fields},origin
