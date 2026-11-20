from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    inventory_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    inventory_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    unit_price: Decimal
    inventory_quantity: int
    is_active: bool
    created_at: datetime


class InventoryRead(BaseModel):
    product_id: int
    sku: str
    inventory_quantity: int
    is_active: bool
