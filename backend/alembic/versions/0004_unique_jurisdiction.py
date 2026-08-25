"""add jurisdiction to the financial_data unique constraint

Stage 3: a subsidiary may upload multiple jurisdiction rows for the same
fiscal year, so uniqueness is now (company_id, fiscal_year, jurisdiction).
"""
from alembic import op

revision = "0004_unique_jurisdiction"
down_revision = "0003_entity_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_financial_company_year", "financial_data", type_="unique")
    op.create_unique_constraint(
        "uq_financial_company_year_jurisdiction",
        "financial_data",
        ["company_id", "fiscal_year", "jurisdiction"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_financial_company_year_jurisdiction", "financial_data", type_="unique")
    op.create_unique_constraint(
        "uq_financial_company_year",
        "financial_data",
        ["company_id", "fiscal_year"],
    )
