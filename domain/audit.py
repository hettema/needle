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
    RETITLED = "retitled"
    """The card's document changed its title and the face followed (plan 08, item 1)."""
    ARCHIVED = "archived"
    RETIRED = "retired"
    """A number that is no longer a card: 0.1's retired numbers, and a card
    retired into another whose document its own was renamed into before the
    board could follow the rename (plan 08, item 1)."""
    STARTED = "started"
    """A lane was launched for the card."""
    ROW = "row"
    """A row was written on the card by a session or the owner."""
    ANSWERED = "answered"
    DISCUSSED = "discussed"
    STOPPED = "stopped"
    """The machine or the owner ended the lane's session — or, once the
    session had ended by any road, what it left running in its group
    (card #99)."""
    RESCUED = "rescued"
    """The runtime moved the lane's session to another rung."""
    SCOPED = "scoped"
    """The lane's session was found outside the lane's scope — put back by
    the machine after a kill, or resumed by hand — and put back in it, so a
    limit or a kill stays one lane's (plan 53, item 2)."""
    ENDED = "ended"
    """The lane's session ended, with the machine's reason."""
    SIGNAL = "signal"
    """A reading of the card's WATCH signal, or the owner's answer to it."""
    FOLDED = "folded"
    """The lane's work is in the trunk."""
    FOLDED_INTO = "folded-into"
    """The card's suggestion is carried by a plan whose card is another: this
    card is folded under it (plan 06, item 5)."""
    SYNCED = "synced"
    """The trunk or main checkout was brought level after a fold."""
    DIAL = "dial"
    """The dial took the card, planned it, started it, or left it to the
    owner, with why (plan 11, item 4)."""
    TITLE = "title"
    """A cold reading of the card's title landed: placeable, or not, with
    the reader's words (card #74, item 3)."""
    TOLD = "told"
    """The owner was told on his screen — a card the machine moved out of
    Executing, or a running card that started waiting on him — with the
    popup's words, or why it could not be raised (card #41, item 2)."""
    LEVERAGE = "leverage"
    """A reading of the card against the project's chosen focus landed:
    its class, its likelihood and the reader's sentence (card #87, item 4)."""


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
