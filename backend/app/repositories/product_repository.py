from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Product


def get(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_many(db: Session, product_ids: list[int]) -> dict[int, Product]:
    if not product_ids:
        return {}
    rows = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    return {p.id: p for p in rows}


def find_by_sku(db: Session, sku: str) -> Product | None:
    return db.scalars(select(Product).where(Product.sku == sku)).first()


def list_products(db: Session, *, search: str | None, active_only: bool) -> list[Product]:
    stmt = select(Product).order_by(Product.id)
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Product.name).like(pattern), func.lower(Product.sku).like(pattern))
        )
    return list(db.scalars(stmt).all())
