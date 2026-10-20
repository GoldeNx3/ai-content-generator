"""Scope sources, candidates, jobs and job batches to a workspace.

Existing rows go to the oldest workspace; when data exists but no workspace does (fresh production),
a "Domyślny" workspace is created. `make create-user EMAIL=... WORKSPACE=<id>` attaches an account to it.
"""
from alembic import op
import sqlalchemy as sa
revision='0010_workspace_scope'
down_revision='0009_auth'
branch_labels=None
depends_on=None

TABLES = ('sources', 'candidates', 'jobs', 'job_batches')


def upgrade():
    bind = op.get_bind()
    for table in TABLES:
        op.add_column(table, sa.Column('workspace_id', sa.Integer(), nullable=True))

    has_data = any(bind.scalar(sa.text(f'SELECT EXISTS (SELECT 1 FROM {table})')) for table in TABLES)
    workspace_id = bind.scalar(sa.text('SELECT id FROM workspaces ORDER BY created_at, id LIMIT 1'))
    if has_data and workspace_id is None:
        workspace_id = bind.scalar(sa.text("INSERT INTO workspaces (name) VALUES ('Domyślny') RETURNING id"))
    if workspace_id is not None:
        for table in TABLES:
            bind.execute(sa.text(f'UPDATE {table} SET workspace_id = :ws'), {'ws': workspace_id})

    for table in TABLES:
        op.alter_column(table, 'workspace_id', nullable=False)

    # sources: URL unikalny w workspace; (id, workspace_id) jako cel złożonego FK.
    op.create_foreign_key('fk_sources_workspace', 'sources', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('sources_url_key', 'sources', type_='unique')
    op.create_unique_constraint('uq_sources_workspace_url', 'sources', ['workspace_id', 'url'])
    op.create_unique_constraint('uq_sources_id_workspace', 'sources', ['id', 'workspace_id'])

    # candidates: workspace zgodny ze źródłem, URL unikalny w workspace.
    op.create_foreign_key('fk_candidates_workspace', 'candidates', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('candidates_source_id_fkey', 'candidates', type_='foreignkey')
    op.create_foreign_key('fk_candidates_source_workspace', 'candidates', 'sources',
                          ['source_id', 'workspace_id'], ['id', 'workspace_id'], ondelete='CASCADE')
    op.drop_constraint('candidates_external_url_key', 'candidates', type_='unique')
    op.create_unique_constraint('uq_candidates_workspace_url', 'candidates', ['workspace_id', 'external_url'])
    op.create_unique_constraint('uq_candidates_id_workspace', 'candidates', ['id', 'workspace_id'])
    op.create_index('ix_candidates_workspace_created', 'candidates', ['workspace_id', 'created_at'])

    # jobs: workspace zgodny z kandydatem.
    op.create_foreign_key('fk_jobs_workspace', 'jobs', 'workspaces', ['workspace_id'], ['id'], ondelete='RESTRICT')
    op.drop_constraint('jobs_candidate_id_fkey', 'jobs', type_='foreignkey')
    op.create_foreign_key('fk_jobs_candidate_workspace', 'jobs', 'candidates',
                          ['candidate_id', 'workspace_id'], ['id', 'workspace_id'], ondelete='RESTRICT')
    op.create_index('ix_jobs_workspace_created', 'jobs', ['workspace_id', 'created_at'])

    op.create_foreign_key('fk_job_batches_workspace', 'job_batches', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')


def downgrade():
    raise RuntimeError('Workspace ownership must not be silently discarded; use a reviewed forward migration.')
