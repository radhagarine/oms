import Link from "next/link";
import type { OrderSummary } from "@/services/types";
import { formatDateTime, formatMoney } from "@/services/format";
import { StatusBadge } from "./ui";

export default function OrdersTable({ orders, showCustomer = true }: { orders: OrderSummary[]; showCustomer?: boolean }) {
  if (orders.length === 0) return <p className="muted">No orders found.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Order</th>
          {showCustomer && <th>Customer</th>}
          <th>Date</th>
          <th>Status</th>
          <th>Payment</th>
          <th className="num">Items</th>
          <th className="num">Total</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id}>
            <td>
              <Link href={`/orders/${o.id}`}>#{o.id}</Link>
            </td>
            {showCustomer && (
              <td>
                <Link href={`/customers/${o.customer_id}`}>{o.customer_name ?? `Customer ${o.customer_id}`}</Link>
              </td>
            )}
            <td>{formatDateTime(o.order_date)}</td>
            <td>
              <StatusBadge value={o.status} />
            </td>
            <td>
              <StatusBadge value={o.payment_status} />
            </td>
            <td className="num">{o.item_count}</td>
            <td className="num">{formatMoney(o.grand_total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
