import os
from collections.abc import Iterator
from datetime import date

# Must be set before importing the app (settings are read at import time).
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://venda:venda_dev@localhost:5432/venda_doces_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import Batch, Product, User


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE payments, sales, reservations, batches, product_prices, "
                "product_photos, products, refresh_tokens, audit_logs, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def session() -> Iterator[Session]:
    with SessionLocal() as s:
        yield s


@pytest.fixture
def make_user(session: Session):
    def _make(email: str = "ana@example.com", is_admin: bool = False) -> User:
        user = User(name="Ana", email=email, is_admin=is_admin)
        session.add(user)
        session.commit()
        return user

    return _make


@pytest.fixture
def make_batch(session: Session):
    def _make(quantity: int = 10) -> Batch:
        product = Product(name="Pão de mel")
        session.add(product)
        session.flush()
        batch = Batch(
            product_id=product.id,
            production_date=date(2026, 10, 1),
            expiry_date=date(2026, 10, 15),
            taken_date=date(2026, 10, 2),
            quantity_total=quantity,
        )
        session.add(batch)
        session.commit()
        return batch

    return _make
