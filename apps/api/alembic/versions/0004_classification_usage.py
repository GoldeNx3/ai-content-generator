"""Store usage for subsequent classifications; historical usage remains unknown."""
from alembic import op
import sqlalchemy as sa
revision = "0004_classification_usage"
down_revision = "0003_articles"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("candidates", sa.Column("llm_model", sa.String(200), nullable=True))
    op.add_column("candidates", sa.Column("llm_input_tokens", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("llm_output_tokens", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=True))

def downgrade() -> None:
    for column in ("estimated_cost_usd", "llm_output_tokens", "llm_input_tokens", "llm_model"):
        op.drop_column("candidates", column)
