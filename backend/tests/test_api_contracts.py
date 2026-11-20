"""HTTP contract: status codes, validation and error formats."""
from __future__ import annotations

import pytest

from tests.conftest import API, create_order

# ============================================================== A. passing tests


def test_openapi_documents_all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v1/orders", "/api/v1/orders/{order_id}", "/api/v1/orders/{order_id}/status",
        "/api/v1/orders/{order_id}/cancel", "/api/v1/orders/{order_id}/items",
        "/api/v1/products", "/api/v1/products/{product_id}", "/api/v1/products/{product_id}/inventory",
        "/api/v1/customers", "/api/v1/customers/{customer_id}", "/api/v1/customers/{customer_id}/orders",
    ):
        assert path in paths


def test_create_product_returns_201_and_rejects_duplicate_sku(client):
    body = {"name": "Cable", "sku": "SKU-C", "unit_price": "3.50", "inventory_quantity": 4}
    assert client.post(f"{API}/products", json=body).status_code == 201
    assert client.post(f"{API}/products", json=body).status_code == 409


def test_create_product_rejects_negative_price_and_inventory(client):
    assert client.post(f"{API}/products", json={"name": "X", "sku": "X1", "unit_price": "-1"}).status_code == 422
    assert client.post(f"{API}/products", json={"name": "X", "sku": "X2", "unit_price": "1", "inventory_quantity": -1}).status_code == 422


def test_create_customer_returns_201_and_rejects_duplicate_email(client):
    body = {"name": "Ana", "email": "ana@example.com"}
    assert client.post(f"{API}/customers", json=body).status_code == 201
    assert client.post(f"{API}/customers", json=body).status_code == 409


def test_invalid_customer_email_returns_422(client):
    assert client.post(f"{API}/customers", json={"name": "Ana", "email": "not-an-email"}).status_code == 422


def test_missing_customer_and_order_items_return_404(client):
    assert client.get(f"{API}/customers/999").status_code == 404
    assert client.get(f"{API}/customers/999/orders").status_code == 404
    assert client.get(f"{API}/orders/999/items").status_code == 404
    assert client.post(f"{API}/orders/999/cancel").status_code == 404
    assert client.get(f"{API}/products/999/inventory").status_code == 404


def test_invalid_status_value_returns_422(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)])
    assert client.patch(f"{API}/orders/{order['id']}/status", json={"status": "LOST"}).status_code == 422


def test_invalid_sort_field_returns_422(client):
    assert client.get(f"{API}/orders", params={"sort_by": "password"}).status_code == 422


def test_errors_do_not_leak_internals(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.empty, "quantity": 1}]})
    assert "Traceback" not in resp.text and "sqlalchemy" not in resp.text.lower()


def test_customer_list_is_paginated(client):
    for i in range(3):
        client.post(f"{API}/customers", json={"name": f"C{i}", "email": f"c{i}@example.com"})
    body = client.get(f"{API}/customers", params={"page_size": 2}).json()
    assert (len(body["items"]), body["total"], body["has_next"]) == (2, 3, True)


# ============================================================== B. known failing tests


@pytest.mark.known_bug("BUG-08")
def test_error_responses_share_one_structure(client, sample):
    not_found_http = client.patch(f"{API}/products/999", json={"name": "x"})  # router-raised 404
    not_found_domain = client.post(f"{API}/orders/999/cancel")  # service-raised 404
    validation = client.post(f"{API}/orders", json={"customer_id": "abc"})
    assert (not_found_http.status_code, not_found_domain.status_code, validation.status_code) == (404, 404, 422)
    shapes = {frozenset(r.json().keys()) for r in (not_found_http, not_found_domain, validation)}
    assert len(shapes) == 1, f"Inconsistent error shapes: {shapes}"


@pytest.mark.known_bug("BUG-09")
def test_create_order_returns_201(client, sample):
    resp = client.post(f"{API}/orders", json={"customer_id": sample.john, "items": [{"product_id": sample.mouse, "quantity": 1}]})
    assert resp.status_code == 201


@pytest.mark.known_bug("BUG-10")
def test_put_requires_full_representation(client, sample):
    order = create_order(client, sample.john, [(sample.mouse, 1)], discount="2.00")
    resp = client.put(f"{API}/orders/{order['id']}", json={"payment_status": "PAID"})
    assert resp.status_code == 422


@pytest.mark.known_bug("BUG-11")
def test_page_zero_is_rejected(client):
    assert client.get(f"{API}/orders", params={"page": 0}).status_code == 422


@pytest.mark.known_bug("BUG-11")
def test_non_positive_page_size_is_rejected(client):
    assert client.get(f"{API}/orders", params={"page_size": -5}).status_code == 422
    assert client.get(f"{API}/orders", params={"page_size": 0}).status_code == 422


@pytest.mark.known_bug("BUG-21")
def test_page_size_is_bounded(client):
    resp = client.get(f"{API}/orders", params={"page_size": 100000})
    assert resp.status_code == 422 or resp.json()["page_size"] <= 100


@pytest.mark.known_bug("BUG-12")
def test_missing_order_returns_404(client):
    resp = client.get(f"{API}/orders/999")
    assert resp.status_code == 404


@pytest.mark.known_bug("BUG-12")
def test_missing_product_returns_404(client):
    resp = client.get(f"{API}/products/999")
    assert resp.status_code == 404
