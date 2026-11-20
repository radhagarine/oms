"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Card, ErrorBanner, Loading, StatusBadge } from "@/components/ui";
import { api } from "@/services/api";
import { formatDateTime, formatMoney, titleCase } from "@/services/format";
import { ORDER_STATUSES, type OrderDetail, type OrderStatus } from "@/services/types";

const EDITABLE: OrderStatus[] = ["PENDING", "CONFIRMED"];
const TERMINAL: OrderStatus[] = ["DELIVERED", "CANCELLED"];

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const orderId = Number(params.id);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [nextStatus, setNextStatus] = useState<OrderStatus>("CONFIRMED");
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState(false);

  const apply = (o: OrderDetail) => {
    setOrder(o);
    // Default the status picker to the next step in the fulfilment sequence.
    setNextStatus(ORDER_STATUSES[ORDER_STATUSES.indexOf(o.status) + 1] ?? "CANCELLED");
    setQuantities(Object.fromEntries(o.items.map((i) => [i.id, i.quantity])));
  };

  const load = useCallback(async () => {
    try {
      const o = await api.getOrder(orderId);
      if (!o) setNotFound(true);
      else apply(o);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (action: () => Promise<OrderDetail>, success: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      apply(await action());
      setNotice(success);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (notFound) return <p>Order not found. <Link href="/orders">Back to orders</Link></p>;
  if (!order) return error ? <ErrorBanner message={error} /> : <Loading />;

  const quantitiesChanged = order.items.some((i) => quantities[i.id] !== i.quantity);
  const editable = EDITABLE.includes(order.status);

  return (
    <>
      <p>
        <Link href="/orders">← Orders</Link>
      </p>
      <h1>
        Order #{order.id} <StatusBadge value={order.status} /> <StatusBadge value={order.payment_status} />
      </h1>
      <ErrorBanner message={error} />
      {notice && <div className="notice">{notice}</div>}

      <div className="grid-2">
        <Card title="Customer">
          {order.customer ? (
            <dl className="kv">
              <dt>Name</dt>
              <dd>
                <Link href={`/customers/${order.customer.id}`}>{order.customer.name}</Link>
              </dd>
              <dt>Email</dt>
              <dd>{order.customer.email}</dd>
              <dt>Phone</dt>
              <dd>{order.customer.phone ?? "—"}</dd>
            </dl>
          ) : (
            <p className="muted">Customer {order.customer_id} not found.</p>
          )}
        </Card>
        <Card title="Order">
          <dl className="kv">
            <dt>Order date</dt>
            <dd>{formatDateTime(order.order_date)}</dd>
            <dt>Last updated</dt>
            <dd>{formatDateTime(order.updated_at)}</dd>
          </dl>
          {!TERMINAL.includes(order.status) && (
            <div className="row-actions" style={{ marginTop: "1rem" }}>
              <select value={nextStatus} onChange={(e) => setNextStatus(e.target.value as OrderStatus)} aria-label="New status">
                {ORDER_STATUSES.filter((s) => s !== order.status).map((s) => (
                  <option key={s} value={s}>
                    {titleCase(s)}
                  </option>
                ))}
              </select>
              <button disabled={busy} onClick={() => run(() => api.changeStatus(order.id, nextStatus), `Status changed to ${titleCase(nextStatus)}`)}>
                Update status
              </button>
            </div>
          )}
          {order.status !== "CANCELLED" && (
            <div className="row-actions" style={{ marginTop: "0.75rem" }}>
              <button
                className="danger"
                disabled={busy}
                onClick={() => {
                  if (window.confirm(`Cancel order #${order.id}?`)) run(() => api.cancelOrder(order.id), "Order cancelled");
                }}
              >
                Cancel order
              </button>
            </div>
          )}
        </Card>
      </div>

      <Card title="Items">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>SKU</th>
              <th className="num">Unit price</th>
              <th className="num">Quantity</th>
              <th className="num">Line total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((i) => (
              <tr key={i.id}>
                <td>{i.product_name}</td>
                <td>{i.sku}</td>
                <td className="num">{formatMoney(i.unit_price)}</td>
                <td className="num">
                  {editable ? (
                    <input
                      className="qty"
                      type="number"
                      value={quantities[i.id] ?? i.quantity}
                      onChange={(e) => setQuantities((q) => ({ ...q, [i.id]: Number(e.target.value) }))}
                      aria-label={`Quantity for ${i.product_name}`}
                    />
                  ) : (
                    i.quantity
                  )}
                </td>
                <td className="num">{formatMoney(i.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {editable && (
          <div className="row-actions" style={{ marginTop: "0.75rem" }}>
            <button
              disabled={busy || !quantitiesChanged}
              onClick={() =>
                run(
                  () =>
                    api.updateOrder(order.id, {
                      payment_status: order.payment_status,
                      discount: order.discount,
                      shipping_charge: order.shipping_charge,
                      items: order.items.map((i) => ({ id: i.id, quantity: quantities[i.id] ?? i.quantity })),
                    }),
                  "Quantities updated",
                )
              }
            >
              Save quantities
            </button>
          </div>
        )}
      </Card>

      <Card title="Totals">
        <dl className="kv totals" style={{ maxWidth: 360, marginLeft: "auto" }}>
          <dt>Subtotal</dt>
          <dd>{formatMoney(order.subtotal)}</dd>
          <dt>Discount</dt>
          <dd>−{formatMoney(order.discount)}</dd>
          <dt>Tax</dt>
          <dd>{formatMoney(order.tax)}</dd>
          <dt>Shipping</dt>
          <dd>{formatMoney(order.shipping_charge)}</dd>
          <dt className="grand">Grand total</dt>
          <dd className="grand">{formatMoney(order.grand_total)}</dd>
        </dl>
      </Card>
    </>
  );
}
