from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, SoftDeleteMixin


class Batch(Base, CreatedAtMixin, SoftDeleteMixin):
    """A production batch. quantity_total = produced = taken to sell (same number)."""

    __tablename__ = "batches"
    __table_args__ = (
        CheckConstraint("quantity_total > 0", name="quantity_positive"),
        CheckConstraint("expiry_date >= production_date", name="expiry_after_production"),
        CheckConstraint("taken_date >= production_date", name="taken_after_production"),
        Index("ix_batches_product_id", "product_id"),
        Index("ix_batches_taken_date", "taken_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    taken_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_total: Mapped[int] = mapped_column(Integer, nullable=False)
