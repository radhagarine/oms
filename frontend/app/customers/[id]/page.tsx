"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import OrdersTable from "@/components/OrdersTable";
import { Card, ErrorBanner, Loading } from "@/components/ui";
import { api } from "@/services/api";
import { formatDate, formatMoney } from "@/services/format";
import type { Customer, OrderSummary } from "@/services/types";

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = Number(params.id);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getCustomer(customerId), api.getCustomerOrders(customerId)])
      .then(([c, o]) => {
        setCustomer(c);
        setOrders(o);
      })
      .catch((e: Error) => setError(e.message));
  }, [customerId]);

  if (error) return <ErrorBanner message={error} />;
  if (!customer) return <Loading />;

  const lifetime = orders.filter((o) => o.status !== "CANCELLED").reduce((sum, o) => sum + Number(o.grand_total), 0);

  return (
    <>
      <p>
        <Link href="/customers">← Customers</Link>
      </p>
      <h1>{customer.name}</h1>
      <Card title="Customer details">
        <dl className="kv">
          <dt>Email</dt>
          <dd>{customer.email}</dd>
          <dt>Phone</dt>
          <dd>{customer.phone ?? "—"}</dd>
          <dt>Customer since</dt>
          <dd>{formatDate(customer.created_at)}</dd>
          <dt>Orders</dt>
          <dd>{orders.length}</dd>
          <dt>Lifetime value</dt>
          <dd>{formatMoney(lifetime)}</dd>
        </dl>
      </Card>
      <Card title="Order history">
        <OrdersTable orders={orders} showCustomer={false} />
      </Card>
    </>
  );
}
