"""The one clock. Everything that needs the time asks here, so a test can hold it."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)
