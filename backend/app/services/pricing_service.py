"""Order monetary calculations. All values are Decimal and rounded to cents."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.errors import BusinessValidationError
from app.utils.money import to_money

TAX_RATE = Decimal("0.08")


@dataclass(frozen=True)
class OrderTotals:
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    shipping_charge: Decimal
    grand_total: Decimal


def line_total(unit_price: Decimal, quantity: int) -> Decimal:
    return to_money(unit_price * quantity)


def subtotal_of(line_totals: Iterable[Decimal]) -> Decimal:
    return to_money(sum(line_totals, Decimal("0")))


def calculate_totals(subtotal: Decimal, discount: Decimal, shipping_charge: Decimal) -> OrderTotals:
    """Tax is charged on the discounted subtotal."""
    subtotal = to_money(subtotal)
    discount = to_money(discount)
    shipping_charge = to_money(shipping_charge)
    if discount < 0 or shipping_charge < 0:
        raise BusinessValidationError("Discount and shipping charge must be non-negative")

    tax = to_money((subtotal - discount) * TAX_RATE)
    grand_total = to_money(subtotal - discount + tax)
    if grand_total < 0:
        raise BusinessValidationError("Grand total cannot be negative")

    return OrderTotals(
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        shipping_charge=shipping_charge,
        grand_total=grand_total,
    )
