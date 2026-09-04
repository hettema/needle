"""What a session pushes to the board: one event per hook firing.

Sessions push; the board never polls a session (INTENT.md lesson 3). The hook
registered in each project's Claude settings posts these at session start,
stop, end and stop failure. The board keeps every event, attributes it to a
card by the working directory, and reads a lane's state from the latest one
together with the runtime's session list.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class HookKind(StrEnum):
    SESSION_START = "SessionStart"
    STOP = "Stop"
    SESSION_END = "SessionEnd"
    STOP_FAILURE = "StopFailure"


class HookPosted(BaseModel):
    """What the hook script sends, verbatim from Claude Code's payload, minus
    everything the board does not read."""

    kind: HookKind
    session_id: str
    cwd: str
    at: datetime
    source: str | None
    """SessionStart: startup, resume, clear or compact."""
    message: str | None
    """Stop and StopFailure: the last assistant message."""
    reason: str | None
    """SessionEnd: why the session ended, in Claude Code's own word."""
    error: str | None
    """StopFailure: the error class (`rate_limit`, ...)."""
    transcript_path: str | None


class HookEvent(HookPosted):
    """A posted event as the board holds it, attributed to a card when the
    working directory is a lane of a registered project."""

    id: int
    project: str | None
    card_number: int | None
