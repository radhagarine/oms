import type { ReactNode } from "react";
import { titleCase } from "@/services/format";

export function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${value.toLowerCase()}`}>{titleCase(value)}</span>;
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="error" role="alert">
      {message}
    </div>
  );
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="card">
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}

export function Loading() {
  return <p className="muted">Loading…</p>;
}

export function Pager(props: {
  page: number;
  totalPages: number;
  total: number;
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <div className="pager">
      <button onClick={props.onPrevious} disabled={!props.hasPrevious}>
        ← Previous
      </button>
      <span className="muted">
        Page {props.page} of {Math.max(props.totalPages, 1)} · {props.total} records
      </span>
      <button onClick={props.onNext} disabled={!props.hasNext}>
        Next →
      </button>
    </div>
  );
}
