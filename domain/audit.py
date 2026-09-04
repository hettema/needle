"""The audit trail: one row per change to a card, from the first commit.

0.1 kept no history, so every card's record starts at the import and says so.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.card import Actor, Place
from domain.evidence import Evidence


class AuditKind(StrEnum):
    BORN = "born"
    MOVED = "moved"
    LINKED = "linked"
    RENAMED = "renamed"
    ARCHIVED = "archived"
    RETIRED = "retired"
    STARTED = "started"
    """A lane was launched for the card."""
    ROW = "row"
    """A row was written on the card by a session or the owner."""
    ANSWERED = "answered"
    DISCUSSED = "discussed"
    STOPPED = "stopped"
    RESCUED = "rescued"
    """The runtime moved the lane's session to another rung."""
    ENDED = "ended"
    """The lane's session ended, with the machine's reason."""
    SIGNAL = "signal"
    """A reading of the card's WATCH signal, or the owner's answer to it."""
    FOLDED = "folded"
    SYNCED = "synced"
    """The trunk or main checkout was brought level after a fold."""


class AuditEntry(BaseModel):
    id: int
    at: datetime
    actor: Actor
    kind: AuditKind
    card_number: int
    from_place: Place | None
    to_place: Place | None
    detail: str
    evidence: Evidence | None = None
    """The predicate a machine move satisfied (plan 04, item 1); None on every other row."""
