from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Batch, ProductPrice, Reservation, Sale, User


def test_sale_total_must_equal_quantity_times_unit_price(session, make_user, make_batch):
    user, batch = make_user(), make_batch()
    session.add(Sale(batch_id=batch.id, buyer_id=user.id, quantity=3, unit_price=Decimal("5.00"),
                     total_price=Decimal("10.00"), created_by=user.id))
    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("qty", [0, -1])
def test_quantity_must_be_positive(session, make_user, make_batch, qty):
    user, batch = make_user(), make_batch()
    session.add(Reservation(batch_id=batch.id, user_id=user.id, quantity=qty))
    with pytest.raises(IntegrityError):
        session.commit()


def test_expiry_cannot_precede_production(session, make_batch):
    batch = make_batch()
    session.add(Batch(product_id=batch.product_id, production_date=date(2026, 10, 10),
                      expiry_date=date(2026, 10, 9), taken_date=date(2026, 10, 10), quantity_total=5))
    with pytest.raises(IntegrityError):
        session.commit()


def test_only_one_current_price_per_product(session, make_batch):
    batch = make_batch()
    session.add_all([ProductPrice(product_id=batch.product_id, price=Decimal("5.00")),
                     ProductPrice(product_id=batch.product_id, price=Decimal("6.00"))])
    with pytest.raises(IntegrityError):
        session.commit()


def test_closed_price_allows_a_new_current_price(session, make_batch):
    batch = make_batch()
    now = datetime.now(timezone.utc)
    session.add_all([
        ProductPrice(product_id=batch.product_id, price=Decimal("5.00"), valid_from=now - timedelta(days=2), valid_until=now),
        ProductPrice(product_id=batch.product_id, price=Decimal("6.00"), valid_from=now),
    ])
    session.commit()


def test_negative_price_rejected(session, make_batch):
    batch = make_batch()
    session.add(ProductPrice(product_id=batch.product_id, price=Decimal("-1.00")))
    with pytest.raises(IntegrityError):
        session.commit()


def test_email_unique_among_active_users_only(session):
    session.add(User(name="A", email="a@example.com"))
    session.commit()
    session.add(User(name="B", email="a@example.com"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    # soft-deleted user frees the e-mail
    session.query(User).update({"deleted_at": datetime.now(timezone.utc)})
    session.add(User(name="C", email="a@example.com"))
    session.commit()


def test_email_must_be_lowercase(session):
    session.add(User(name="A", email="A@Example.com"))
    with pytest.raises(IntegrityError):
        session.commit()
