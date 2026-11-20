"use client";

import { FormEvent, useEffect, useState } from "react";
import { Card, ErrorBanner, Loading, StatusBadge } from "@/components/ui";
import { api } from "@/services/api";
import { formatMoney } from "@/services/format";
import type { Product } from "@/services/types";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = (term?: string) => {
    api
      .listProducts(term)
      .then(setProducts)
      .catch((e: Error) => setError(e.message));
  };

  useEffect(() => load(), []);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    load(search.trim() || undefined);
  };

  return (
    <>
      <h1>Products</h1>
      <Card>
        <form className="toolbar" onSubmit={onSubmit}>
          <input placeholder="Search name or SKU…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search products" />
          <button type="submit">Search</button>
        </form>
        <ErrorBanner message={error} />
        {!products ? (
          <Loading />
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>SKU</th>
                <th className="num">Price</th>
                <th className="num">Available</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.name}</td>
                  <td>{p.sku}</td>
                  <td className="num">{formatMoney(p.unit_price)}</td>
                  <td className="num" style={p.inventory_quantity === 0 ? { color: "var(--danger)", fontWeight: 600 } : undefined}>
                    {p.inventory_quantity}
                  </td>
                  <td>
                    <StatusBadge value={p.is_active ? "ACTIVE" : "INACTIVE"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
