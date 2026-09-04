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


class HeardMark(BaseModel):
    """Where a running lane's hearing stands (plan 10, item 1): the last
    watercooler line it was told, the drift sentence it was last told, and
    when and what it last heard. Kept in the store so "once" survives a
    restart of the board and never depends on the hook remembering."""

    project: str
    card_number: int
    watercooler_id: int
    """The newest watercooler line the lane has heard; 0 before any."""
    collision: str | None
    """The drift sentence the lane was last told; None when it was told none."""
    at: datetime | None
    """When the lane last heard a word that said something."""
    text: str | None
    """What it heard then, as the card shows it."""


class Word(BaseModel):
    """What the board has not yet told a running lane, in the board's voice:
    one sentence per fact, empty when there is nothing new. Read by the hook
    on every tool use and given to the session once; reading it moves the
    lane's HeardMark."""

    project: str
    card_number: int
    sentences: list[str]
    read_at: datetime
    """When the loop last read the lane the drift comes from: the same
    staleness the pill has, at most the loop's beat."""
