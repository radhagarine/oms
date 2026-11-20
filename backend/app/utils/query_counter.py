"""SQL statement instrumentation used by tests and benchmarks."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import event
from sqlalchemy.engine import Engine


@dataclass
class QueryLog:
    statements: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.statements)

    def matching(self, fragment: str) -> list[str]:
        return [s for s in self.statements if fragment.lower() in s.lower()]


@contextmanager
def count_queries(engine: Engine) -> Iterator[QueryLog]:
    log = QueryLog()

    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if not statement.lstrip().upper().startswith("PRAGMA"):
            log.statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        yield log
    finally:
        event.remove(engine, "before_cursor_execute", _before)
