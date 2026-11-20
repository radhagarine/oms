"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Card, ErrorBanner, Loading, Pager } from "@/components/ui";
import { api } from "@/services/api";
import { formatDate } from "@/services/format";
import type { Customer, Page } from "@/services/types";

const PAGE_SIZE = 20;

export default function CustomersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState<string | undefined>();
  const [result, setResult] = useState<Page<Customer> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCustomers(page, PAGE_SIZE, term)
      .then(setResult)
      .catch((e: Error) => setError(e.message));
  }, [page, term]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setPage(1);
    setTerm(search.trim() || undefined);
  };

  return (
    <>
      <h1>Customers</h1>
      <Card>
        <form className="toolbar" onSubmit={onSubmit}>
          <input placeholder="Search name or email…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search customers" />
          <button type="submit">Search</button>
        </form>
        <ErrorBanner message={error} />
        {!result ? (
          <Loading />
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Customer since</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>
                      <Link href={`/customers/${c.id}`}>{c.name}</Link>
                    </td>
                    <td>{c.email}</td>
                    <td>{c.phone ?? "—"}</td>
                    <td>{formatDate(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager
              page={result.page}
              totalPages={result.total_pages}
              total={result.total}
              hasPrevious={result.has_previous}
              hasNext={result.has_next}
              onPrevious={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          </>
        )}
      </Card>
    </>
  );
}
