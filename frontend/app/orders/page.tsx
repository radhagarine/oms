"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import OrdersTable from "@/components/OrdersTable";
import { Card, ErrorBanner, Loading, Pager } from "@/components/ui";
import { api } from "@/services/api";
import { titleCase } from "@/services/format";
import { ORDER_STATUSES, PAYMENT_STATUSES, type OrderListQuery, type OrderSummary, type Page } from "@/services/types";

const DEFAULT_QUERY: OrderListQuery = {
  page: 1,
  page_size: 20,
  search: "",
  status: "",
  payment_status: "",
  sort_by: "order_date",
  sort_order: "desc",
};

export default function OrdersPage() {
  const [query, setQuery] = useState<OrderListQuery>(DEFAULT_QUERY);
  const [searchInput, setSearchInput] = useState("");
  const [result, setResult] = useState<Page<OrderSummary> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (q: OrderListQuery) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.listOrders(q));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(query);
  }, [query, load]);

  const update = (patch: Partial<OrderListQuery>) => setQuery((q) => ({ ...q, page: 1, ...patch }));

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    update({ search: searchInput.trim() });
  };

  return (
    <>
      <h1>Orders</h1>
      <Card>
        <form className="toolbar" onSubmit={onSearch}>
          <input
            placeholder="Search customer name…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Search"
          />
          <button type="submit">Search</button>
          <select value={query.status} onChange={(e) => update({ status: e.target.value as OrderListQuery["status"] })} aria-label="Status filter">
            <option value="">All statuses</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
          <select
            value={query.payment_status}
            onChange={(e) => update({ payment_status: e.target.value as OrderListQuery["payment_status"] })}
            aria-label="Payment filter"
          >
            <option value="">All payments</option>
            {PAYMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
          <select value={query.sort_by} onChange={(e) => update({ sort_by: e.target.value as OrderListQuery["sort_by"] })} aria-label="Sort by">
            <option value="order_date">Order date</option>
            <option value="grand_total">Grand total</option>
            <option value="status">Status</option>
            <option value="id">Order ID</option>
          </select>
          <button
            type="button"
            className="secondary"
            onClick={() => update({ sort_order: query.sort_order === "asc" ? "desc" : "asc" })}
          >
            {query.sort_order === "asc" ? "↑ Ascending" : "↓ Descending"}
          </button>
          <select value={query.page_size} onChange={(e) => update({ page_size: Number(e.target.value) })} aria-label="Page size">
            {[10, 20, 50].map((n) => (
              <option key={n} value={n}>
                {n} / page
              </option>
            ))}
          </select>
        </form>
        <ErrorBanner message={error} />
        {loading && !result ? <Loading /> : result && <OrdersTable orders={result.items} />}
        {result && (
          <Pager
            page={result.page}
            totalPages={result.total_pages}
            total={result.total}
            hasPrevious={result.has_previous}
            hasNext={result.has_next}
            onPrevious={() => setQuery((q) => ({ ...q, page: (q.page ?? 1) - 1 }))}
            onNext={() => setQuery((q) => ({ ...q, page: (q.page ?? 1) + 1 }))}
          />
        )}
      </Card>
    </>
  );
}
