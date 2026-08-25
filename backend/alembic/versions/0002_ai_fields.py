"""add ai fields to financial_data and mapping_rules"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ai_fields"
down_revision = "0001_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI-related fields to financial_data table
    op.add_column("financial_data", sa.Column("ai_anomaly_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("financial_data", sa.Column("missing_suggestion", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add AI-related fields to mapping_rules table
    op.add_column("mapping_rules", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column("mapping_rules", sa.Column("confirmed_by_user", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("mapping_rules", "confirmed_by_user")
    op.drop_column("mapping_rules", "confidence_score")
    op.drop_column("financial_data", "missing_suggestion")
    op.drop_column("financial_data", "ai_anomaly_flags")
