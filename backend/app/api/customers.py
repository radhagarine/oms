from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import customer_repository
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerRead
from app.schemas.order import OrderSummary
from app.services import catalog_service
from app.services.order_mappers import to_summary

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerRead])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
) -> Page[CustomerRead]:
    rows, total = customer_repository.list_customers(
        db, offset=(page - 1) * page_size, limit=page_size, search=search
    )
    total_pages = math.ceil(total / page_size)
    return Page[CustomerRead](
        items=[CustomerRead.model_validate(c) for c in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> CustomerRead:
    customer = customer_repository.get(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return CustomerRead.model_validate(customer)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> CustomerRead:
    return CustomerRead.model_validate(catalog_service.create_customer(db, payload))


@router.get("/{customer_id}/orders", response_model=list[OrderSummary])
def get_customer_orders(customer_id: int, db: Session = Depends(get_db)) -> list[OrderSummary]:
    return [to_summary(o) for o in catalog_service.customer_orders(db, customer_id)]
