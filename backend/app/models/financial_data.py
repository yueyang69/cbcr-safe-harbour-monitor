from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, Timestamped, UUIDPrimaryKey

# JSONB on PostgreSQL; falls back to JSON on SQLite so tests can build the schema.
JSONB_VARIANT = JSONB().with_variant(SQLiteJSON(), "sqlite")


class FinancialData(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "financial_data"
    __table_args__ = (UniqueConstraint("company_id", "fiscal_year", "jurisdiction", name="uq_financial_company_year_jurisdiction"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pbt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    covered_taxes: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    payroll: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    tangible_assets: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    is_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_manual_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_anomaly_flags: Mapped[dict | None] = mapped_column(JSONB_VARIANT, nullable=True)
    missing_suggestion: Mapped[dict | None] = mapped_column(JSONB_VARIANT, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="financial_data")
