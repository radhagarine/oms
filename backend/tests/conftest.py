from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401
from app.database import Base, build_engine, get_db
from app.main import app
from app.models import Customer, Product

API = "/api/v1"


@pytest.fixture
def engine(tmp_path) -> Iterator[Engine]:
    eng = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker) -> Iterator[Session]:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def client(session_factory: sessionmaker) -> Iterator[TestClient]:
    def _override() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@dataclass
class SampleData:
    john: int
    priya: int
    jane: int
    mouse: int  # 10.00, stock 10
    keyboard: int  # 25.50, stock 5
    retired: int  # inactive
    empty: int  # stock 0


@pytest.fixture
def sample(db: Session) -> SampleData:
    customers = [
        Customer(name="John Smith", email="jsmith@example.com", phone="555-0001"),
        Customer(name="Priya Patel", email="ppatel@example.com", phone="555-0002"),
        Customer(name="Jane Doe", email="jdoe@example.com", phone="555-0003"),
    ]
    products = [
        Product(name="Mouse", sku="SKU-M", unit_price=Decimal("10.00"), inventory_quantity=10),
        Product(name="Keyboard", sku="SKU-K", unit_price=Decimal("25.50"), inventory_quantity=5),
        Product(name="Retired", sku="SKU-R", unit_price=Decimal("5.00"), inventory_quantity=50, is_active=False),
        Product(name="Empty", sku="SKU-E", unit_price=Decimal("7.00"), inventory_quantity=0),
    ]
    db.add_all(customers + products)
    db.commit()
    return SampleData(
        john=customers[0].id,
        priya=customers[1].id,
        jane=customers[2].id,
        mouse=products[0].id,
        keyboard=products[1].id,
        retired=products[2].id,
        empty=products[3].id,
    )


def create_order(client: TestClient, customer_id: int, items: list[tuple[int, int]], **extra) -> dict:
    body = {"customer_id": customer_id, "items": [{"product_id": p, "quantity": q} for p, q in items]}
    body.update(extra)
    resp = client.post(f"{API}/orders", json=body)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def inventory_of(client: TestClient, product_id: int) -> int:
    return client.get(f"{API}/products/{product_id}/inventory").json()["inventory_quantity"]


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:  # noqa: ANN001
    """Summarise known-bug tests so evaluators can see which injected defects are still present."""
    rows = []
    for outcome in ("failed", "passed"):
        for rep in terminalreporter.stats.get(outcome, []):
            if rep.when != "call":
                continue
            bug = next((k[1] for k in getattr(rep, "user_properties", []) if k[0] == "known_bug"), None)
            if bug:
                rows.append((bug, outcome, rep.nodeid))
    if not rows:
        return
    terminalreporter.section("Known-bug test status")
    for bug, outcome, nodeid in sorted(rows):
        label = "BUG PRESENT" if outcome == "failed" else "fixed/passing"
        terminalreporter.write_line(f"{bug:<8} {label:<14} {nodeid}")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item) -> None:  # noqa: ANN001
    marker = item.get_closest_marker("known_bug")
    if marker and marker.args:
        item.user_properties.append(("known_bug", marker.args[0]))
