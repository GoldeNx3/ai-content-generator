"""Append-only versions, editorial fix reports and guarded approval."""
import hashlib,json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
revision='0007_auto_fix_approval'
down_revision='0006_article_qa'
branch_labels=None
depends_on=None


def upgrade():
    with op.get_context().autocommit_block():
        for value in ('needs_changes','ready_for_approval','manual_review_required','superseded'):
            op.execute(f"ALTER TYPE article_status ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column('articles',sa.Column('parent_version_id',sa.Integer(),sa.ForeignKey('articles.id',name='fk_articles_parent',ondelete='RESTRICT')))
    op.add_column('articles',sa.Column('created_by',sa.String(30),nullable=False,server_default='legacy'))
    op.add_column('articles',sa.Column('creation_reason',sa.Text()))
    op.add_column('articles',sa.Column('content_hash',sa.String(64),nullable=False,server_default=''))
    op.add_column('articles',sa.Column('auto_fix_iteration',sa.Integer(),nullable=False,server_default='0'))
    op.add_column('articles',sa.Column('approved_at',sa.DateTime(timezone=True)))
    op.add_column('articles',sa.Column('approved_by',sa.String(100)))
    op.add_column('articles',sa.Column('rejection_reason',sa.Text()))
    connection=op.get_bind()
    for row in connection.execute(sa.text('SELECT id,title,lead,content,slug,meta_title,meta_description FROM articles')).mappings():
        data={k:row[k].replace('\r\n','\n').replace('\r','\n') for k in ('title','lead','content','slug','meta_title','meta_description')}
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        connection.execute(sa.text('UPDATE articles SET content_hash=:digest WHERE id=:id'),dict(digest=digest,id=row['id']))
    op.execute("UPDATE articles SET status='superseded' WHERE status='approved' AND id NOT IN (SELECT DISTINCT ON (candidate_id) id FROM articles WHERE status='approved' ORDER BY candidate_id,version DESC)")
    # Existing valid QA is already a completed readiness decision; avoid rewriting its evidence.
    op.execute("UPDATE articles SET status='ready_for_approval' WHERE qa_passed AND status IN ('draft','review')")
    op.create_index('uq_articles_one_approved_per_candidate','articles',['candidate_id'],unique=True,postgresql_where=sa.text("status='approved'"))
    op.drop_constraint('ck_jobs_kind','jobs',type_='check')
    op.create_check_constraint('ck_jobs_kind','jobs',"kind IN ('classify','research','write','qa_article','auto_fix_article')")
    timestamps=lambda:[sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now())]
    op.create_table('article_fixes',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('source_article_version_id',sa.Integer(),sa.ForeignKey('articles.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('result_article_version_id',sa.Integer(),sa.ForeignKey('articles.id',ondelete='RESTRICT'),unique=True),
        sa.Column('qa_id',sa.Integer(),sa.ForeignKey('article_qas.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('job_id',sa.Uuid(),sa.ForeignKey('jobs.id',ondelete='SET NULL'),unique=True),
        sa.Column('status',sa.String(20),nullable=False),sa.Column('iteration',sa.Integer(),nullable=False),
        sa.Column('input_hash',sa.String(64),nullable=False),sa.Column('input_snapshot',pg.JSONB(),nullable=False),
        *[sa.Column(k,sa.Integer(),nullable=False) for k in ('issues_requested','issues_fixed','issues_skipped')],
        sa.Column('summary',sa.Text()),sa.Column('change_ratio',sa.Numeric(8,6)),
        sa.Column('warnings',pg.JSONB(),nullable=False),sa.Column('changes',pg.JSONB(),nullable=False),
        sa.Column('llm_model',sa.String(100)),sa.Column('llm_input_tokens',sa.Integer()),sa.Column('llm_output_tokens',sa.Integer()),
        sa.Column('estimated_cost_usd',sa.Numeric(12,6)),*timestamps(),
        sa.CheckConstraint("status IN ('pending','running','completed','failed')",name='ck_article_fix_status'))
    op.create_index('ix_article_fixes_source_article_version_id','article_fixes',['source_article_version_id'])
    op.create_table('article_fix_issues',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('article_fix_id',sa.Integer(),sa.ForeignKey('article_fixes.id',ondelete='CASCADE'),nullable=False),
        sa.Column('qa_issue_id',sa.Integer(),sa.ForeignKey('article_qa_issues.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),sa.Column('reason',sa.Text(),nullable=False),*timestamps(),
        sa.UniqueConstraint('article_fix_id','qa_issue_id',name='uq_fix_issue'),
        sa.CheckConstraint("status IN ('fixed','skipped','failed')",name='ck_fix_issue_status'))
    op.create_index('ix_article_fix_issues_article_fix_id','article_fix_issues',['article_fix_id'])


def downgrade():
    # Never silently discard versions, fixes, or the durable queue.
    raise RuntimeError('Export fix history and use a reviewed forward migration; destructive downgrade is disabled.')
