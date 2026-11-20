"""Query-count, execution-plan and index measurements (category C).

Measurement tests print baseline numbers (run with `pytest -s` to see them) and pass.
Tests marked known_bug assert the expected optimised behaviour and fail while the
defect is present. Larger-scale benchmarks live in scripts/benchmark_*.py.
"""
from __future__ import annotations

import pytest
from sqlalchemy import event, text

from app.models import Order
from app.seed import seed
from app.utils.query_counter import count_queries
from tests.conftest import API

pytestmark = pytest.mark.perf

CANONICAL_LISTING_SQL = (
    "SELECT * FROM orders WHERE status = 'CONFIRMED' AND payment_status = 'PAID' "
    "ORDER BY order_date DESC LIMIT 20"
)


@pytest.fixture
def seeded(db):
    return seed(db, customers=50, orders=200)


def _list_with_metrics(client, engine, **params) -> tuple[dict, list[str], int]:
    loaded = {"n": 0}

    def on_load(_target, _ctx):
        loaded["n"] += 1

    event.listen(Order, "load", on_load)
    try:
        with count_queries(engine) as log:
            resp = client.get(f"{API}/orders", params=params)
    finally:
        event.remove(Order, "load", on_load)
    assert resp.status_code == 200, resp.text
    return resp.json(), log.statements, loaded["n"]


def _query_plan(engine, sql: str) -> list[str]:
    with engine.connect() as conn:
        return [row[-1] for row in conn.execute(text(f"EXPLAIN QUERY PLAN {sql}"))]


def _orders_indexes(engine) -> dict[str, list[str]]:
    with engine.connect() as conn:
        names = [r[1] for r in conn.execute(text("PRAGMA index_list('orders')")) if r[3] == "c"]
        return {n: [c[2] for c in conn.execute(text(f"PRAGMA index_info('{n}')"))] for n in names}


# ============================================================== baseline measurements (pass)


def test_baseline_query_counts_by_page_size(client, engine, seeded):
    rows = []
    for size in (5, 20, 50):
        body, statements, loaded = _list_with_metrics(client, engine, page_size=size)
        rows.append((size, len(body["items"]), len(statements), loaded))
    print("\n[BUG-18/19] page_size | returned | SQL statements | Order rows loaded")
    for r in rows:
        print(f"            {r[0]:>9} | {r[1]:>8} | {r[2]:>14} | {r[3]:>17}")
    assert all(r[1] == r[0] for r in rows)


def test_baseline_canonical_query_plan_and_indexes(engine, seeded):
    plan = _query_plan(engine, CANONICAL_LISTING_SQL)
    print("\n[BUG-01] EXPLAIN QUERY PLAN:", *plan, sep="\n  ")
    print("[BUG-20] orders indexes:", _orders_indexes(engine))
    assert plan


def test_canonical_query_returns_correct_rows(engine, seeded):
    with engine.connect() as conn:
        rows = conn.execute(text(CANONICAL_LISTING_SQL)).mappings().all()
    assert rows and all(r["status"] == "CONFIRMED" and r["payment_status"] == "PAID" for r in rows)
    dates = [r["order_date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


# ============================================================== known failing tests


@pytest.mark.known_bug("BUG-18")
def test_listing_query_count_is_bounded(client, engine, seeded):
    _, small, _ = _list_with_metrics(client, engine, page_size=5)
    _, large, _ = _list_with_metrics(client, engine, page_size=50)
    assert len(large) <= len(small) + 1, f"{len(small)} queries for 5 orders vs {len(large)} for 50"


@pytest.mark.known_bug("BUG-19")
def test_listing_loads_only_requested_page(client, engine, seeded):
    body, statements, loaded = _list_with_metrics(client, engine, page_size=10, status="DELIVERED")
    assert len(body["items"]) == 10
    assert loaded <= 10, f"{loaded} Order rows materialised to return 10"
    order_selects = [s for s in statements if "FROM orders" in s and "count(" not in s.lower()]
    assert any("LIMIT" in s.upper() for s in order_selects), "pagination not pushed to SQL"


@pytest.mark.known_bug("BUG-22")
def test_listing_runs_single_count_query(client, engine, seeded):
    _, statements, _ = _list_with_metrics(client, engine, page_size=20, status="PENDING")
    counts = [s for s in statements if "count(" in s.lower()]
    assert len(counts) <= 1, f"{len(counts)} count queries executed"


@pytest.mark.known_bug("BUG-01")
def test_canonical_listing_query_avoids_temp_sort(engine, seeded):
    plan = " | ".join(_query_plan(engine, CANONICAL_LISTING_SQL))
    assert "TEMP B-TREE" not in plan.upper(), plan


@pytest.mark.known_bug("BUG-20")
def test_orders_table_has_no_redundant_indexes(engine):
    indexes = _orders_indexes(engine)
    redundant = [
        (a, b)
        for a, cols_a in indexes.items()
        for b, cols_b in indexes.items()
        if a != b and len(cols_a) < len(cols_b) and cols_b[: len(cols_a)] == cols_a
    ]
    assert not redundant, f"Left-prefix-redundant indexes: {redundant}"
