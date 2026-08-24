from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, Timestamped, UUIDPrimaryKey


class Company(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    financial_data: Mapped[list["FinancialData"]] = relationship(back_populates="company", cascade="all, delete-orphan")
