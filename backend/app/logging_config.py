"""Logging setup for the OrderFlow API.

The app logs full tracebacks for unhandled errors (see ``app.api.errors``).
Python's standard ``logging``/``traceback`` machinery renders each frame
using the absolute ``co_filename`` of the source file, which on a developer
machine includes the full path to the repository (and therefore the OS
username) -- e.g. ``/Users/<name>/.../backend/app/services/order_service.py``.

Pytest shortens paths in *its own* failure reports (relative to the
invocation directory), but that shortening does not apply to text emitted
through the logging module -- including the "Captured log call" sections
pytest prints for a failing test, or plain console output when running with
``-s``. Anything logged via ``logger.exception``/``logger.warning`` would
otherwise leak the absolute, username-bearing path whenever a request
triggers it during a test run.

``_RedactProjectRootFilter`` rewrites the message and any exception
traceback on each log record *in place*, stripping the repository's absolute
path prefix before any handler (ours, pytest's own log capture, a future log
aggregator, etc.) formats and displays it. This only changes how paths are
*displayed*; logging level, propagation and capture timing (e.g. pytest only
showing "Captured log call" on failure) are untouched.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

# backend/ -- the directory containing the "app" package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT_PREFIX = str(PROJECT_ROOT) + os.sep

_plain_formatter = logging.Formatter()


class _RedactProjectRootFilter(logging.Filter):
    """Strip the absolute backend path from a record's message and traceback.

    Filters run once, on the originating logger, before the record reaches
    any handler (ours or an ancestor logger's, e.g. pytest's log-capture
    handler on the root logger). ``logging.Formatter.format`` caches
    ``record.exc_text`` the first time it renders a traceback and every
    later formatter reuses that cached value verbatim, so sanitizing it here
    guarantees every downstream renderer sees the redacted path.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        if _PROJECT_ROOT_PREFIX in rendered:
            record.msg = rendered.replace(_PROJECT_ROOT_PREFIX, "")
            record.args = ()

        if record.exc_info and not record.exc_text:
            record.exc_text = _plain_formatter.formatException(record.exc_info).replace(
                _PROJECT_ROOT_PREFIX, ""
            )

        return True


_CONFIGURED = False


def configure_logging() -> None:
    """Install the path-redacting filter on the app logger.

    Idempotent: safe to call multiple times (e.g. once per test-session app
    import) without installing duplicate filters.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.getLogger("orderflow").addFilter(_RedactProjectRootFilter())
    _CONFIGURED = True
