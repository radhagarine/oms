"""Model relationships and database-level integrity constraints."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Customer, Order, OrderItem, Product
from tests.helpers import insert_order

# ============================================================== A. passing tests


def test_order_relationships_load(db, sample):
    order = insert_order(db, sample.john, sample.mouse, quantity=2)
    db.expire_all()
    loaded = db.get(Order, order.id)
    assert loaded.customer.name == "John Smith"
    assert loaded.items[0].product.sku == "SKU-M"
    assert len(db.get(Customer, sample.john).orders) == 1


def test_deleting_order_cascades_items(db, sample):
    order = insert_order(db, sample.john, sample.mouse)
    db.delete(order)
    db.commit()
    assert db.scalar(select(func.count(OrderItem.id))) == 0


def test_item_with_unknown_product_is_rejected(db, sample):
    order = insert_order(db, sample.john, sample.mouse)
    db.add(OrderItem(order_id=order.id, product_id=9999, quantity=1, unit_price=Decimal("1"), line_total=Decimal("1")))
    with pytest.raises(IntegrityError):
        db.commit()


def test_negative_price_is_rejected_by_database(db):
    db.add(Product(name="Bad", sku="BAD-1", unit_price=Decimal("-1.00"), inventory_quantity=1))
    with pytest.raises(IntegrityError):
        db.commit()


def test_duplicate_customer_email_rejected_by_database(db, sample):
    db.add(Customer(name="Clone", email="jsmith@example.com"))
    with pytest.raises(IntegrityError):
        db.commit()


# ============================================================== B. known failing tests (BUG-16)


@pytest.mark.known_bug("BUG-16")
def test_duplicate_sku_rejected_by_database(db, sample):
    db.add(Product(name="Mouse copy", sku="SKU-M", unit_price=Decimal("1.00"), inventory_quantity=1))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.known_bug("BUG-16")
def test_negative_inventory_rejected_by_database(db, sample):
    product = db.get(Product, sample.mouse)
    product.inventory_quantity = -3
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.known_bug("BUG-16")
def test_non_positive_item_quantity_rejected_by_database(db, sample):
    order = insert_order(db, sample.john, sample.mouse)
    db.add(OrderItem(order_id=order.id, product_id=sample.mouse, quantity=0, unit_price=Decimal("1"), line_total=Decimal("0")))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.known_bug("BUG-16")
def test_order_with_unknown_customer_rejected_by_database(db, sample):
    with pytest.raises(IntegrityError):
        insert_order(db, 9999, sample.mouse)
