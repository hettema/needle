"""A card's lane: what is happening to it right now, and the doors it offers.

A lane is the worktree named for the card (`card-<n>-<slug>`), the sessions
that have or had hands in it, and what those sessions said through the hooks.
The board derives all of it at read time from the runtime's one list, the
hook events and the store's lane record; nothing here is set by hand. The
card says one sentence about its lane and offers only the doors that can
honestly open (INTENT.md lesson 5: a door either opens and proves it, or
says why not).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.session import Session
from domain.slot import Placement


class LaneState(StrEnum):
    NONE = "none"
    """No lane: nothing has ever had hands on this card."""
    WORKING = "working"
    ASKING = "asking"
    """The session's turn ended with a question for the owner."""
    STOPPED = "stopped"
    """The session's turn ended without a question; it waits to be answered or watched."""
    BLOCKED = "blocked"
    """Waiting on something outside itself that is not a wall: a prompt, a permission."""
    MOVING = "moving"
    """Died on a limit; the handoff is filed and the runtime is moving it."""
    ENDED = "ended"
    """No live session anywhere; the worktree or the record remains."""


HANDS_ON: frozenset[LaneState] = frozenset(
    {LaneState.WORKING, LaneState.ASKING, LaneState.STOPPED, LaneState.BLOCKED, LaneState.MOVING}
)
"""The states in which a live session holds the card's worktree."""


class LaneRecord(BaseModel):
    """The board's own record of where a card's lane lives and what became of
    its work. Separate from the runtime's rescue ledger (plan 03, item 7): a
    session's rescues can be cleared without losing where the lane is."""

    project: str
    card_number: int
    name: str
    path: str
    branch: str | None
    birth: str | None
    """The commit the lane was created at, from its first sighting: a fold is
    proved by the tip being in the trunk AND having moved from here, since a
    zero-commit branch is an ancestor of the trunk from birth (verified live
    2026-09-04: a stopped lane's deleted branch read as folded without this)."""
    tip: str | None
    """The last commit seen on the lane's branch, kept so a fold can still be
    proved after the branch is deleted at the fold."""
    first_seen: datetime
    last_seen: datetime
    """The last read that found the worktree on disk."""
    gone_at: datetime | None
    folded_at: datetime | None
    trunk_synced_at: datetime | None
    main_synced_at: datetime | None


class Discussion(BaseModel):
    """A conversation opened from the board: a card's Discuss door, or the
    head's Idea door about nothing yet (plan 07, item 1). Talking is not
    executing: a discussion never counts as hands on any tree and never
    blocks Start."""

    id: int
    project: str
    card_number: int | None
    """The card discussed; None for an idea, which is about no card yet."""
    session_id: str
    slot: str
    started_at: datetime


class Conversation(BaseModel):
    """A discussion whose session is alive right now, as the rail lists it."""

    short_id: str
    slot: str
    card_number: int | None
    what: str
    """`Idea`, or `#N` for a card's Discuss."""
    started_at: datetime


class Lane(BaseModel):
    card_number: int
    name: str
    path: str | None
    """The worktree, when it exists on disk."""
    state: LaneState
    sentence: str
    """What the card says about its lane, in one sentence."""
    session: Session | None
    """The session that holds the lane: the live one, else the last known."""
    question: str | None
    """The session's last words when it stopped with a question."""
    said: str | None
    """The session's last words, whatever they were."""
    said_at: datetime | None
    discussing: list[str]
    """Short ids of live discussion sessions about this card."""
    window_open: bool
    hands_on_since: datetime | None
    died: str | None
    """The machine's reason when the lane ended without a close."""
    moved: str | None
    """The rescue sentence, when the runtime moved this lane in its current life."""
    folded: bool
    trunk_synced: bool
    main_synced: bool
    edits: list[str]
    """The lane's actual footprint: what its worktree has changed against the
    trunk, re-read from git on every read while a session has hands on it."""
    declared: list[str]
    """The files the card's plan names: the footprint promised before Start."""
    colliding: "Collision | None"
    """Another live lane is editing files this one is also editing, named;
    None while no live lane's edits overlap (plan 07, item 2)."""


class DoorResult(BaseModel):
    """What a door answers when it opened: which door, and the evidence in a sentence."""

    door: str
    said: str


class LaneSnapshot(BaseModel):
    """Every lane of a project as the loop last read it, with each card's
    doors. The page reads this; only the loop writes it."""

    lanes: dict[int, Lane]
    doors: dict[int, "Doors"]
    conversations: list[Conversation]
    """Every discussion with a live session, an idea or a card's, for the rail."""
    read_at: datetime


class Door(BaseModel):
    """One action a card offers, or does not, with the reason either way."""

    offered: bool
    label: str
    why: str


class CollisionVerdict(StrEnum):
    CLEAR = "clear"
    COLLIDES = "collides"
    UNKNOWN = "unknown"
    """The plan names no files, so nothing can prove it disjoint."""


class Collision(BaseModel):
    verdict: CollisionVerdict
    sentence: str
    files: list[str]
    """The overlapping files, when there are any."""


class Doors(BaseModel):
    start: Door
    start_anyway: Door
    placement: Placement | None
    """Where Start would run, from the one rule; None when the rule found nowhere."""
    placement_note: str
    collision: Collision | None
    watch: Door
    answer: Door
    discuss: Door
    look: Door
    resume: Door
    stop: Door
    signal: Door
    """The owner's one-click answer to a signal only he can read, when it is due."""


Lane.model_rebuild()
LaneSnapshot.model_rebuild()
