"""Version-owned SEO and durable WordPress publication state."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0008_wordpress'
down_revision='0007_auto_fix_approval'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('articles',sa.Column('seo_data',JSONB(),nullable=False,server_default='{}'))
    from app.models.wordpress import WordPressPublication
    WordPressPublication.__table__.create(op.get_bind())
    op.drop_constraint('ck_jobs_kind','jobs',type_='check')
    op.create_check_constraint('ck_jobs_kind','jobs',"kind IN ('classify','research','write','qa_article','auto_fix_article','prepare_wordpress','publish_wordpress')")

def downgrade():
    raise RuntimeError('Publication history must not be silently discarded; use a reviewed forward migration.')
