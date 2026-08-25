"""add entity_type and parent_entity_id to companies"""
from alembic import op
import sqlalchemy as sa

revision = "0003_entity_fields"
down_revision = "0002_ai_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reporting entity hierarchy: Subsidiary / Branch + optional parent entity
    op.add_column("companies", sa.Column("entity_type", sa.String(length=20), server_default=sa.text("'subsidiary'"), nullable=False))
    op.add_column("companies", sa.Column("parent_entity_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_companies_parent_entity", "companies", "companies", ["parent_entity_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_companies_parent_entity_id", "companies", ["parent_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_companies_parent_entity_id", table_name="companies")
    op.drop_constraint("fk_companies_parent_entity", "companies", type_="foreignkey")
    op.drop_column("companies", "parent_entity_id")
    op.drop_column("companies", "entity_type")
