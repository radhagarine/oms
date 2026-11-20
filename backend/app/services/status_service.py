"""Order status transition rules."""
from __future__ import annotations

from app.errors import InvalidStatusTransitionError
from app.models.order import OrderStatus

FULFILMENT_SEQUENCE: list[str] = [
    OrderStatus.PENDING.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
]


def validate_transition(current: str, new: str) -> None:
    """Raise InvalidStatusTransitionError if `current -> new` is not permitted."""
    if new == OrderStatus.CANCELLED.value:
        return
    if current == OrderStatus.CANCELLED.value:
        raise InvalidStatusTransitionError(f"Cannot change status of a {current} order")
    if FULFILMENT_SEQUENCE.index(new) <= FULFILMENT_SEQUENCE.index(current):
        raise InvalidStatusTransitionError(f"Cannot move order from {current} to {new}")
