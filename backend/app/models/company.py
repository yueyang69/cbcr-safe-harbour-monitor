from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, Timestamped, UUIDPrimaryKey


class Company(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, default="subsidiary")
    parent_entity_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)

    financial_data: Mapped[list["FinancialData"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    parent_entity: Mapped["Company | None"] = relationship(remote_side=lambda: [Company.id], back_populates="child_entities")
    child_entities: Mapped[list["Company"]] = relationship(back_populates="parent_entity")
