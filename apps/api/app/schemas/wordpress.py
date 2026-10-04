from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict, ValidationInfo

class InternalLink(BaseModel):
    anchor: str
    url: str

class FAQEntry(BaseModel):
    question: str
    answer: str

class HowToStep(BaseModel):
    name: str
    text: str

class SEOData(BaseModel):
    excerpt: str = ''
    canonical_url: str | None = None
    focus_keyword: str = ''
    secondary_keywords: list[str] = Field(default_factory=list)
    og_title: str = ''
    og_description: str = ''
    twitter_title: str = ''
    twitter_description: str = ''
    robots_index: bool = True
    robots_follow: bool = True
    schema_type: Literal['Article','NewsArticle','TechArticle','HowTo','FAQPage'] = 'Article'
    category: Literal['AI','Modele AI','Programowanie','Narzędzia AI','Automatyzacja','Biznes','Newsy','Poradniki','Porównania'] | None = None
    tags: list[str] = Field(default_factory=list, max_length=8)
    author_id: int | None = Field(default=None, gt=0)
    featured_image_url: str | None = None
    featured_image_asset: str | None = None
    internal_links: list[InternalLink] = Field(default_factory=list)
    faq: list[FAQEntry] = Field(default_factory=list)
    howto_steps: list[HowToStep] = Field(default_factory=list)
    include_sources: bool = False

class PublishRequest(BaseModel):
    status: Literal['draft','future','publish'] = 'draft'
    scheduled_at: datetime | None = None
    expected_wp_hash: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    @model_validator(mode='after')
    def schedule(self, info:ValidationInfo):
        if self.status=='future':
            if not self.scheduled_at or self.scheduled_at.utcoffset() is None:
                raise ValueError('Schedule requires a datetime with timezone.')
            if (info.context or {}).get('check_time',True) and self.scheduled_at <= datetime.now(timezone.utc):
                raise ValueError('Scheduled date must be in the future.')
            self.scheduled_at=self.scheduled_at.astimezone(timezone.utc)
        elif self.scheduled_at:
            raise ValueError('scheduled_at is only valid for future status.')
        return self

class SyncRequest(BaseModel):
    status: Literal['draft','future','publish'] | None = None
    scheduled_at: datetime | None = None
    expected_wp_hash: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

class PublicationRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    article_version_id: int
    candidate_id: int
    wordpress_post_id: int | None
    wordpress_url: str | None
    status: str
    wp_status: str | None
    title: str
    slug: str
    scheduled_at: datetime | None
    published_at: datetime | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_synced_content_hash: str | None
    media_id: int | None
    warnings: list[str]
    profile: dict
    error_code: str | None
