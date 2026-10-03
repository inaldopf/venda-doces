from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Reservation, ReservationStatus, Sale
from app.services.stock import InsufficientStock, ensure_available, get_stock


def _sale(batch_id: int, buyer_id: int, qty: int, reservation_id: int | None = None, deleted: bool = False) -> Sale:
    price = Decimal("5.00")
    return Sale(
        batch_id=batch_id, buyer_id=buyer_id, quantity=qty, unit_price=price, total_price=price * qty,
        created_by=buyer_id, reservation_id=reservation_id,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )


def test_stock_formula_counts_each_unit_once(session, make_user, make_batch):
    user, batch = make_user(), make_batch(10)
    r_active = Reservation(batch_id=batch.id, user_id=user.id, quantity=3)
    r_cancelled = Reservation(batch_id=batch.id, user_id=user.id, quantity=2, status="CANCELLED")
    r_converted = Reservation(batch_id=batch.id, user_id=user.id, quantity=1, status="CONVERTED")
    session.add_all([r_active, r_cancelled, r_converted])
    session.flush()
    session.add_all([
        _sale(batch.id, user.id, 2),                                  # direct sale
        _sale(batch.id, user.id, 1, reservation_id=r_converted.id),   # sale born from a reservation
        _sale(batch.id, user.id, 4, deleted=True),                    # cancelled sale: ignored
    ])
    session.commit()

    stock = get_stock(session, batch)
    assert (stock.total, stock.reserved, stock.sold, stock.available) == (10, 3, 3, 4)


def test_converting_a_reservation_does_not_change_availability(session, make_user, make_batch):
    user, batch = make_user(), make_batch(10)
    reservation = Reservation(batch_id=batch.id, user_id=user.id, quantity=3)
    session.add(reservation)
    session.commit()
    assert get_stock(session, batch).available == 7

    reservation.status = ReservationStatus.CONVERTED.value
    session.flush()
    session.add(_sale(batch.id, user.id, 3, reservation_id=reservation.id))
    session.commit()

    stock = get_stock(session, batch)
    assert (stock.reserved, stock.sold, stock.available) == (0, 3, 7)


def test_cancelling_returns_quantity_to_the_batch(session, make_user, make_batch):
    user, batch = make_user(), make_batch(10)
    reservation = Reservation(batch_id=batch.id, user_id=user.id, quantity=4)
    session.add(reservation)
    session.commit()
    reservation.status = ReservationStatus.CANCELLED.value
    session.commit()
    assert get_stock(session, batch).available == 10


def test_request_above_available_is_rejected(session, make_user, make_batch):
    user, batch = make_user(), make_batch(5)
    session.add(Reservation(batch_id=batch.id, user_id=user.id, quantity=4))
    session.commit()
    with pytest.raises(InsufficientStock) as exc:
        ensure_available(session, batch.id, 2)
    assert exc.value.available == 1


def test_concurrent_reservations_never_oversell(make_user, make_batch):
    """8 simultaneous requests of 2 units against a batch of 10: exactly 5 must succeed."""
    user, batch = make_user(), make_batch(10)
    user_id, batch_id = user.id, batch.id

    def try_reserve() -> bool:
        with SessionLocal() as s:
            try:
                ensure_available(s, batch_id, 2)  # takes the row lock
                s.add(Reservation(batch_id=batch_id, user_id=user_id, quantity=2))
                s.commit()
                return True
            except InsufficientStock:
                s.rollback()
                return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: try_reserve(), range(8)))

    assert results.count(True) == 5
    with SessionLocal() as s:
        total = sum(r.quantity for r in s.scalars(select(Reservation)))
        assert total == 10
