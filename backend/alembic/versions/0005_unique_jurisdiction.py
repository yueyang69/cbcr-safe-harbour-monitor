"""add jurisdiction to the financial_data unique constraint

Stage 3: a subsidiary may upload multiple jurisdiction rows for the same
fiscal year, so uniqueness is now (company_id, fiscal_year, jurisdiction).

Renumbered 0004 -> 0005 during the V2.4 merge: origin/main shipped
0004_return_reason first, so this migration now chains after it.
"""
from alembic import op

revision = "0005_unique_jurisdiction"
down_revision = "0004_return_reason"
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
