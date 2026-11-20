"""Deterministic seed data builders (used by scripts/seed_data.py, tests and benchmarks)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Customer, Order, OrderItem, OrderStatus, PaymentStatus, Product
from app.services import pricing_service
from app.utils.money import to_money

SEED = 42
BASE_DATE = datetime(2025, 1, 1, 9, 0, 0)
DATE_SPAN_DAYS = 660  # Jan 2025 -> Oct 2026

FIRST_NAMES = [
    "John", "Priya", "Maria", "Wei", "Ahmed", "Olivia", "Liam", "Sofia", "Noah", "Aisha",
    "Ethan", "Mei", "Lucas", "Fatima", "Mateo", "Hana", "Arjun", "Emma", "Diego", "Yuki",
    "Johnny", "Grace", "Omar", "Chloe", "Ravi",
]
LAST_NAMES = ["Smith", "Patel", "Garcia", "Chen", "Khan", "Johnson", "Nguyen", "Rossi", "Kim", "Brown"]

PRODUCT_NAMES = [
    "Wireless Mouse", "Mechanical Keyboard", "USB-C Hub", "27in Monitor", "Laptop Stand",
    "Noise-Cancelling Headphones", "Webcam HD", "Desk Lamp", "Ergonomic Chair", "Standing Desk",
    "Portable SSD 1TB", "Bluetooth Speaker", "Phone Charger", "HDMI Cable", "Mouse Pad XL",
    "Smartwatch", "Fitness Tracker", "Tablet Case", "Stylus Pen", "Microphone",
    "Ring Light", "Cable Organizer", "Laptop Sleeve", "Wireless Earbuds", "Power Bank",
    "Router", "Ethernet Switch", "Graphics Tablet", "Docking Station", "Screen Cleaner Kit",
]

STATUS_CYCLE = [
    OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING,
    OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.DELIVERED, OrderStatus.CANCELLED,
]


def _payment_for(status: OrderStatus, rng: random.Random) -> PaymentStatus:
    if status == OrderStatus.PENDING:
        return PaymentStatus.UNPAID
    if status == OrderStatus.CANCELLED:
        return rng.choice([PaymentStatus.UNPAID, PaymentStatus.REFUNDED])
    if status == OrderStatus.CONFIRMED:
        return rng.choice([PaymentStatus.UNPAID, PaymentStatus.PAID])
    return PaymentStatus.PAID


def build_customers(count: int) -> list[Customer]:
    customers = []
    for i in range(count):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i // len(FIRST_NAMES) + i) % len(LAST_NAMES)]
        customers.append(
            Customer(
                name=f"{first} {last}",
                email=f"{first.lower()}.{last.lower()}{i + 1}@example.com",
                phone=f"+1-555-{1000 + i:04d}",
                created_at=BASE_DATE - timedelta(days=60 - i),
            )
        )
    return customers


def build_products(rng: random.Random) -> list[Product]:
    products = []
    for i, name in enumerate(PRODUCT_NAMES):
        if i in (4, 13, 22):
            inventory = 0  # out of stock
        else:
            inventory = rng.choice([5, 12, 25, 40, 75, 120, 250])
        products.append(
            Product(
                name=name,
                sku=f"SKU-{1001 + i}",
                unit_price=to_money(Decimal(rng.randint(500, 45000)) / 100),
                inventory_quantity=inventory,
                is_active=i not in (27, 29),
                created_at=BASE_DATE - timedelta(days=90),
            )
        )
    return products


def build_orders(
    rng: random.Random, customers: list[Customer], products: list[Product], count: int
) -> list[Order]:
    orderable = [p for p in products if p.is_active]
    orders = []
    for i in range(count):
        status = STATUS_CYCLE[i % len(STATUS_CYCLE)]
        order_date = BASE_DATE + timedelta(
            days=rng.randint(0, DATE_SPAN_DAYS), hours=rng.randint(0, 12), minutes=rng.randint(0, 59)
        )
        chosen = rng.sample(orderable, k=rng.choice([1, 2, 2, 3]))
        items = []
        for product in chosen:
            qty = rng.randint(1, 5)
            items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.unit_price,
                    line_total=pricing_service.line_total(product.unit_price, qty),
                )
            )
        subtotal = pricing_service.subtotal_of(it.line_total for it in items)
        discount = rng.choice([Decimal("0"), Decimal("0"), Decimal("5.00"), Decimal("10.00")])
        discount = min(discount, subtotal)
        shipping = rng.choice([Decimal("0"), Decimal("4.99"), Decimal("9.99")])
        totals = pricing_service.calculate_totals(subtotal, discount, shipping)
        orders.append(
            Order(
                customer_id=(customers[i] if i < len(customers) else rng.choice(customers)).id,
                order_date=order_date,
                status=status.value,
                payment_status=_payment_for(status, rng).value,
                subtotal=totals.subtotal,
                discount=totals.discount,
                tax=totals.tax,
                shipping_charge=totals.shipping_charge,
                grand_total=totals.grand_total,
                created_at=order_date,
                updated_at=order_date,
                items=items,
            )
        )
    return orders


def seed(session: Session, *, customers: int = 50, orders: int = 200) -> dict[str, int]:
    rng = random.Random(SEED)
    customer_rows = build_customers(customers)
    product_rows = build_products(rng)
    session.add_all(customer_rows + product_rows)
    session.flush()
    order_rows = build_orders(rng, customer_rows, product_rows, orders)
    session.add_all(order_rows)
    session.commit()
    return {
        "customers": len(customer_rows),
        "products": len(product_rows),
        "orders": len(order_rows),
        "order_items": sum(len(o.items) for o in order_rows),
    }
