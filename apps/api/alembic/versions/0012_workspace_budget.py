"""Monthly AI budget per workspace (NULL = DEFAULT_MONTHLY_BUDGET_USD) and index for usage queries."""
from alembic import op
import sqlalchemy as sa
revision='0012_workspace_budget'
down_revision='0011_wordpress_connections'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('workspaces', sa.Column('monthly_budget_usd', sa.Numeric(10, 2)))
    op.create_index('ix_job_attempts_started_at', 'job_attempts', ['started_at'])


def downgrade():
    op.drop_index('ix_job_attempts_started_at', 'job_attempts')
    op.drop_column('workspaces', 'monthly_budget_usd')
