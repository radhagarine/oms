"""Inventory reservation, restoration and order-creation atomicity."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.errors import InsufficientInventoryError
from app.models import Order
from app.services import inventory_service
from tests.conftest import API, create_order, inventory_of

# ============================================================== A. passing tests


def test_creating_order_reserves_inventory(client, sample):
    create_order(client, sample.john, [(sample.mouse, 3), (sample.keyboard, 2)])
    assert inventory_of(client, sample.mouse) == 7
    assert inventory_of(client, sample.keyboard) == 3


def test_rejected_order_leaves_inventory_unchanged(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.keyboard, "quantity": 6}]})
    assert resp.status_code == 409
    assert inventory_of(client, sample.keyboard) == 5


def test_inventory_never_negative_via_api(client, sample):
    create_order(client, sample.john, [(sample.keyboard, 5)])
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.keyboard, "quantity": 1}]})
    assert resp.status_code == 409
    assert inventory_of(client, sample.keyboard) == 0


def test_status_cancellation_restores_inventory(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 4)])
    assert inventory_of(client, sample.mouse) == 6
    client.patch(f"{API}/orders/{order['id']}/status", json={"status": "CANCELLED"})
    assert inventory_of(client, sample.mouse) == 10


def test_inventory_endpoint(client, sample):
    body = client.get(f"{API}/products/{sample.keyboard}/inventory").json()
    assert body == {"product_id": sample.keyboard, "sku": "SKU-K", "inventory_quantity": 5, "is_active": True}


def test_reserve_rejects_overdraw(db, sample):
    with pytest.raises(InsufficientInventoryError):
        inventory_service.reserve(db, sample.keyboard, 6)


# ============================================================== B. known failing tests


@pytest.mark.known_bug("BUG-05")
def test_cancel_endpoint_restores_inventory(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 4)])
    client.post(f"{API}/orders/{order['id']}/cancel")
    assert inventory_of(client, sample.mouse) == 10


@pytest.mark.known_bug("BUG-15")
def test_repeated_cancellation_restores_inventory_once(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 4)])
    for _ in range(3):
        client.patch(f"{API}/orders/{order['id']}/status", json={"status": "CANCELLED"})
    assert inventory_of(client, sample.mouse) == 10


@pytest.mark.known_bug("BUG-13")
def test_failed_reservation_does_not_leave_order_behind(client, db, sample):
    # Each line individually fits the 5 units in stock; together they exceed it.
    resp = client.post(
        f"{API}/orders",
        json={"customer_id": sample.john, "items": [{"product_id": sample.keyboard, "quantity": 3}, {"product_id": sample.keyboard, "quantity": 3}]},
    )
    assert resp.status_code == 409
    assert db.scalar(select(func.count(Order.id))) == 0
    assert inventory_of(client, sample.keyboard) == 5


@pytest.mark.known_bug("BUG-13")
def test_simulated_reservation_failure_rolls_back(client, db, sample, monkeypatch):
    real_reserve = inventory_service.reserve
    calls = {"n": 0}

    def flaky_reserve(session, product_id, quantity):
        calls["n"] += 1
        if calls["n"] == 2:
            raise InsufficientInventoryError("simulated reservation failure")
        return real_reserve(session, product_id, quantity)

    monkeypatch.setattr(inventory_service, "reserve", flaky_reserve)
    resp = client.post(
        f"{API}/orders",
        json={"customer_id": sample.john, "items": [{"product_id": sample.mouse, "quantity": 2}, {"product_id": sample.keyboard, "quantity": 1}]},
    )
    assert resp.status_code == 409
    assert db.scalar(select(func.count(Order.id))) == 0
    assert inventory_of(client, sample.mouse) == 10
