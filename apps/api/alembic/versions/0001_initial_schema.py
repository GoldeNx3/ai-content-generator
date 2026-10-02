"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-02 20:38:19.814747

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('type', sa.Enum('rss', name='source_type'), nullable=False),
    sa.Column('url', sa.String(length=2048), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_table('candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('external_url', sa.String(length=2048), nullable=False),
    sa.Column('title', sa.String(length=1000), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('original_published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('pending', 'approved', 'ignored', name='candidate_status'), nullable=False),
    sa.Column('relevance_score', sa.Integer(), nullable=True),
    sa.Column('freshness_score', sa.Integer(), nullable=True),
    sa.Column('search_potential_score', sa.Integer(), nullable=True),
    sa.Column('commercial_potential_score', sa.Integer(), nullable=True),
    sa.Column('total_score', sa.Integer(), nullable=True),
    sa.Column('category', sa.Enum('news', 'guide', 'comparison', 'pricing', 'release', 'tool', 'other', name='candidate_category'), nullable=True),
    sa.Column('llm_reason', sa.Text(), nullable=True),
    sa.Column('classified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_url')
    )
    op.create_index(op.f('ix_candidates_source_id'), 'candidates', ['source_id'], unique=False)
    op.create_index(op.f('ix_candidates_status'), 'candidates', ['status'], unique=False)
    op.create_index(op.f('ix_candidates_total_score'), 'candidates', ['total_score'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_candidates_total_score'), table_name='candidates')
    op.drop_index(op.f('ix_candidates_status'), table_name='candidates')
    op.drop_index(op.f('ix_candidates_source_id'), table_name='candidates')
    op.drop_table('candidates')
    op.drop_table('sources')
    sa.Enum(name='candidate_category').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='candidate_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='source_type').drop(op.get_bind(), checkfirst=True)
