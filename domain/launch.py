"""Starting and moving sessions: the request, the walk down the ladder, the verdict.

A launch is never trusted on the launcher's exit code. `claude --bg` exits 0
for a session that dies a second later; the verdict is read from the registry
and from /proc, and every rung walked is kept so the answer says what was
tried and what each attempt died of.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.gate import Gate
from domain.session import Session
from domain.slot import Placement, Rung


class Start(BaseModel):
    """What a caller asks for: a session for this card, in this repository, with this brief."""

    repo: str
    card: str
    """The lane's name: the worktree, the scope and the window all carry it."""
    brief: str
    effort: Gate
    from_slot: str | None
    """The slot to ask first; None asks the rule from the top."""


class LaunchVerdict(StrEnum):
    ALIVE = "alive"
    """A registered row with a live process that outlived the observation window."""
    DEAD = "dead"
    """The registry recorded a death, with its reason, or the process went away."""
    UNCONFIRMED = "unconfirmed"
    """Neither by the deadline; the caller says so rather than claiming either."""


class Attempt(BaseModel):
    """One rung walked, and what happened there."""

    rung: Rung
    verdict: LaunchVerdict
    short_id: str | None
    reason: str | None
    """The machine's words when dead: the limit message, or what went away."""
    seconds: float


class Launch(BaseModel):
    card: str
    verdict: LaunchVerdict
    session: Session | None
    placement: Placement | None
    scope: str | None
    """The transient unit the session's processes were put in."""
    attempts: list[Attempt]
    reason: str | None
    """Why there is no live session, in one sentence, when there is none."""


class Stopped(BaseModel):
    """What a stop answers: whether the process is gone, proved in /proc."""

    short_id: str
    session_id: str
    slot: str
    gone: bool
    seconds: float
    words: str
    """What `claude stop` said."""


class Rescue(BaseModel):
    """One move of a session from one rung to another, in the runtime's ledger.
    Separate from the record of where the session lives, so clearing a
    session's history never loses its slot."""

    id: int
    session_id: str
    from_rung: Rung | None
    to_rung: Rung
    reason: str
    at: datetime
