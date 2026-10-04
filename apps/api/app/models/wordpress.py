from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
from app.models.mixins import TimestampMixin

class WordPressPublication(TimestampMixin, Base):
    __tablename__='wordpress_publications'
    __table_args__=(CheckConstraint("status IN ('not_sent','queued','sending','draft_created','scheduled','published','failed')",name='ck_wp_publication_status'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    candidate_id: Mapped[int]=mapped_column(ForeignKey('candidates.id',ondelete='RESTRICT'),unique=True)
    article_version_id: Mapped[int]=mapped_column(ForeignKey('articles.id',ondelete='RESTRICT'))
    job_id: Mapped[UUID | None]=mapped_column(ForeignKey('jobs.id',ondelete='SET NULL'))
    wordpress_post_id: Mapped[int | None]=mapped_column(Integer,unique=True)
    wordpress_url: Mapped[str | None]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default='not_sent')
    wp_status: Mapped[str | None]=mapped_column(String(20))
    title: Mapped[str]=mapped_column(String(300),default='')
    slug: Mapped[str]=mapped_column(String(300),default='')
    scheduled_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    last_synced_content_hash: Mapped[str | None]=mapped_column(String(64))
    media_id: Mapped[int | None]=mapped_column(Integer)
    media_fingerprint: Mapped[str | None]=mapped_column(String(64))
    profile: Mapped[dict]=mapped_column(JSONB,default=dict)
    warnings: Mapped[list]=mapped_column(JSONB,default=list)
    conflict: Mapped[dict | None]=mapped_column(JSONB)
    error_code: Mapped[str | None]=mapped_column(String(60))
