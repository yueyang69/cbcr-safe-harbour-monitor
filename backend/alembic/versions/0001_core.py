"""create core tables"""
from alembic import op
import sqlalchemy as sa

revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("companies",
        sa.Column("id", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=100)), sa.PrimaryKeyConstraint("id"))
    op.create_table("financial_data",
        sa.Column("id", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False), sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False), sa.Column("revenue", sa.Numeric(20, 2)), sa.Column("pbt", sa.Numeric(20, 2)),
        sa.Column("covered_taxes", sa.Numeric(20, 2)), sa.Column("payroll", sa.Numeric(20, 2)), sa.Column("tangible_assets", sa.Numeric(20, 2)),
        sa.Column("is_submitted", sa.Boolean(), nullable=False), sa.Column("is_approved", sa.Boolean(), nullable=False),
        sa.Column("requires_manual_confirmation", sa.Boolean(), nullable=False), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("company_id", "fiscal_year", name="uq_financial_company_year"))
    for table, cols in [("mapping_rules", [sa.Column("id", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("source_field", sa.String(200), nullable=False), sa.Column("target_field", sa.String(100), nullable=False), sa.Column("confirmed_by", sa.String(100), nullable=False)]), ("jurisdiction_summary", [sa.Column("id", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("jurisdiction", sa.String(100), nullable=False), sa.Column("fiscal_year", sa.Integer(), nullable=False), sa.Column("revenue", sa.Numeric(20,2)), sa.Column("pbt", sa.Numeric(20,2)), sa.Column("covered_taxes", sa.Numeric(20,2)), sa.Column("payroll", sa.Numeric(20,2)), sa.Column("tangible_assets", sa.Numeric(20,2)), sa.Column("company_count", sa.Integer(), nullable=False), sa.Column("included_count", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("evaluation", sa.JSON()), sa.Column("warnings", sa.JSON(), nullable=False)])]:
        constraints = [sa.PrimaryKeyConstraint("id")]
        if table == "mapping_rules": constraints.append(sa.UniqueConstraint("source_field", "target_field", name="uq_mapping_source_target"))
        else: constraints.append(sa.UniqueConstraint("jurisdiction", "fiscal_year", name="uq_summary_jurisdiction_year"))
        op.create_table(table, *cols, *constraints)


def downgrade() -> None:
    for table in ("jurisdiction_summary", "mapping_rules", "financial_data", "companies"):
        op.drop_table(table)
