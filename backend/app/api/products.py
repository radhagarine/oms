from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import product_repository
from app.schemas.product import InventoryRead, ProductCreate, ProductRead, ProductUpdate
from app.services import catalog_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = None, active_only: bool = False, db: Session = Depends(get_db)
) -> list[ProductRead]:
    products = product_repository.list_products(db, search=search, active_only=active_only)
    return [ProductRead.model_validate(p) for p in products]


@router.get("/{product_id}", response_model=ProductRead | None)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead | None:
    product = product_repository.get(db, product_id)
    return ProductRead.model_validate(product) if product else None


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    return ProductRead.model_validate(catalog_service.create_product(db, payload))


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> ProductRead:
    product = product_repository.get(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return ProductRead.model_validate(catalog_service.update_product(db, product, payload))


@router.get("/{product_id}/inventory", response_model=InventoryRead)
def get_inventory(product_id: int, db: Session = Depends(get_db)) -> InventoryRead:
    product = product_repository.get(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return InventoryRead(
        product_id=product.id,
        sku=product.sku,
        inventory_quantity=product.inventory_quantity,
        is_active=product.is_active,
    )
