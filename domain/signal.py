"""The signal a WATCH row names, and what a reading of it said.

Done is a closed loop, not a claim (INTENT.md): a card enters Executed with
its signal named — what will be observed, where, and by when — and the board
reads the signals it can on the cadence the row states. Three kinds are read
by the board (a URL, a file, a command's output); the fourth is the owner's
to read, and the board asks him at the due time.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel


class SignalKind(StrEnum):
    URL = "url"
    """Delivered when the URL answers 2xx and, with `expect`, carries the text."""
    FILE = "file"
    """Delivered when the file exists in the project."""
    COMMAND = "command"
    """Delivered when the command exits 0 and, with `expect`, its output carries
    the text or, as `>= N`, a number at least N."""
    OWNER = "owner"
    """Only the owner can read it; the board asks him at the due time."""


class Signal(BaseModel):
    what: str
    """What will be observed, in the row's own words."""
    kind: SignalKind
    target: str
    """The URL, the path, the command, or the owner's question."""
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
