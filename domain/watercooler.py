"""The project's watercooler: the lines lanes leave for each other.

Lanes that run at the same time have no memory of each other and no channel
but the files they both touch (plan 07, item 2). The watercooler is the one
channel: a line per act, kept in the board's store and never in a lane's
tree, because a line written into a worktree is invisible to every other
lane until the fold, which is exactly when it is too late. A lane reads the
lines at its start and before its fold, and writes one when it touches a
seam another lane depends on; the board writes one when a fold lands over
another lane's edits, so a silent merge is never silent.
"""

from datetime import datetime

from pydantic import BaseModel

from domain.card import Actor


class WatercoolerLine(BaseModel):
    id: int
    project: str
    card_number: int | None
    """The card whose lane said it; None when the board itself spoke."""
    actor: Actor
    at: datetime
    text: str


class Note(BaseModel):
    """One note on the machine's watercooler: the discussion directory where
    sessions of any make on this laptop talk through files (the machine's
    CLAUDE.md). The two watercoolers stay two (plan 17, ruling 3): this one
    is read by the board so a lane party to a discussion hears a note the
    way it hears a watercooler line, and never written by it."""

    path: str
    first_line: str
    at: datetime
    """The file's last change."""
