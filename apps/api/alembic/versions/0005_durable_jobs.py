"""Trwała kolejka i historia prób; istniejące wyniki pozostają dostępne."""
# Rola pliku: Migracja tabel kolejki i nullable powiązań wyników z zadaniami.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = '0005_durable_jobs'
down_revision = '0004_classification_usage'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('job_batches',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('candidate_ids', pg.JSONB(), nullable=False),
        sa.Column('skipped_ids', pg.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table('jobs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('payload', pg.JSONB(), nullable=False),
        sa.Column('idempotency_key', sa.Uuid(), nullable=False, unique=True),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('stage', sa.String(50)),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('worker_id', sa.String(200)), sa.Column('lease_token', sa.Uuid()),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True)), sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)), sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.Column('result_type', sa.String(30)), sa.Column('result_id', sa.Integer()),
        sa.Column('error_code', sa.String(50)), sa.Column('error_message', sa.Text()),
        sa.Column('retry_of_job_id', sa.Uuid(), sa.ForeignKey('jobs.id')),
        sa.Column('checkpoints', pg.JSONB(), nullable=False),
        sa.CheckConstraint("kind IN ('classify','research','write')", name='ck_jobs_kind'),
        sa.CheckConstraint("status IN ('queued','running','retrying','succeeded','failed')", name='ck_jobs_status'),
    )
    op.create_index('uq_jobs_active_candidate', 'jobs', ['candidate_id'], unique=True,
                    postgresql_where=sa.text("status IN ('queued','running','retrying')"))
    op.create_index('ix_jobs_ready', 'jobs', ['available_at', 'created_at', 'id'],
                    postgresql_where=sa.text("status IN ('queued','retrying')"))
    op.create_index('ix_jobs_expired', 'jobs', ['locked_until'], postgresql_where=sa.text("status='running'"))
    op.create_index('ix_jobs_candidate_history', 'jobs', ['candidate_id', 'created_at'])
    op.create_table('job_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Uuid(), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False), sa.Column('worker_id', sa.String(200), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True)), sa.Column('outcome', sa.String(30), nullable=False),
        sa.Column('error_code', sa.String(50)), sa.Column('error_message', sa.Text()),
        sa.Column('last_stage', sa.String(50)), sa.Column('llm_calls', pg.JSONB(), nullable=False),
        sa.UniqueConstraint('job_id', 'number', name='uq_job_attempt_number'),
    )
    op.create_index('ix_job_attempts_job_id', 'job_attempts', ['job_id'])
    for table, field in [('candidates', 'classification_job_id'), ('researches', 'job_id'), ('articles', 'generation_job_id')]:
        op.add_column(table, sa.Column(field, sa.Uuid(), nullable=True))
        singular = {'candidates': 'candidate', 'researches': 'research', 'articles': 'article'}[table]
        op.create_foreign_key(f'fk_{singular}_{field}', table, 'jobs', [field], ['id'], ondelete='SET NULL')
    op.create_unique_constraint('uq_articles_generation_job_id', 'articles', ['generation_job_id'])
    # Jednorazowo zamykamy raporty pozostawione przez poprzedni mechanizm.
    op.execute("UPDATE researches SET status='failed', error='Interrupted during queue migration', completed_at=now() WHERE status='running' AND job_id IS NULL")


def downgrade() -> None:
    for table, field in [('articles', 'generation_job_id'), ('researches', 'job_id'), ('candidates', 'classification_job_id')]:
        op.drop_column(table, field)
    op.drop_table('job_attempts')
    op.drop_table('jobs')
    op.drop_table('job_batches')
