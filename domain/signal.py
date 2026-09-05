"""The signal a WATCH row names, and what a reading of it said.

Done is a closed loop, not a claim (INTENT.md): a card enters Executed with
its signal named — what will be observed, where, and by when — and the board
reads the signals it can on the cadence the row states. Three kinds are read
by the board itself (a URL, a file, a command's output); a fourth is read by
a session the board starts with the project's read-only tools (plan 09); the
fifth is the owner's to read, and the board asks him at the due time.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.card import Actor


class SignalKind(StrEnum):
    URL = "url"
    """Delivered when the URL answers 2xx and, with `expect`, carries the text."""
    FILE = "file"
    """Delivered when the file exists in the project."""
    COMMAND = "command"
    """Delivered when the command exits 0 and, with `expect`, its output carries
    the text or, as `>= N`, a number at least N."""
    SESSION = "session"
    """Read by a session the board starts in the project's checkout, with the
    project's read-only tools; the target says what to check and where, and
    the session's finding moves the card (plan 09, item 1)."""
    OWNER = "owner"
    """Only the owner can read it; the board asks him at the due time."""


class Finding(StrEnum):
    """What a reading session ends its turn with, through `needle reading`."""

    DELIVERED = "delivered"
    NOT_DELIVERED = "not-delivered"
    CANNOT_TELL = "cannot-tell"
    """The evidence cannot exist yet, or exists and does not decide it; the
    words say what was read and what would decide it, and the owner is asked."""

    @property
    def delivered(self) -> bool | None:
        return {
            Finding.DELIVERED: True,
            Finding.NOT_DELIVERED: False,
            Finding.CANNOT_TELL: None,
        }[self]


class Signal(BaseModel):
    what: str
    """What will be observed, in the row's own words."""
    kind: SignalKind
    target: str
    """The URL, the path, the command, what a session checks and where, or the owner's question."""
    expect: str | None
    """A substring the reading must carry, or `>= N` for a count."""
    due: date
    every_hours: float
    """The cadence the row states; the default is once a day."""


class Reading(BaseModel):
    id: int
    card_number: int
    at: datetime
    delivered: bool | None
    """None when the signal could not be read; `words` says why."""
    words: str
    actor: Actor
    """Who read it: the machine (a URL, a file, a command, or a reading
    session that ended without a finding), a session's finding, or the owner."""


class SessionWork(StrEnum):
    """What a windowless session the board started is doing."""

    READING = "reading"
    """Reading one card's signal, and ending with a finding (plan 09, item 1)."""
    PLANNING = "planning"
    """Writing the plan for a marked defect under the dial (plan 11, item 4)."""
    TRIAGE = "triage"
    """Reading one defect's mark against the source it cites, with no share
    of the finding session's context, and ending with one typed result
    (plan 59, item 3)."""


class WindowlessSession(BaseModel):
    """A session the board started with no window and no worktree, in the
    project's own checkout: to read one card's signal (plan 09, item 1), to
    plan a marked defect (plan 11, item 4), or to verify a defect's mark
    (plan 59, item 3). Listed on the card while it runs, never hands on any
    tree, ended when its finding, its plan or its result lands or its
    process is gone. At most one is open per card and kind: the store
    refuses the second, so a duplicate triager cannot exist however the
    beat raced."""

    id: int
    project: str
    card_number: int
    work: SessionWork
    session_id: str
    slot: str
    started_at: datetime
    ended_at: datetime | None
