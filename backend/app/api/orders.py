from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OrderStatus, PaymentStatus
from app.schemas.common import Page
from app.schemas.order import (
    MetricsSummary,
    OrderCreate,
    OrderDetail,
    OrderItemRead,
    OrderStatusUpdate,
    OrderSummary,
    OrderUpdate,
)
from app.services import order_service
from app.services.order_mappers import to_detail, to_item_read

router = APIRouter(prefix="/orders", tags=["orders"])
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])

SortField = Literal["order_date", "created_at", "grand_total", "status", "id"]


@router.get("", response_model=Page[OrderSummary])
def list_orders(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    customer_id: int | None = None,
    sort_by: SortField = "order_date",
    sort_order: Literal["asc", "desc"] = "desc",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> Page[OrderSummary]:
    params = order_service.OrderListParams(
        page=page,
        page_size=page_size,
        search=search or None,
        status=status.value if status else None,
        payment_status=payment_status.value if payment_status else None,
        customer_id=customer_id,
        sort_by=sort_by,
        sort_order=sort_order,
        date_from=date_from,
        date_to=date_to,
    )
    result = order_service.list_orders(db, params)
    return Page[OrderSummary](**result.__dict__)


@router.get("/{order_id}", response_model=OrderDetail | None)
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderDetail | None:
    order = order_service.get_order(db, order_id)
    return to_detail(order) if order else None


@router.post("", response_model=OrderDetail)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderDetail:
    return to_detail(order_service.create_order(db, payload))


@router.put("/{order_id}", response_model=OrderDetail)
def replace_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)) -> OrderDetail:
    """Replace the editable fields of an order (payment_status, discount, shipping_charge, items)."""
    return to_detail(order_service.update_order(db, order_id, payload))


@router.patch("/{order_id}/status", response_model=OrderDetail)
def change_order_status(
    order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)
) -> OrderDetail:
    return to_detail(order_service.change_status(db, order_id, payload.status))


@router.post("/{order_id}/cancel", response_model=OrderDetail)
def cancel_order(order_id: int, db: Session = Depends(get_db)) -> OrderDetail:
    return to_detail(order_service.cancel_order(db, order_id))


@router.get("/{order_id}/items", response_model=list[OrderItemRead])
def get_order_items(order_id: int, db: Session = Depends(get_db)) -> list[OrderItemRead]:
    order = order_service.require_order(db, order_id)
    return [to_item_read(i) for i in order.items]


@metrics_router.get("/summary", response_model=MetricsSummary)
def metrics_summary(db: Session = Depends(get_db)) -> MetricsSummary:
    return order_service.metrics_summary(db)
