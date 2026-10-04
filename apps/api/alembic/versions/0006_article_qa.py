"""Durable article quality assurance."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006_article_qa'
down_revision = '0005_durable_jobs'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('articles', sa.Column('qa_passed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('jobs', sa.Column('article_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_jobs_article', 'jobs', 'articles', ['article_id'], ['id'], ondelete='RESTRICT')
    op.drop_constraint('ck_jobs_kind', 'jobs', type_='check')
    op.create_check_constraint('ck_jobs_kind', 'jobs', "kind IN ('classify','research','write','qa_article')")
    op.create_table('article_qas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('article_version', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Uuid(), sa.ForeignKey('jobs.id', ondelete='SET NULL'), unique=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('input_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('claims', postgresql.JSONB(), nullable=False),
        *[sa.Column(name, sa.Integer()) for name in
          ('overall_score','factual_score','source_score','style_score','structure_score','seo_score')],
        *[sa.Column(name, sa.Integer(), nullable=False) for name in
          ('supported_claims_count','unsupported_claims_count','critical_issue_count','warning_count')],
        sa.Column('summary', sa.Text()), sa.Column('llm_model', sa.String(100)),
        sa.Column('llm_input_tokens', sa.Integer()), sa.Column('llm_output_tokens', sa.Integer()),
        sa.Column('estimated_cost_usd', sa.Numeric(12,6)),
        sa.Column('qa_passed', sa.Boolean(), nullable=False), sa.Column('pass_score', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending','running','completed','failed')", name='ck_article_qa_status'))
    op.create_index('ix_article_qas_article_id', 'article_qas', ['article_id'])
    op.create_table('article_qa_issues',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_qa_id', sa.Integer(), sa.ForeignKey('article_qas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(40), nullable=False), sa.Column('severity', sa.String(20), nullable=False),
        *[sa.Column(name, sa.Text(), nullable=False) for name in ('excerpt','reason','suggestion')],
        sa.Column('section_heading', sa.Text()),
        sa.Column('fact_ids', postgresql.JSONB(), nullable=False),
        sa.Column('source_ids', postgresql.JSONB(), nullable=False),
        sa.Column('auto_fixable', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('info','warning','high','critical')", name='ck_qa_issue_severity'))
    op.create_index('ix_article_qa_issues_article_qa_id', 'article_qa_issues', ['article_qa_id'])


def downgrade():
    op.drop_table('article_qa_issues')
    op.drop_table('article_qas')
    op.execute("DELETE FROM job_attempts WHERE job_id IN (SELECT id FROM jobs WHERE kind='qa_article')")
    op.execute("UPDATE jobs SET retry_of_job_id=NULL WHERE retry_of_job_id IN (SELECT id FROM jobs WHERE kind='qa_article')")
    op.execute("DELETE FROM jobs WHERE kind='qa_article'")
    op.drop_constraint('ck_jobs_kind', 'jobs', type_='check')
    op.create_check_constraint('ck_jobs_kind', 'jobs', "kind IN ('classify','research','write')")
    op.drop_constraint('fk_jobs_article', 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'article_id')
    op.drop_column('articles', 'qa_passed')
