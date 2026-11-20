# OrderFlow

A lightweight order management system for a small e-commerce business: orders, line items,
products, inventory, customers and basic operational metrics.

| Layer      | Technology                                   |
| ---------- | -------------------------------------------- |
| Frontend   | Next.js (App Router) + TypeScript, Vitest     |
| Backend    | Python + FastAPI, Pydantic v2                 |
| Database   | SQLite via SQLAlchemy 2.x                     |
| Tests      | Pytest (backend), Vitest (frontend)           |
| API docs   | OpenAPI / Swagger at `/docs`, plus `docs/API.md` |

Everything runs locally. No Docker, cloud services or third-party APIs are required.

## Prerequisites

- Python 3.10+
- Node.js 20+ and npm

## Quick start

```bash
# 1. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Create and seed the database (from the repository root)
cd ..
python ../scripts/seed_data.py        # resets backend/orderflow.db: 50 customers, 30 products, 200 orders

# 3. Run the API (from backend/)
cd backend
uvicorn app.main:app --reload --port 8000
#   API:      http://localhost:8000/api/v1
#   Swagger:  http://localhost:8000/docs

# 4. Frontend (new terminal)
cd frontend
cp .env.example .env.local         # optional; defaults to http://localhost:8000/api/v1
npm install
npm run dev                        # http://localhost:3000
```

Production-style frontend build: `npm run build && npm start`.

### Configuration

| Variable                    | Default                                   | Purpose                      |
| --------------------------- | ----------------------------------------- | ---------------------------- |
| `ORDERFLOW_DATABASE_URL`    | `sqlite:///<repo>/backend/orderflow.db`   | SQLAlchemy database URL      |
| `ORDERFLOW_CORS_ORIGINS`    | `http://localhost:3000,http://127.0.0.1:3000` | Allowed browser origins  |
| `NEXT_PUBLIC_API_BASE_URL`  | `http://localhost:8000/api/v1`            | API base URL for the frontend |

The database schema is created automatically on API start-up; `scripts/seed_data.py` drops
and recreates it with deterministic data (fixed RNG seed), so runs are repeatable.

## Project structure

```
orderflow/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers + exception handlers
│   │   ├── models/         # SQLAlchemy models (customer, product, order, order item)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # business logic: orders, inventory, pricing, status rules, catalog
│   │   ├── repositories/   # database queries
│   │   ├── utils/          # money rounding, time, SQL query counter
│   │   ├── seed.py         # deterministic dataset builders
│   │   ├── database.py     # engine / session / Base
│   │   └── main.py         # app factory
│   ├── tests/              # pytest suite
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── app/                # pages: dashboard, orders, order detail, products, customers
│   ├── components/
│   ├── services/           # API client, types, formatting
│   └── tests/              # vitest
├── scripts/
│   ├── seed_data.py        # reset + seed the database
│   ├── benchmark_indexes.py    # query plans / timings / index cost on 1k–50k orders
│   ├── benchmark_listing.py    # listing endpoint: SQL count, rows loaded, memory, latency
│   └── race_harness.py         # concurrent order-creation harness
├── benchmarks/results/     # JSON output from the benchmark scripts
└── docs/API.md
```

## Business rules (summary)

- Totals: `subtotal = Σ(unit_price × quantity)`, `tax = 8% × (subtotal − discount)`,
  `grand_total = subtotal − discount + tax + shipping_charge`. Decimal arithmetic, half-up
  rounding to cents. Discount and shipping must be non-negative; grand total cannot be negative.
- Line items store a snapshot of the unit price at purchase time.
- Creating an order reserves inventory; cancelling an eligible order restores it (once).
- Status flow: `PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED`; `PENDING`,
  `CONFIRMED` and `PROCESSING` may also move to `CANCELLED`. `DELIVERED` and `CANCELLED` are terminal.
- Only `PENDING` / `CONFIRMED` orders can be edited.

## Testing

```bash
cd backend
pytest                      # full suite
pytest -m "not known_bug"   # functionality that currently works (should be all green)
pytest -m known_bug         # tests that currently fail (see below)
pytest -m perf -s           # performance / concurrency measurements with printed baselines
```

The suite is split into three groups:

- **Passing tests** – behaviour that works today.
- **`known_bug` tests** – each is tagged with an issue ID (`@pytest.mark.known_bug("BUG-xx")`)
  and currently **fails**. A summary table ("Known-bug test status") is printed at the end of
  every pytest run showing which issues are still present.
- **`perf` tests** – query counts, execution plans, index inventory and a deterministic
  concurrency harness.

Frontend:

```bash
cd frontend
npm test            # vitest
npm run typecheck
```

### Benchmarks and harnesses

Run from the repository root (with the backend virtualenv active):

```bash
python scripts/benchmark_indexes.py --label baseline         # 1k / 10k / 50k orders
python scripts/benchmark_listing.py --label baseline         # 500 / 2k / 8k orders
python scripts/race_harness.py --workers 8 --stock 10 --qty 3
```

Results are written to `benchmarks/results/<name>_<label>.json` so different runs can be compared.

## API

See `docs/API.md` or the live Swagger UI at `http://localhost:8000/docs`.
