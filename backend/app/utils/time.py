from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite stores datetimes without timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
