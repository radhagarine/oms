"""Deterministic concurrency harness for inventory reservation (BUG-14).

Instead of relying on timing, a threading.Barrier is inserted right after each thread has
read and checked the stock level. Both threads are therefore guaranteed to have observed
the same "available" quantity before either one writes, which is exactly the interleaving
that a read-check-write implementation cannot handle. A correct implementation (atomic
conditional UPDATE or row locking) is unaffected by the barrier: if it no longer calls
`check_stock`, the barrier is simply never reached.

SQLite note: SQLite serialises writers with a database-level lock, so true parallel writes
never happen; the lost update occurs because the *decision* is made on a stale read.
PostgreSQL would additionally require SELECT ... FOR UPDATE or a conditional UPDATE.
"""
from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.errors import AppError
from app.models import Order, Product
from app.schemas.order import OrderCreate
from app.services import inventory_service, order_service

pytestmark = pytest.mark.perf


def _barrier_after_check(monkeypatch, parties: int) -> None:
    barrier = threading.Barrier(parties)
    original = inventory_service.check_stock

    def check_then_wait(product, quantity):
        original(product, quantity)
        try:
            barrier.wait(timeout=5)
        except threading.BrokenBarrierError:
            pass

    monkeypatch.setattr(inventory_service, "check_stock", check_then_wait, raising=False)


def _run_concurrently(target, n: int) -> list[str]:
    results: list[str] = []
    lock = threading.Lock()

    def runner(i: int) -> None:
        try:
            target(i)
            outcome = "ok"
        except AppError as exc:
            outcome = f"rejected: {exc.message}"
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=runner, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


@pytest.mark.known_bug("BUG-14")
def test_concurrent_reservations_never_oversell(session_factory, sample, monkeypatch):
    _barrier_after_check(monkeypatch, parties=2)

    def reserve(_i: int) -> None:
        with session_factory() as session:
            inventory_service.reserve(session, sample.keyboard, 3)  # stock is 5
            session.commit()

    results = _run_concurrently(reserve, 2)
    successes = results.count("ok")
    with session_factory() as session:
        remaining = session.get(Product, sample.keyboard).inventory_quantity

    print(f"\n[BUG-14] reserve() results={results} remaining={remaining}")
    assert successes * 3 <= 5, f"{successes} reservations of 3 succeeded against stock of 5"
    assert remaining == 5 - 3 * successes


@pytest.mark.known_bug("BUG-14")
def test_concurrent_order_creation_never_oversells(session_factory, sample, monkeypatch):
    _barrier_after_check(monkeypatch, parties=2)
    payload = OrderCreate(customer_id=sample.john, items=[{"product_id": sample.keyboard, "quantity": 4}])

    def create(_i: int) -> None:
        with session_factory() as session:
            order_service.create_order(session, payload)

    results = _run_concurrently(create, 2)
    successes = results.count("ok")
    with session_factory() as session:
        remaining = session.get(Product, sample.keyboard).inventory_quantity
        orders = session.scalar(select(func.count(Order.id)))
        reserved = session.scalar(select(func.coalesce(func.sum(Order.subtotal), 0)))

    print(f"\n[BUG-14] create_order() results={results} remaining={remaining} orders={orders}")
    assert successes <= 1
    assert orders == successes
    assert remaining == 5 - 4 * successes
    assert Decimal(str(reserved)) == Decimal("102.00") * successes
