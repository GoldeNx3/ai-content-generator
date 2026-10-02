"""articles

Revision ID: 0003_articles
Revises: 0002_research
Create Date: 2026-10-02 21:46:33.975111

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0003_articles'
down_revision: str | None = '0002_research'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('research_id', sa.Integer(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'review', 'approved', 'rejected', name='article_status'), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('slug', sa.String(length=300), nullable=False),
    sa.Column('lead', sa.Text(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('generated_content', sa.Text(), nullable=False),
    sa.Column('meta_title', sa.String(length=300), nullable=False),
    sa.Column('meta_description', sa.String(length=500), nullable=False),
    sa.Column('article_type', postgresql.ENUM('news', 'guide', 'comparison', 'pricing', 'release', 'tool', 'other', name='candidate_category', create_type=False), nullable=False),
    sa.Column('angle', sa.Text(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), nullable=False),
    sa.Column('brief', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('sections', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('lead_fact_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('generation_options', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('research_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('validation_warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('word_count', sa.Integer(), nullable=False),
    sa.Column('sections_count', sa.Integer(), nullable=False),
    sa.Column('facts_used_count', sa.Integer(), nullable=False),
    sa.Column('facts_available_count', sa.Integer(), nullable=False),
    sa.Column('source_count', sa.Integer(), nullable=False),
    sa.Column('llm_model', sa.String(length=100), nullable=True),
    sa.Column('llm_input_tokens', sa.Integer(), nullable=False),
    sa.Column('llm_output_tokens', sa.Integer(), nullable=False),
    sa.Column('estimated_cost_usd', sa.Numeric(precision=12, scale=6), nullable=True),
    sa.Column('brief_llm_model', sa.String(length=100), nullable=True),
    sa.Column('brief_input_tokens', sa.Integer(), nullable=False),
    sa.Column('brief_output_tokens', sa.Integer(), nullable=False),
    sa.Column('brief_cost_usd', sa.Numeric(precision=12, scale=6), nullable=True),
    sa.Column('writer_input_tokens', sa.Integer(), nullable=False),
    sa.Column('writer_output_tokens', sa.Integer(), nullable=False),
    sa.Column('writer_cost_usd', sa.Numeric(precision=12, scale=6), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['research_id'], ['researches.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('candidate_id', 'version', name='uq_articles_candidate_version')
    )
    op.create_index(op.f('ix_articles_candidate_id'), 'articles', ['candidate_id'], unique=False)
    op.create_index('uq_articles_one_current_per_candidate', 'articles', ['candidate_id'], unique=True, postgresql_where=sa.text('is_current'))


def downgrade() -> None:
    op.drop_index('uq_articles_one_current_per_candidate', table_name='articles', postgresql_where=sa.text('is_current'))
    op.drop_index(op.f('ix_articles_candidate_id'), table_name='articles')
    op.drop_table('articles')
    sa.Enum(name='article_status').drop(op.get_bind(), checkfirst=True)
