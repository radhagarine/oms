"""Order business logic: listing, creation, updates, status changes and cancellation."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Order, OrderItem, OrderStatus, PaymentStatus
from app.repositories import customer_repository, order_repository, product_repository
from app.schemas.order import MetricsSummary, OrderCreate, OrderSummary, OrderUpdate
from app.services import inventory_service, pricing_service, status_service
from app.services.order_mappers import to_summary
from app.utils.money import to_money

DISPLAY_DATE_FORMAT = "%m/%d/%Y %I:%M %p"
EDITABLE_STATUSES = {OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value}


@dataclass
class OrderListParams:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    status: str | None = None
    payment_status: str | None = None
    customer_id: int | None = None
    sort_by: str = "order_date"
    sort_order: str = "desc"
    date_from: date | None = None
    date_to: date | None = None


@dataclass
class OrderPage:
    items: list[OrderSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


# --------------------------------------------------------------------------- listing


def _sort_key(order: Order, sort_by: str):  # noqa: ANN202
    if sort_by in ("order_date", "created_at"):
        return getattr(order, sort_by).strftime(DISPLAY_DATE_FORMAT)
    if sort_by == "grand_total":
        return order.grand_total
    if sort_by == "status":
        return order.status
    return order.id


def list_orders(db: Session, params: OrderListParams) -> OrderPage:
    stmt = order_repository.base_orders_query()
    stmt = order_repository.apply_scope_filters(
        stmt,
        payment_status=params.payment_status,
        customer_id=params.customer_id,
        date_from=params.date_from,
        date_to=params.date_to,
    )
    count_stmt = stmt
    stmt = order_repository.apply_status_filter(stmt, params.status)
    stmt = order_repository.apply_search(stmt, params.search)

    orders = order_repository.fetch_orders(db, stmt)
    orders.sort(key=lambda o: _sort_key(o, params.sort_by), reverse=params.sort_order == "desc")

    start = (params.page - 1) * params.page_size
    page_orders = orders[start : start + params.page_size]

    total = order_repository.count_orders(db, count_stmt)
    total_pages = math.ceil(total / params.page_size) if params.page_size > 0 else 0
    has_next = params.page * params.page_size < order_repository.count_orders(db, count_stmt)
    has_previous = params.page > 1 and order_repository.count_orders(db, count_stmt) > 0

    return OrderPage(
        items=[to_summary(o) for o in page_orders],
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
    )


# --------------------------------------------------------------------------- retrieval


def get_order(db: Session, order_id: int) -> Order | None:
    return order_repository.get_order_detail(db, order_id)


def require_order(db: Session, order_id: int) -> Order:
    order = get_order(db, order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


# --------------------------------------------------------------------------- creation


def create_order(db: Session, payload: OrderCreate) -> Order:
    if customer_repository.get(db, payload.customer_id) is None:
        raise NotFoundError(f"Customer {payload.customer_id} not found")

    products = product_repository.get_many(db, [i.product_id for i in payload.items])
    items: list[OrderItem] = []
    for line in payload.items:
        product = products.get(line.product_id)
        if product is None:
            raise NotFoundError(f"Product {line.product_id} not found")
        if not product.is_active:
            raise ConflictError(f"Product {product.sku} is inactive and cannot be ordered")
        inventory_service.check_stock(product, line.quantity)
        items.append(
            OrderItem(
                product_id=product.id,
                quantity=line.quantity,
                unit_price=to_money(product.unit_price),
                line_total=pricing_service.line_total(product.unit_price, line.quantity),
            )
        )

    totals = pricing_service.calculate_totals(
        pricing_service.subtotal_of(i.line_total for i in items),
        payload.discount,
        payload.shipping_charge,
    )
    order = Order(
        customer_id=payload.customer_id,
        status=OrderStatus.PENDING.value,
        payment_status=payload.payment_status.value,
        subtotal=totals.subtotal,
        discount=totals.discount,
        tax=totals.tax,
        shipping_charge=totals.shipping_charge,
        grand_total=totals.grand_total,
        items=items,
    )
    db.add(order)
    db.commit()

    for line in payload.items:
        inventory_service.reserve(db, line.product_id, line.quantity)

    return require_order(db, order.id)


# --------------------------------------------------------------------------- updates


def update_order(db: Session, order_id: int, payload: OrderUpdate) -> Order:
    order = require_order(db, order_id)
    if order.status not in EDITABLE_STATUSES:
        raise ConflictError(f"Order in status {order.status} cannot be edited")

    changes = payload.model_dump(exclude_unset=True)

    if changes.get("payment_status") is not None:
        order.payment_status = payload.payment_status.value

    if payload.items:
        items_by_id = {i.id: i for i in order.items}
        for change in payload.items:
            item = items_by_id.get(change.id)
            if item is None:
                raise NotFoundError(f"Order item {change.id} not found on order {order_id}")
            inventory_service.adjust_for_quantity_change(
                db, item.product_id, change.quantity - item.quantity
            )
            item.quantity = change.quantity
            item.line_total = pricing_service.line_total(item.unit_price, change.quantity)

    if "discount" in changes or "shipping_charge" in changes:
        discount = payload.discount if payload.discount is not None else order.discount
        shipping = (
            payload.shipping_charge if payload.shipping_charge is not None else order.shipping_charge
        )
        totals = pricing_service.calculate_totals(order.subtotal, discount, shipping)
        order.discount = totals.discount
        order.shipping_charge = totals.shipping_charge
        order.tax = totals.tax
        order.grand_total = totals.grand_total

    db.commit()
    return require_order(db, order_id)


def change_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    order = require_order(db, order_id)
    target = new_status.value
    if target != order.status:
        status_service.validate_transition(order.status, target)

    if target == OrderStatus.CANCELLED.value:
        inventory_service.restore_order_inventory(db, order)
        if order.payment_status == PaymentStatus.PAID.value:
            order.payment_status = PaymentStatus.REFUNDED.value

    order.status = target
    db.commit()
    return require_order(db, order_id)


def cancel_order(db: Session, order_id: int) -> Order:
    order = require_order(db, order_id)
    if order.status != OrderStatus.CANCELLED.value:
        status_service.validate_transition(order.status, OrderStatus.CANCELLED.value)

    order.status = OrderStatus.CANCELLED.value
    if order.payment_status == PaymentStatus.PAID.value:
        order.payment_status = PaymentStatus.REFUNDED.value
    db.commit()
    return require_order(db, order_id)


# --------------------------------------------------------------------------- metrics


def metrics_summary(db: Session) -> MetricsSummary:
    stmt = select(
        func.count(Order.id),
        func.sum(case((Order.status == OrderStatus.PENDING.value, 1), else_=0)),
        func.sum(case((Order.status == OrderStatus.DELIVERED.value, 1), else_=0)),
        func.sum(case((Order.status == OrderStatus.CANCELLED.value, 1), else_=0)),
        func.sum(case((Order.status != OrderStatus.CANCELLED.value, Order.grand_total), else_=0)),
    )
    total, pending, delivered, cancelled, value = db.execute(stmt).one()
    return MetricsSummary(
        total_orders=total or 0,
        pending_orders=pending or 0,
        delivered_orders=delivered or 0,
        cancelled_orders=cancelled or 0,
        total_order_value=to_money(Decimal(str(value or 0))),
    )
