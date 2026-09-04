"""What a machine-placed status rests on, and whether it still holds.

A column is one of two kinds of fact (plan 04, item 1). The owner's placements
are true because he said so and are never re-tested. The machine's placements
— into Executing, Executed, Done, and out of Executing to Decision moment or
back — are true only while a named piece of evidence holds: a live session in
the card's worktree, an archived plan with DELIVERED written and a readable
signal, a reading that said delivered, a lane that ended. Every machine move
records which predicate it satisfied, and every read re-tests the card
against that predicate; a card whose evidence is gone says so on the page
before and independent of any move the loop makes.
"""

from enum import StrEnum

from pydantic import BaseModel

from domain.card import Actor


class Evidence(StrEnum):
    """The predicate a machine placement satisfied, named so a read can ask it again."""

    HANDS_ON = "hands-on"
    """Executing: a session with a live process in the card's worktree, on disk."""
    CLOSE_LANDED = "close-landed"
    """Executed: the plan is archived, DELIVERED is written, the WATCH row names a signal."""
    SIGNAL_DELIVERED = "signal-delivered"
    """Done: the last reading of the card's signal said delivered."""
    SIGNAL_FAILED = "signal-failed"
    """Decision moment: the last reading said not delivered, or could not read, past due."""
    LANE_ENDED = "lane-ended"
    """Decision moment, or back where the card came from: no session has hands on it."""
    DOCUMENT_ARCHIVED = "document-archived"
    """Decision moment: the card's document was archived with no lane on the
    card and nothing written up (plan 06, item 1). Holds while the document
    stays archived and no session has hands on the card."""


class EvidenceState(StrEnum):
    HELD = "held"
    """The predicate was re-tested on this read and still holds."""
    DOUBTED = "doubted"
    """The predicate no longer holds; `words` names the missing fact."""
    UNKNOWN = "unknown"
    """Not yet tested: the loop has not read the machine since the board was served."""
    TRUSTED = "trusted"
    """The owner's own placement, or a column no predicate governs; never tested."""


class Standing(BaseModel):
    """Where a card's placement stands: who put it there, on what evidence, and
    whether that evidence holds now."""

    actor: Actor
    """Who placed the card in its column: the last move, or its birth."""
    evidence: Evidence | None
    """The predicate the placement rests on; None when nobody's predicate governs it."""
    state: EvidenceState
    words: str | None
    """The missing fact in words when doubted; why it is unknown when unknown."""
