"""Convert ORM orders into API response schemas."""
from __future__ import annotations

from app.models import Order, OrderItem
from app.schemas.customer import CustomerRead
from app.schemas.order import OrderDetail, OrderItemRead, OrderSummary


def to_item_read(item: OrderItem) -> OrderItemRead:
    return OrderItemRead(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product.name if item.product else "",
        sku=item.product.sku if item.product else "",
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=item.line_total,
    )


def to_summary(order: Order) -> OrderSummary:
    customer = order.customer
    return OrderSummary(
        id=order.id,
        customer_id=order.customer_id,
        customer_name=customer.name if customer else None,
        order_date=order.order_date,
        status=order.status,
        payment_status=order.payment_status,
        grand_total=order.grand_total,
        item_count=len(order.items),
    )


def to_detail(order: Order) -> OrderDetail:
    return OrderDetail(
        id=order.id,
        customer_id=order.customer_id,
        customer=CustomerRead.model_validate(order.customer) if order.customer else None,
        order_date=order.order_date,
        status=order.status,
        payment_status=order.payment_status,
        subtotal=order.subtotal,
        discount=order.discount,
        tax=order.tax,
        shipping_charge=order.shipping_charge,
        grand_total=order.grand_total,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[to_item_read(i) for i in order.items],
    )
