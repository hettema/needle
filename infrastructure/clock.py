"""The one clock. Everything that needs the time asks here, so a test can hold it."""

from datetime import UTC, datetime

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
"""Before every moment the board records: what a sort falls back to for a
stamp that is missing, so an unstamped row orders last rather than raising."""


def now() -> datetime:
    return datetime.now(UTC)
