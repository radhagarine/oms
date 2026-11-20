"""Database access for orders."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, Order, OrderItem


def get_order_detail(db: Session, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
    )
    return db.scalars(stmt).first()


def base_orders_query() -> Select:
    return select(Order)


def apply_scope_filters(
    stmt: Select,
    *,
    payment_status: str | None,
    customer_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> Select:
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if date_from:
        stmt = stmt.where(Order.order_date >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Order.order_date <= datetime.combine(date_to, time.max))
    return stmt


def apply_status_filter(stmt: Select, status: str | None) -> Select:
    if status:
        stmt = stmt.where(Order.status == status)
    return stmt


def apply_search(stmt: Select, search: str | None) -> Select:
    if not search:
        return stmt
    pattern = f"%{search}%"
    return stmt.join(Customer, Customer.id == Order.customer_id).where(Customer.name.like(pattern))


def fetch_orders(db: Session, stmt: Select) -> list[Order]:
    return list(db.scalars(stmt).all())


def count_orders(db: Session, stmt: Select) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(db.scalar(count_stmt) or 0)


def orders_for_customer(db: Session, customer_id: int) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .order_by(Order.order_date.desc())
    )
    return list(db.scalars(stmt).all())
