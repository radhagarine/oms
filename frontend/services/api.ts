import type {
  Customer,
  MetricsSummary,
  OrderDetail,
  OrderItem,
  OrderListQuery,
  OrderStatus,
  OrderSummary,
  OrderUpdateBody,
  Page,
  Product,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/** Extract a human-readable message from any of the error payload shapes the API returns. */
export function parseApiError(status: number, body: unknown): ApiError {
  let message = `Request failed with status ${status}`;
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (typeof b.detail === "string") message = b.detail;
    else if (typeof b.error === "string") message = b.error;
    else if (Array.isArray(b.errors) && b.errors.length) {
      message = b.errors
        .map((e) => {
          const err = e as { field?: string; message?: string };
          return err.field ? `${err.field}: ${err.message}` : String(err.message);
        })
        .join("; ");
    } else if (typeof b.message === "string") message = b.message;
  }
  return new ApiError(status, message);
}

export function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    qs.set(key, String(value));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

type FetchFn = typeof fetch;

export async function request<T>(path: string, init: RequestInit = {}, fetchFn: FetchFn = fetch): Promise<T> {
  const resp = await fetchFn(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    cache: "no-store",
  });
  const text = await resp.text();
  const body = text ? JSON.parse(text) : null;
  if (!resp.ok) throw parseApiError(resp.status, body);
  return body as T;
}

export const api = {
  metrics: () => request<MetricsSummary>("/metrics/summary"),

  listOrders: (q: OrderListQuery) => request<Page<OrderSummary>>(`/orders${buildQuery({ ...q })}`),
  getOrder: (id: number) => request<OrderDetail | null>(`/orders/${id}`),
  getOrderItems: (id: number) => request<OrderItem[]>(`/orders/${id}/items`),
  updateOrder: (id: number, body: OrderUpdateBody) =>
    request<OrderDetail>(`/orders/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  changeStatus: (id: number, status: OrderStatus) =>
    request<OrderDetail>(`/orders/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  cancelOrder: (id: number) => request<OrderDetail>(`/orders/${id}/cancel`, { method: "POST" }),

  listProducts: (search?: string) => request<Product[]>(`/products${buildQuery({ search })}`),

  listCustomers: (page: number, pageSize: number, search?: string) =>
    request<Page<Customer>>(`/customers${buildQuery({ page, page_size: pageSize, search })}`),
  getCustomer: (id: number) => request<Customer>(`/customers/${id}`),
  getCustomerOrders: (id: number) => request<OrderSummary[]>(`/customers/${id}/orders`),
};
