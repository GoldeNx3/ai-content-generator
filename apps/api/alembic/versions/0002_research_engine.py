# Rola pliku: Migracja researchu: dodaje raporty, źródła, fakty i ich powiązania.

"""research engine

Revision ID: 0002_research
Revises: 0001_initial
Create Date: 2026-10-02 20:57:45.533515

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002_research'
down_revision: str | None = '0001_initial'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Alembic wywołuje upgrade przy przejściu do tej wersji schematu; operacje dotyczą struktury SQL, nie
# endpointów API.
def upgrade() -> None:
    op.create_table('researches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='research_status'), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('why_it_matters', sa.Text(), nullable=True),
    sa.Column('suggested_angle', sa.Text(), nullable=True),
    sa.Column('search_queries', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('uncertainties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('conflicts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('llm_model', sa.String(length=100), nullable=True),
    sa.Column('llm_input_tokens', sa.Integer(), nullable=False),
    sa.Column('llm_output_tokens', sa.Integer(), nullable=False),
    sa.Column('estimated_cost_usd', sa.Numeric(precision=12, scale=6), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('candidate_id')
    )
    op.create_table('research_facts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('research_id', sa.Integer(), nullable=False),
    sa.Column('claim', sa.Text(), nullable=False),
    sa.Column('importance', sa.Enum('critical', 'important', 'supporting', name='fact_importance'), nullable=False),
    sa.Column('confidence', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['research_id'], ['researches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_facts_research_id'), 'research_facts', ['research_id'], unique=False)
    op.create_table('research_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('research_id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=2048), nullable=False),
    sa.Column('origin', sa.Enum('original', 'search', 'manual', name='research_source_origin'), nullable=False),
    sa.Column('title', sa.String(length=1000), nullable=True),
    sa.Column('publisher', sa.String(length=300), nullable=True),
    sa.Column('source_type', sa.Enum('official', 'documentation', 'github', 'news', 'blog', 'community', 'other', name='research_source_type'), nullable=False),
    sa.Column('source_score', sa.Integer(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('raw_content', sa.Text(), nullable=True),
    sa.Column('extracted_content', sa.Text(), nullable=True),
    sa.Column('fetch_status', sa.Enum('pending', 'success', 'failed', name='fetch_status'), nullable=False),
    sa.Column('http_status', sa.Integer(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['research_id'], ['researches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('research_id', 'url', name='uq_research_sources_research_url')
    )
    op.create_index(op.f('ix_research_sources_research_id'), 'research_sources', ['research_id'], unique=False)
    op.create_table('research_fact_sources',
    sa.Column('fact_id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['fact_id'], ['research_facts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_id'], ['research_sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('fact_id', 'source_id')
    )


# downgrade opisuje cofnięcie tej migracji; usuwanie tabel lub kolumn może usunąć przechowywane dane.
def downgrade() -> None:
    op.drop_table('research_fact_sources')
    op.drop_index(op.f('ix_research_sources_research_id'), table_name='research_sources')
    op.drop_table('research_sources')
    op.drop_index(op.f('ix_research_facts_research_id'), table_name='research_facts')
    op.drop_table('research_facts')
    op.drop_table('researches')
    sa.Enum(name='fact_importance').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='fetch_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='research_source_origin').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='research_source_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='research_status').drop(op.get_bind(), checkfirst=True)
