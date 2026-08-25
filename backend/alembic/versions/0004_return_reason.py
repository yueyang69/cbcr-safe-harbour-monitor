"""add return_reason to financial_data"""
from alembic import op
import sqlalchemy as sa

revision = "0004_return_reason"
down_revision = "0003_entity_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reason HQ attached when returning a submission; shown to the subsidiary.
    op.add_column("financial_data", sa.Column("return_reason", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("financial_data", "return_reason")
