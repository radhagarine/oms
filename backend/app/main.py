from __future__ import annotations

import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import exc as sa_exc

from app.api import customers, orders, products
from app.api.errors import register_exception_handlers
from app.database import init_db
from app.logging_config import configure_logging

# SQLite stores NUMERIC as REAL-affinity text; values are quantized to cents in the service layer.
warnings.filterwarnings("ignore", category=sa_exc.SAWarning, message=".*Decimal objects natively.*")

# Must run before any handler logs an exception, so tracebacks never include the
# machine-specific absolute repo path (see app/logging_config.py for details).
configure_logging()

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="OrderFlow API",
        version="0.1.0",
        description="Order management API for OrderFlow.",
        lifespan=lifespan,
    )
    origins = os.getenv("ORDERFLOW_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(orders.router, prefix=API_PREFIX)
    app.include_router(orders.metrics_router, prefix=API_PREFIX)
    app.include_router(products.router, prefix=API_PREFIX)
    app.include_router(customers.router, prefix=API_PREFIX)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
