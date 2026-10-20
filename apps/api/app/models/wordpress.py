from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, CheckConstraint, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
from app.models.mixins import TimestampMixin

class WordPressPublication(TimestampMixin, Base):
    __tablename__='wordpress_publications'
    # ID posta jest unikalne tylko w obrębie jednej instalacji WP (instancji połączenia workspace'u).
    __table_args__=(CheckConstraint("status IN ('not_sent','queued','sending','draft_created','scheduled','published','failed')",name='ck_wp_publication_status'),
                    UniqueConstraint('wordpress_instance_id','wordpress_post_id',name='uq_wp_publication_instance_post'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    candidate_id: Mapped[int]=mapped_column(ForeignKey('candidates.id',ondelete='RESTRICT'),unique=True)
    article_version_id: Mapped[int]=mapped_column(ForeignKey('articles.id',ondelete='RESTRICT'))
    job_id: Mapped[UUID | None]=mapped_column(ForeignKey('jobs.id',ondelete='SET NULL'))
    wordpress_post_id: Mapped[int | None]=mapped_column(Integer)
    # Instancja (połączenie), w której istnieje wordpress_post_id; zmiana strony odpina publikację.
    wordpress_instance_id: Mapped[str | None]=mapped_column(String(100))
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


class WordPressConnection(TimestampMixin, Base):
    """Jedna strona WordPress na workspace. Hasło aplikacji zaszyfrowane (app/core/secrets.py)."""
    __tablename__='wordpress_connections'
    __table_args__=(CheckConstraint("seo_plugin IN ('yoast','rankmath','none')",name='ck_wp_connection_seo'),
                    CheckConstraint("default_status IN ('draft','future','publish')",name='ck_wp_connection_status'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    workspace_id: Mapped[int]=mapped_column(ForeignKey('workspaces.id',ondelete='CASCADE'),unique=True)
    site_url: Mapped[str]=mapped_column(String(2048))
    # Opcjonalny adres wewnętrzny (np. sieć Dockera); Host pozostaje z site_url.
    api_url: Mapped[str | None]=mapped_column(String(2048))
    username: Mapped[str]=mapped_column(String(200))
    app_password_encrypted: Mapped[str]=mapped_column(Text)
    # Tożsamość instance:candidate w Bridge; stała dla tej strony, nowa po zmianie strony.
    instance_id: Mapped[str]=mapped_column(String(100),unique=True)
    seo_plugin: Mapped[str]=mapped_column(String(20),default='none')
    default_status: Mapped[str]=mapped_column(String(20),default='draft')
    default_author_id: Mapped[int | None]=mapped_column(Integer)
    default_category_id: Mapped[int | None]=mapped_column(Integer)
    wp_user_id: Mapped[int | None]=mapped_column(Integer)
    wp_user_name: Mapped[str | None]=mapped_column(String(200))
    can_publish: Mapped[bool]=mapped_column(Boolean,default=False)
    last_checked_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None]=mapped_column(String(60))


class WordPressAuthRequest(Base):
    """Oczekująca autoryzacja aplikacji w WP: state (tylko hash) wiąże powrót z workspace'em i stroną."""
    __tablename__='wordpress_auth_requests'
    id: Mapped[int]=mapped_column(primary_key=True)
    state_hash: Mapped[str]=mapped_column(String(64),unique=True)
    workspace_id: Mapped[int]=mapped_column(ForeignKey('workspaces.id',ondelete='CASCADE'),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
    site_url: Mapped[str]=mapped_column(String(2048))
    api_url: Mapped[str | None]=mapped_column(String(2048))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
