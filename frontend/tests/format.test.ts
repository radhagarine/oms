import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, titleCase } from "@/services/format";

describe("formatMoney", () => {
  it("formats decimal strings as USD", () => {
    expect(formatMoney("1234.5")).toBe("$1,234.50");
  });
  it("handles missing and invalid values", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney("abc")).toBe("—");
  });
});

describe("formatDate", () => {
  it("formats ISO dates", () => {
    expect(formatDate("2026-03-01T10:00:00")).toBe("Mar 01, 2026");
  });
  it("handles invalid input", () => {
    expect(formatDate("nope")).toBe("—");
  });
});

describe("titleCase", () => {
  it("title-cases enum values", () => {
    expect(titleCase("DELIVERED")).toBe("Delivered");
  });
});
