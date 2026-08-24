from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, Timestamped, UUIDPrimaryKey


class MappingRule(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mapping_rules"
    __table_args__ = (UniqueConstraint("source_field", "target_field", name="uq_mapping_source_target"),)

    source_field: Mapped[str] = mapped_column(String(200), nullable=False)
    target_field: Mapped[str] = mapped_column(String(100), nullable=False)
    confirmed_by: Mapped[str] = mapped_column(String(100), nullable=False, default="hq")
