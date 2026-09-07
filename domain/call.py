"""A call: one session asking a running colleague for its judgment (plan 17).

A person walks to a desk with the thread and the question; a session calls
a colleague warm. The call names the colleague's session, the note that
holds the thread and the question, and the file the answer lands in, and
the runtime resumes that session through its lifecycle owner with the note
as its brief. The record is the caller's handle: `needle wait` reads it,
and the loop tends it — it follows the forked id when the runtime moves the
colleague, and ends it with the runtime's own words when the colleague is
blocked, moved or ends without its note, so a waiter never outlives the
colleague it waits on. The verb owns nothing of the colleague's life
(plan 17, ruling 5).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CallOutcome(StrEnum):
    """How a wait, or the loop's tending, found the call."""

    LANDED = "landed"
    """The answer landed (or the note changed) after the call."""
    NOTHING = "nothing"
    """The ceiling passed with the colleague still at work."""
    BLOCKED = "blocked"
    """The colleague waits on something outside itself: a wall, a question."""
    MOVED = "moved"
    """The runtime moved the colleague to another slot; the record follows."""
    ENDED = "ended"
    """The colleague's turn or process ended without the note."""


class Call(BaseModel):
    id: int
    session_id: str
    """The colleague's session; follows the forked id when the runtime moves it."""
    slot: str
    name: str
    """The colleague's name in the one list."""
    note: str
    """The file that holds the thread and the question, read by the colleague."""
    answer: str
    """Where the answer lands; a waiter returns when it lands or changes."""
    brief: str
    caller: str
    """The working directory the call was made from: a lane's worktree when a
    lane called, so the lane hears the answer as its word."""
    called_at: datetime
    moved: str | None
    """The runtime's words when the colleague was moved after the call."""
    ended_at: datetime | None
    words: str | None
    """Why the call ended, in the runtime's words, when it did."""


class CallVerdict(BaseModel):
    """What one reading of a call against the one list and the answer file
    says: the same reading `needle wait` and the loop make (plan 17)."""

    outcome: CallOutcome
    words: str
    session_id: str
    """The session the call now names: the fork when the colleague moved."""
    slot: str


class HowKnown(StrEnum):
    """How a colleague knew what it answered: `docs/HOW-WE-WORK.md` §8's own
    three words, so an answer says how it was known and never speaks in the
    voice of the checked."""

    CHECKED = "checked"
    RECALLED = "recalled"
    INFERRED = "inferred"


class Answer(BaseModel):
    """The shape a called colleague answers in (card #73, item 2): the
    words, how they were known, and what they stood on. One shape for
    every call, whatever the make: a Codex worker is held to it by
    `--output-schema` with this model's JSON schema, and a Claude colleague
    is asked for it in words, so `runtime.calls` has one reader for both.
    Extra keys are forbidden, so the schema closes the object
    (`additionalProperties: false`) and a reply with a key outside the
    shape is not the shape; a Codex worker held to this schema answered in
    it first time (2026-09-07)."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    """The reply itself, the words the verdict carries."""
    how_known: HowKnown
    sources: list[str]
    """What the answer stood on: files read, commands run, a document; empty
    when it stood on nothing, which the caller then sees."""
