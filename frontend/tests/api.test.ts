import { describe, expect, it, vi } from "vitest";
import { ApiError, buildQuery, parseApiError, request } from "@/services/api";

describe("buildQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(buildQuery({ page: 1, search: "john smith", status: "", customer_id: undefined })).toBe("?page=1&search=john+smith");
  });
  it("returns an empty string when there are no params", () => {
    expect(buildQuery({ search: "" })).toBe("");
  });
});

describe("parseApiError", () => {
  it("reads {detail}", () => {
    expect(parseApiError(404, { detail: "Product 9 not found" }).message).toBe("Product 9 not found");
  });
  it("reads {error}", () => {
    expect(parseApiError(409, { error: "Insufficient inventory" }).message).toBe("Insufficient inventory");
  });
  it("reads validation {errors: [...]}", () => {
    const err = parseApiError(422, { message: "Validation failed", errors: [{ field: "query.page", message: "bad" }] });
    expect(err.message).toBe("query.page: bad");
    expect(err.status).toBe(422);
  });
  it("falls back to a generic message", () => {
    expect(parseApiError(500, null).message).toBe("Request failed with status 500");
  });
});

describe("request", () => {
  it("returns parsed JSON on success", async () => {
    const fetchFn = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1 }), { status: 200 }));
    await expect(request("/orders/1", {}, fetchFn)).resolves.toEqual({ id: 1 });
    expect(fetchFn).toHaveBeenCalledWith(expect.stringContaining("/orders/1"), expect.objectContaining({ cache: "no-store" }));
  });
  it("throws ApiError on failure", async () => {
    const fetchFn = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "nope" }), { status: 409 }));
    await expect(request("/orders", { method: "POST" }, fetchFn)).rejects.toBeInstanceOf(ApiError);
  });
});
