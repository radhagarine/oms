export type OrderStatus = "PENDING" | "CONFIRMED" | "PROCESSING" | "SHIPPED" | "DELIVERED" | "CANCELLED";
export type PaymentStatus = "UNPAID" | "PAID" | "REFUNDED";

export const ORDER_STATUSES: OrderStatus[] = ["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"];
export const PAYMENT_STATUSES: PaymentStatus[] = ["UNPAID", "PAID", "REFUNDED"];

/** Monetary values are serialised by the API as decimal strings. */
export type Money = string;

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  unit_price: Money;
  inventory_quantity: number;
  is_active: boolean;
  created_at: string;
}

export interface OrderSummary {
  id: number;
  customer_id: number;
  customer_name: string | null;
  order_date: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  grand_total: Money;
  item_count: number;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: Money;
  line_total: Money;
}

export interface OrderDetail {
  id: number;
  customer_id: number;
  customer: Customer | null;
  order_date: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  subtotal: Money;
  discount: Money;
  tax: Money;
  shipping_charge: Money;
  grand_total: Money;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface MetricsSummary {
  total_orders: number;
  pending_orders: number;
  delivered_orders: number;
  cancelled_orders: number;
  total_order_value: Money;
}

export interface OrderListQuery {
  page?: number;
  page_size?: number;
  search?: string;
  status?: OrderStatus | "";
  payment_status?: PaymentStatus | "";
  customer_id?: number;
  sort_by?: "order_date" | "created_at" | "grand_total" | "status" | "id";
  sort_order?: "asc" | "desc";
  date_from?: string;
  date_to?: string;
}

export interface OrderUpdateBody {
  payment_status?: PaymentStatus;
  discount?: Money;
  shipping_charge?: Money;
  items?: { id: number; quantity: number }[];
}
