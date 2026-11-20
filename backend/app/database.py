"""Database engine, session factory and declarative base."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = f"sqlite:///{Path(__file__).resolve().parent.parent / 'orderflow.db'}"


class Base(DeclarativeBase):
    pass


def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    # SKU lookups must be exact, so LIKE comparisons are configured case-sensitive.
    cursor.execute("PRAGMA case_sensitive_like=ON")
    cursor.close()


def build_engine(url: str | None = None) -> Engine:
    database_url = url or os.getenv("ORDERFLOW_DATABASE_URL", DEFAULT_DATABASE_URL)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    eng = create_engine(database_url, connect_args=connect_args, future=True)
    if eng.dialect.name == "sqlite":
        event.listen(eng, "connect", _configure_sqlite)
    return eng


engine: Engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Engine | None = None) -> None:
    # Import models so they register with Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=bind or engine)
