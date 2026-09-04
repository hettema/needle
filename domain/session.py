"""A session as the runtime knows it: one row of the one list.

Claude Code keeps a registry per config directory, so one session id can
appear in several. The runtime reads them all, checks `/proc` for every row,
and reports one row per session id: the copy with a live process wins and
the others are marked stale. A row with no process is never working.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.gate import Gate
from domain.slot import Handoff, Model


class SessionKind(StrEnum):
    BACKGROUND = "background"
    """Started with `claude --bg`; attachable, stoppable, listed in jobs/."""
    INTERACTIVE = "interactive"
    """Running in a terminal of its own; the terminal is its window."""


class SessionState(StrEnum):
    """The runtime's verdict, not the registry's word (that is `Session.recorded`)."""

    WORKING = "working"
    BLOCKED = "blocked"
    """Waiting on something outside itself: a question, a permission, a wall."""
    IDLE = "idle"
    DONE = "done"
    """Its turn finished; the process is still there and can be attached."""
    ENDED = "ended"
    """No process behind the row, whatever the registry says."""


class Session(BaseModel):
    slot: str
    config_dir: str
    """The registry this row was read from; attach and stop go through it."""
    short_id: str
    session_id: str
    kind: SessionKind
    name: str
    cwd: str
    worktree: str | None
    """Where the hands are when the session was started with a worktree of its own."""
    state: SessionState
    recorded: str
    """The registry's own word, verbatim."""
    detail: str
    pid: int | None
    """The process verified in /proc, by pid and start time; None is no process."""
    scope: str | None
    """The systemd unit holding the process, when it has one."""
    model: Model | None
    effort: Gate | None
    """The effort the session was started with, so a fresh session from its transcript keeps it."""
    stale: bool
    """A copy of a session id whose live process is in another slot's registry."""
    wall: Handoff | None
    """The wall detector's file naming this session, when one is waiting to be acted on."""
    intent: str
    """The prompt the session was born with, from the registry."""
    created_at: datetime | None
    updated_at: datetime | None


class SessionSlot(BaseModel):
    """The runtime's own record of where a session it started runs. Only the
    thing that started or moved a session knows; everything else reads this."""

    session_id: str
    slot: str
    card: str
    scope: str
    recorded_at: datetime
