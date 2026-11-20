"""Product and customer business logic."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Customer, Order, Product
from app.repositories import customer_repository, order_repository, product_repository
from app.schemas.customer import CustomerCreate
from app.schemas.product import ProductCreate, ProductUpdate


# --------------------------------------------------------------------------- products


def create_product(db: Session, payload: ProductCreate) -> Product:
    if product_repository.find_by_sku(db, payload.sku) is not None:
        raise ConflictError(f"SKU {payload.sku} already exists")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


# --------------------------------------------------------------------------- customers


def create_customer(db: Session, payload: CustomerCreate) -> Customer:
    if customer_repository.find_by_email(db, payload.email) is not None:
        raise ConflictError(f"A customer with email {payload.email} already exists")
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def customer_orders(db: Session, customer_id: int) -> list[Order]:
    if customer_repository.get(db, customer_id) is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return order_repository.orders_for_customer(db, customer_id)
