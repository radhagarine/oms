"""Order creation, retrieval, listing, calculations and status transitions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from tests.conftest import API, create_order
from tests.helpers import insert_order

# ============================================================== A. passing tests


def test_create_order_persists_items_and_price_snapshot(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 2), (sample.keyboard, 1)])
    assert order["status"] == "PENDING"
    assert order["customer"]["name"] == "John Smith"
    lines = {i["product_id"]: i for i in order["items"]}
    assert Decimal(lines[sample.mouse]["unit_price"]) == Decimal("10.00")
    assert Decimal(lines[sample.mouse]["line_total"]) == Decimal("20.00")
    assert Decimal(lines[sample.keyboard]["line_total"]) == Decimal("25.50")


def test_create_order_unknown_customer_returns_404(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": 999, "items": [{"product_id": sample.mouse, "quantity": 1}]})
    assert resp.status_code == 404


def test_create_order_unknown_product_returns_404(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": 999, "quantity": 1}]})
    assert resp.status_code == 404


def test_create_order_with_inactive_product_is_rejected(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.retired, "quantity": 1}]})
    assert resp.status_code == 409


def test_create_order_with_insufficient_stock_is_rejected(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.empty, "quantity": 1}]})
    assert resp.status_code == 409
    assert client.get(f"{API}/orders").json()["items"] == []


def test_create_order_rejects_zero_quantity_and_negative_charges(client, sample):
    base = {"customer_id": sample.john, "items": [{"product_id": sample.mouse, "quantity": 1}]}
    assert client.post(f"{API}/orders", json={**base, "items": [{"product_id": sample.mouse, "quantity": 0}]}).status_code == 422
    assert client.post(f"{API}/orders", json={**base, "discount": "-1"}).status_code == 422
    assert client.post(f"{API}/orders", json={**base, "shipping_charge": "-5"}).status_code == 422


def test_get_order_and_items(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 3)])
    detail = client.get(f"{API}/orders/{order['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == order["id"]
    items = client.get(f"{API}/orders/{order['id']}/items")
    assert items.status_code == 200
    assert [i["quantity"] for i in items.json()] == [3]


def test_subtotal_discount_and_tax_calculation(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 2), (sample.keyboard, 2)], discount="10.00")
    assert Decimal(order["subtotal"]) == Decimal("71.00")
    assert Decimal(order["discount"]) == Decimal("10.00")
    assert Decimal(order["tax"]) == Decimal("4.88")  # 8% of 61.00


def test_historical_price_unchanged_after_product_price_change(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    client.patch(f"{API}/products/{sample.mouse}", json={"unit_price": "99.00"})
    detail = client.get(f"{API}/orders/{order['id']}").json()
    assert Decimal(detail["items"][0]["unit_price"]) == Decimal("10.00")
    assert Decimal(detail["subtotal"]) == Decimal("10.00")


def test_list_orders_filters_by_status(client, db, sample):
    insert_order(db, sample.john, sample.mouse, status="PENDING")
    insert_order(db, sample.john, sample.mouse, status="SHIPPED", payment_status="PAID")
    insert_order(db, sample.priya, sample.mouse, status="SHIPPED", payment_status="PAID")
    body = client.get(f"{API}/orders", params={"status": "SHIPPED"}).json()
    assert len(body["items"]) == 2
    assert {o["status"] for o in body["items"]} == {"SHIPPED"}


def test_list_orders_filters_by_payment_status_and_customer(client, db, sample):
    insert_order(db, sample.john, sample.mouse, payment_status="PAID", status="CONFIRMED")
    insert_order(db, sample.john, sample.mouse)
    insert_order(db, sample.priya, sample.mouse, payment_status="PAID", status="CONFIRMED")
    body = client.get(f"{API}/orders", params={"payment_status": "PAID", "customer_id": sample.john}).json()
    assert body["total"] == 1
    assert body["items"][0]["customer_id"] == sample.john


def test_list_orders_filters_by_date_range(client, db, sample):
    insert_order(db, sample.john, sample.mouse, order_date=datetime(2025, 3, 10))
    insert_order(db, sample.john, sample.mouse, order_date=datetime(2025, 6, 10))
    body = client.get(f"{API}/orders", params={"date_from": "2025-06-01", "date_to": "2025-06-30"}).json()
    assert body["total"] == 1


def test_search_with_matching_case_finds_customer(client, db, sample):
    insert_order(db, sample.john, sample.mouse)
    insert_order(db, sample.priya, sample.mouse)
    body = client.get(f"{API}/orders", params={"search": "John"}).json()
    assert [o["customer_name"] for o in body["items"]] == ["John Smith"]


def test_unfiltered_pagination(client, db, sample):
    for _ in range(5):
        insert_order(db, sample.john, sample.mouse)
    page1 = client.get(f"{API}/orders", params={"page": 1, "page_size": 2}).json()
    page3 = client.get(f"{API}/orders", params={"page": 3, "page_size": 2}).json()
    assert (page1["total"], page1["total_pages"], page1["has_next"], page1["has_previous"]) == (5, 3, True, False)
    assert len(page3["items"]) == 1
    assert page3["has_next"] is False and page3["has_previous"] is True


def test_sort_by_grand_total(client, db, sample):
    for qty in (3, 1, 2):
        insert_order(db, sample.john, sample.mouse, quantity=qty)
    body = client.get(f"{API}/orders", params={"sort_by": "grand_total", "sort_order": "asc"}).json()
    assert [Decimal(o["grand_total"]) for o in body["items"]] == [Decimal("10.00"), Decimal("20.00"), Decimal("30.00")]


def test_valid_forward_transitions(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    for status in ("CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"):
        resp = client.patch(f"{API}/orders/{order['id']}/status", json={"status": status})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == status


def test_backward_transition_rejected(client, db, sample):
    order = insert_order(db, sample.john, sample.mouse, status="SHIPPED", payment_status="PAID")
    resp = client.patch(f"{API}/orders/{order.id}/status", json={"status": "PENDING"})
    assert resp.status_code == 409


def test_cancelled_order_cannot_be_reopened(client, db, sample):
    order = insert_order(db, sample.john, sample.mouse, status="CANCELLED")
    resp = client.patch(f"{API}/orders/{order.id}/status", json={"status": "CONFIRMED"})
    assert resp.status_code == 409


def test_cancel_pending_order(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    resp = client.post(f"{API}/orders/{order['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_customer_orders_endpoint(client, db, sample):
    insert_order(db, sample.john, sample.mouse)
    insert_order(db, sample.john, sample.keyboard)
    insert_order(db, sample.priya, sample.mouse)
    resp = client.get(f"{API}/customers/{sample.john}/orders")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_metrics_summary(client, db, sample):
    insert_order(db, sample.john, sample.mouse, status="PENDING")
    insert_order(db, sample.john, sample.mouse, status="DELIVERED", payment_status="PAID", quantity=2)
    insert_order(db, sample.john, sample.mouse, status="CANCELLED", quantity=5)
    m = client.get(f"{API}/metrics/summary").json()
    assert (m["total_orders"], m["pending_orders"], m["delivered_orders"], m["cancelled_orders"]) == (3, 1, 1, 1)
    assert Decimal(m["total_order_value"]) == Decimal("30.00")


# ============================================================== B. known failing tests


@pytest.mark.known_bug("BUG-02")
def test_search_is_case_insensitive(client, db, sample):
    insert_order(db, sample.john, sample.mouse)
    body = client.get(f"{API}/orders", params={"search": "john"}).json()
    assert [o["customer_name"] for o in body["items"]] == ["John Smith"]


@pytest.mark.known_bug("BUG-03")
def test_grand_total_includes_shipping(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 2)], discount="5.00", shipping_charge="7.50")
    expected = Decimal(order["subtotal"]) - Decimal(order["discount"]) + Decimal(order["tax"]) + Decimal(order["shipping_charge"])
    assert Decimal(order["grand_total"]) == expected  # 20 - 5 + 1.20 + 7.50 = 23.70


@pytest.mark.known_bug("BUG-04")
def test_delivered_order_cannot_be_cancelled(client, db, sample):
    order = insert_order(db, sample.john, sample.mouse, status="DELIVERED", payment_status="PAID")
    resp = client.patch(f"{API}/orders/{order.id}/status", json={"status": "CANCELLED"})
    assert resp.status_code == 409


@pytest.mark.known_bug("BUG-04")
def test_status_cannot_skip_steps(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    resp = client.patch(f"{API}/orders/{order['id']}/status", json={"status": "SHIPPED"})
    assert resp.status_code == 409


@pytest.mark.known_bug("BUG-06")
def test_order_update_rejects_negative_quantity(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 2)])
    item_id = order["items"][0]["id"]
    resp = client.put(
        f"{API}/orders/{order['id']}",
        json={"payment_status": "UNPAID", "discount": "0", "shipping_charge": "0", "items": [{"id": item_id, "quantity": -3}]},
    )
    assert resp.status_code == 422


@pytest.mark.known_bug("BUG-07")
def test_sort_by_order_date_is_chronological(client, db, sample):
    for when in (datetime(2025, 12, 20), datetime(2026, 1, 5), datetime(2026, 3, 1)):
        insert_order(db, sample.john, sample.mouse, order_date=when)
    body = client.get(f"{API}/orders", params={"sort_by": "order_date", "sort_order": "desc"}).json()
    assert [o["order_date"][:10] for o in body["items"]] == ["2026-03-01", "2026-01-05", "2025-12-20"]


@pytest.mark.known_bug("BUG-17")
def test_order_totals_recalculated_after_quantity_update(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    item_id = order["items"][0]["id"]
    resp = client.put(
        f"{API}/orders/{order['id']}",
        json={"payment_status": "UNPAID", "discount": "0", "shipping_charge": "0", "items": [{"id": item_id, "quantity": 4}]},
    )
    body = resp.json()
    assert Decimal(body["items"][0]["line_total"]) == Decimal("40.00")
    assert Decimal(body["subtotal"]) == Decimal("40.00")


@pytest.mark.known_bug("BUG-23")
def test_filtered_pagination_metadata_matches_results(client, db, sample):
    for _ in range(3):
        insert_order(db, sample.john, sample.mouse, status="PENDING")
    insert_order(db, sample.john, sample.mouse, status="SHIPPED", payment_status="PAID")
    body = client.get(f"{API}/orders", params={"status": "SHIPPED", "page_size": 1}).json()
    assert len(body["items"]) == 1
    assert body["total"] == 1
    assert body["total_pages"] == 1
    assert body["has_next"] is False
