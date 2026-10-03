from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PaymentStatus
from app.models.mixins import CreatedAtMixin, SoftDeleteMixin


class Sale(Base, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        # Defense in depth: the backend computes the total, the database refuses anything else.
        CheckConstraint("total_price = quantity * unit_price", name="total_matches"),
        CheckConstraint("payment_status IN ('PAID','PENDING','PARTIAL')", name="payment_status_valid"),
        CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('CASH','PIX','CARD','OTHER')",
            name="payment_method_valid",
        ),
        Index("ix_sales_batch_id", "batch_id"),
        Index("ix_sales_buyer_id", "buyer_id"),
        Index("ix_sales_sale_date", "sale_date"),
        Index("ix_sales_payment_status", "payment_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # UNIQUE: a reservation can become at most one sale.
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), unique=True)
    sale_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # snapshot
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=PaymentStatus.PENDING.value
    )
    payment_method: Mapped[str | None] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text)


class Payment(Base, CreatedAtMixin):
    """Immutable payment record. A mistake is corrected by voiding (never deleting)."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("method IN ('CASH','PIX','CARD','OTHER')", name="method_valid"),
        Index("ix_payments_sale_id", "sale_id"),
        Index("ix_payments_paid_at", "paid_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)
