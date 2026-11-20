from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer


def get(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def find_by_email(db: Session, email: str) -> Customer | None:
    return db.scalars(select(Customer).where(func.lower(Customer.email) == email.lower())).first()


def list_customers(db: Session, *, offset: int, limit: int, search: str | None) -> tuple[list[Customer], int]:
    stmt = select(Customer)
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Customer.name).like(pattern) | func.lower(Customer.email).like(pattern))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(stmt.order_by(Customer.id).offset(offset).limit(limit)).all()
    return list(rows), total
