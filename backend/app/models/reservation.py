from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ReservationStatus
from app.models.mixins import CreatedAtMixin


class Reservation(Base, CreatedAtMixin):
    """A reservation holds stock only while ACTIVE.

    The link to the sale lives in sales.reservation_id (UNIQUE); there is no reverse FK,
    which avoids a circular dependency when converting inside one transaction.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("status IN ('ACTIVE','CONVERTED','CANCELLED')", name="status_valid"),
        Index("ix_reservations_batch_id", "batch_id"),
        Index("ix_reservations_user_id", "user_id"),
        Index("ix_reservations_active_batch", "batch_id", postgresql_where=text("status = 'ACTIVE'")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=ReservationStatus.ACTIVE.value
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
