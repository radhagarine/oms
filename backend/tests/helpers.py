from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Order, OrderItem


def insert_order(
    db: Session,
    customer_id: int,
    product_id: int,
    *,
    status: str = "PENDING",
    payment_status: str = "UNPAID",
    order_date: datetime | None = None,
    quantity: int = 1,
    unit_price: Decimal = Decimal("10.00"),
) -> Order:
    """Insert a historical order directly (bypassing services and inventory)."""
    when = order_date or datetime(2026, 1, 1, 12, 0)
    line = (unit_price * quantity).quantize(Decimal("0.01"))
    order = Order(
        customer_id=customer_id,
        order_date=when,
        status=status,
        payment_status=payment_status,
        subtotal=line,
        discount=Decimal("0"),
        tax=Decimal("0"),
        shipping_charge=Decimal("0"),
        grand_total=line,
        created_at=when,
        updated_at=when,
        items=[OrderItem(product_id=product_id, quantity=quantity, unit_price=unit_price, line_total=line)],
    )
    db.add(order)
    db.commit()
    return order
