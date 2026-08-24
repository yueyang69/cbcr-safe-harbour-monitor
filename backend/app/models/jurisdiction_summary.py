from decimal import Decimal
from sqlalchemy import Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, Timestamped, UUIDPrimaryKey


class JurisdictionSummary(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "jurisdiction_summary"
    __table_args__ = (UniqueConstraint("jurisdiction", "fiscal_year", name="uq_summary_jurisdiction_year"),)

    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pbt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    covered_taxes: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    payroll: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    tangible_assets: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    company_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    included_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INCOMPLETE")
    evaluation: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
