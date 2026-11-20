from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentStatus
from app.schemas.customer import CustomerRead

Money = Decimal


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10_000)


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    items: list[OrderItemCreate] = Field(min_length=1)
    discount: Money = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    shipping_charge: Money = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    payment_status: PaymentStatus = PaymentStatus.UNPAID


class OrderItemUpdate(BaseModel):
    id: int
    quantity: int


class OrderUpdate(BaseModel):
    """Body for PUT /orders/{id}: full replacement of the editable order fields."""

    payment_status: PaymentStatus | None = None
    discount: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    shipping_charge: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    items: list[OrderItemUpdate] | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: Money
    line_total: Money


class OrderSummary(BaseModel):
    id: int
    customer_id: int
    customer_name: str | None
    order_date: datetime
    status: OrderStatus
    payment_status: PaymentStatus
    grand_total: Money
    item_count: int


class OrderDetail(BaseModel):
    id: int
    customer_id: int
    customer: CustomerRead | None
    order_date: datetime
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Money
    discount: Money
    tax: Money
    shipping_charge: Money
    grand_total: Money
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]


class MetricsSummary(BaseModel):
    total_orders: int
    pending_orders: int
    delivered_orders: int
    cancelled_orders: int
    total_order_value: Money
