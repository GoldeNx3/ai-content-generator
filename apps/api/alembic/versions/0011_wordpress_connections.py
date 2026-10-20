"""WordPress connection per workspace (encrypted app password) and authorize-application requests.

Publication post IDs become unique per WP instance; existing publications get the instance from
WORDPRESS_INSTANCE_ID (the global .env config), so `make wordpress-import-env` keeps them linked.
"""
from alembic import op
import sqlalchemy as sa
revision='0011_wordpress_connections'
down_revision='0010_workspace_scope'
branch_labels=None
depends_on=None


def upgrade():
    from app.core.config import get_settings
    from app.models.wordpress import WordPressAuthRequest, WordPressConnection
    bind = op.get_bind()
    WordPressConnection.__table__.create(bind)
    WordPressAuthRequest.__table__.create(bind)
    op.add_column('wordpress_publications', sa.Column('wordpress_instance_id', sa.String(100)))
    bind.execute(sa.text('UPDATE wordpress_publications SET wordpress_instance_id = :instance '
                         'WHERE wordpress_post_id IS NOT NULL'), {'instance': get_settings().wordpress_instance_id})
    op.drop_constraint('wordpress_publications_wordpress_post_id_key', 'wordpress_publications', type_='unique')
    op.create_unique_constraint('uq_wp_publication_instance_post', 'wordpress_publications',
                                ['wordpress_instance_id', 'wordpress_post_id'])


def downgrade():
    raise RuntimeError('WordPress connections hold credentials and publication links; use a reviewed forward migration.')
