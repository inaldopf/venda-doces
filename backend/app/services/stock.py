"""Batch stock rules.

    available = quantity_total
              - SUM(reservations.quantity WHERE status = 'ACTIVE')
              - SUM(sales.quantity        WHERE deleted_at IS NULL)

Every non-cancelled sale counts, including sales created from a reservation. When a reservation is
converted it stops being ACTIVE (leaves the "reserved" term) in the same transaction in which the
sale appears (enters the "sold" term), so each unit is counted exactly once.

Concurrency: any operation that can change availability (new reservation, new sale, lowering the
batch size) must call `lock_batch` first. It takes `SELECT ... FOR UPDATE` on the batch row, so
concurrent operations on the SAME batch run one at a time while other batches are unaffected.
Lock order is always: batch first, then the reservation/sale rows. That avoids deadlocks.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Batch, Reservation, ReservationStatus, Sale


class BatchNotFound(Exception):
    pass


class InsufficientStock(Exception):
    def __init__(self, available: int, requested: int) -> None:
        super().__init__(f"available={available} requested={requested}")
        self.available = available
        self.requested = requested


@dataclass(frozen=True)
class BatchStock:
    total: int
    reserved: int
    sold: int

    @property
    def available(self) -> int:
        return self.total - self.reserved - self.sold


def lock_batch(session: Session, batch_id: int) -> Batch:
    """Lock the batch row until the end of the transaction."""
    batch = session.execute(
        select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)).with_for_update()
    ).scalar_one_or_none()
    if batch is None:
        raise BatchNotFound(batch_id)
    return batch


def get_stock(session: Session, batch: Batch) -> BatchStock:
    reserved = session.scalar(
        select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
            Reservation.batch_id == batch.id, Reservation.status == ReservationStatus.ACTIVE.value
        )
    )
    sold = session.scalar(
        select(func.coalesce(func.sum(Sale.quantity), 0)).where(
            Sale.batch_id == batch.id, Sale.deleted_at.is_(None)
        )
    )
    return BatchStock(total=batch.quantity_total, reserved=int(reserved or 0), sold=int(sold or 0))


def ensure_available(session: Session, batch_id: int, quantity: int) -> Batch:
    """Lock the batch and make sure `quantity` units can still be taken. Call inside a transaction."""
    batch = lock_batch(session, batch_id)
    stock = get_stock(session, batch)
    if quantity > stock.available:
        raise InsufficientStock(stock.available, quantity)
    return batch
