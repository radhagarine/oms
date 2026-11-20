"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import OrdersTable from "@/components/OrdersTable";
import { Card, ErrorBanner, Loading } from "@/components/ui";
import { api } from "@/services/api";
import { formatMoney } from "@/services/format";
import type { MetricsSummary, OrderSummary } from "@/services/types";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [recent, setRecent] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.metrics(), api.listOrders({ page: 1, page_size: 8, sort_by: "order_date", sort_order: "desc" })])
      .then(([m, page]) => {
        setMetrics(m);
        setRecent(page.items);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const cards = metrics
    ? [
        { label: "Total orders", value: metrics.total_orders.toLocaleString() },
        { label: "Pending", value: metrics.pending_orders.toLocaleString() },
        { label: "Delivered", value: metrics.delivered_orders.toLocaleString() },
        { label: "Cancelled", value: metrics.cancelled_orders.toLocaleString() },
        { label: "Total order value", value: formatMoney(metrics.total_order_value) },
      ]
    : [];

  return (
    <>
      <h1>Dashboard</h1>
      <ErrorBanner message={error} />
      {!metrics && !error && <Loading />}
      <div className="grid">
        {cards.map((c) => (
          <div className="metric" key={c.label}>
            <div className="label">{c.label}</div>
            <div className="value">{c.value}</div>
          </div>
        ))}
      </div>
      <Card title="Recent orders">
        <OrdersTable orders={recent} />
        <p>
          <Link href="/orders">View all orders →</Link>
        </p>
      </Card>
    </>
  );
}
