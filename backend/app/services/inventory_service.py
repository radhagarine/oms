"""Product-level inventory reservation and restoration."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import InsufficientInventoryError, NotFoundError
from app.models import Order, Product


def _load_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


def check_stock(product: Product, quantity: int) -> None:
    if product.inventory_quantity < quantity:
        raise InsufficientInventoryError(
            f"Insufficient inventory for product {product.sku}: "
            f"requested {quantity}, available {product.inventory_quantity}"
        )


def reserve(db: Session, product_id: int, quantity: int) -> None:
    """Reserve `quantity` units of a product and persist the new stock level."""
    product = _load_product(db, product_id)
    check_stock(product, quantity)
    product.inventory_quantity = product.inventory_quantity - quantity
    db.commit()


def adjust_for_quantity_change(db: Session, product_id: int, delta: int) -> None:
    """Apply a change in ordered quantity (positive delta reserves more stock). Caller commits."""
    product = _load_product(db, product_id)
    if delta > 0:
        check_stock(product, delta)
    product.inventory_quantity = product.inventory_quantity - delta


def restore_order_inventory(db: Session, order: Order) -> None:
    """Return every reserved unit of an order to stock. Caller commits."""
    for item in order.items:
        product = _load_product(db, item.product_id)
        product.inventory_quantity = product.inventory_quantity + item.quantity


def get_inventory(db: Session, product_id: int) -> Product:
    return _load_product(db, product_id)
