# Rola pliku: Zadania WordPress: `seo.profile` (pełny profil SEO wersji), `seo.prepare` (uzupełnienie braków
# przez LLM z zamrożonych materiałów), `wordpress.render` (HTML wpisu), `wordpress.metadata` (meta wtyczki
# SEO) i `wordpress.verify_meta` (potwierdzenie zapisanych meta). HTTP do WordPressa wykonuje Laravel.

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from ai.context import TaskContext
from app.schemas.wordpress import SEOData
from app.services.llm.base import LLMUsage
from app.services.llm.client import OpenAIClient
from app.services.wordpress.adapters import adapter_for
from app.services.wordpress.preparation import content_html, seo_profile, slugify

PREPARE_PROMPT = (
    "Przygotuj polskie metadane SEO wyłącznie na podstawie zatwierdzonego artykułu, briefu i research snapshotu. "
    "Nie dodawaj faktów ani FAQ. SEO title naturalny około 50–60 znaków, description 140–160. Tagi 3–8 krótkich nazw. "
    "Canonical null; robots true; NewsArticle dla newsów. OG/Twitter korzystają z SEO title/opisu. Nie wybieraj "
    "obrazka, użytkownika ani linków bez danych. include_sources zachowaj zgodnie z profilem, nie zmieniaj konwencji artykułu."
)


class ArticlePayload(BaseModel):
    title: str
    slug: str
    lead: str
    content: str
    meta_title: str
    meta_description: str
    article_type: str
    seo_data: dict[str, Any] = {}
    brief: dict[str, Any] = {}
    sections: list[dict[str, Any]] = []
    research_snapshot: dict[str, Any] = {}


class ProfileInput(BaseModel):
    article: ArticlePayload
    overrides: dict[str, Any] = {}


class RenderInput(BaseModel):
    article: ArticlePayload
    profile: dict[str, Any]


class MetadataInput(BaseModel):
    profile: dict[str, Any]
    capabilities: dict[str, Any]
    seo_plugin: str


class VerifyInput(BaseModel):
    metadata: dict[str, Any]
    post: dict[str, Any]
    seo_plugin: str


class PreparedSEO(SEOData):
    seo_title: str
    meta_description: str
    slug: str


@dataclass
class PreparedResult:
    output: PreparedSEO
    usage: LLMUsage


def _article(payload: ArticlePayload) -> SimpleNamespace:
    return SimpleNamespace(**payload.model_dump())


async def profile(data: dict, ctx: TaskContext) -> dict:
    payload = ProfileInput.model_validate(data)
    return {"profile": seo_profile(_article(payload.article), payload.overrides)}


async def prepare(data: dict, ctx: TaskContext) -> dict:
    payload = ProfileInput.model_validate(data)
    article = _article(payload.article)
    current = seo_profile(article, payload.overrides)
    if ctx.demo or (all(current.get(k) for k in ("seo_title", "meta_description", "slug", "focus_keyword")) and current.get("tags")):
        return {"profile": current}
    llm = OpenAIClient(ctx.settings.openai_api_key, ctx.settings.llm_timeout_seconds, max_retries=0)
    snapshot = article.research_snapshot or {}

    async def generate():
        output, usage = await llm.parse(ctx.settings.writer_model, PREPARE_PROMPT, json.dumps({
            "article": {"title": article.title, "lead": article.lead, "content": article.content},
            "brief": article.brief, "profile": current,
            "research": {"facts": snapshot.get("facts", []),
                         "sources": [{k: s.get(k) for k in ("id", "url", "title", "publisher")} for s in snapshot.get("sources", [])]},
        }, ensure_ascii=False), PreparedSEO)
        return PreparedResult(output, usage)

    try:
        result = await ctx.call("preparing_seo", generate)
    finally:
        await llm._client.close()
    generated = merge_prepared(current, result.output.model_dump())
    generated["slug"] = slugify(generated["slug"])
    generated["canonical_url"] = current.get("canonical_url")
    return {"profile": seo_profile(article, generated)}


# Fields the model may only fill as text; publishing decisions (image, author, links, indexing) stay with the user.
USER_ONLY_FIELDS = ("featured_image_url", "featured_image_asset", "author_id", "internal_links", "robots_index", "robots_follow",
                    "include_sources", "canonical_url")


def merge_prepared(current: dict, generated: dict) -> dict:
    merged = dict(generated)
    for key, value in current.items():
        if value is not None and value != "" and value != []:
            merged[key] = value
    for key in USER_ONLY_FIELDS:
        if key in current or key in merged:
            merged[key] = current.get(key)
    return merged


async def render(data: dict, ctx: TaskContext) -> dict:
    payload = RenderInput.model_validate(data)
    resolved = {**payload.profile, "slug": slugify(payload.profile.get("slug") or payload.article.slug)}
    return {"html": content_html(_article(payload.article), resolved), "slug": resolved["slug"]}


async def metadata(data: dict, ctx: TaskContext) -> dict:
    payload = MetadataInput.model_validate(data)
    meta, warnings = adapter_for(payload.seo_plugin).metadata(payload.profile, payload.capabilities)
    return {"metadata": meta, "warnings": warnings}


async def verify_meta(data: dict, ctx: TaskContext) -> dict:
    payload = VerifyInput.model_validate(data)
    return {"warnings": adapter_for(payload.seo_plugin).verify(payload.metadata, payload.post)}
