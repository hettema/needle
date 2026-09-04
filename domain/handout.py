"""What a plan hands out, and what its lane dispatched (plan 12).

A plan item that hands work to a role says so in a `Hands out:` sentence
(`docs/plans/README.md`): the role, what goes to it, and what the executing
session verifies before acting on the result. The roles are the machine's
(`~/.claude-accounts/roles.json`), read by the runtime and never hard-coded
here; the board only reads what the plan wrote and what the machine names.
At a lane's close the board reads the lane's transcripts for the dispatches
it made and writes the two side by side on the card, so an unnamed handout,
an unfollowed one, or a role nobody has earned is a row, never a guess.
"""

from datetime import datetime

from pydantic import BaseModel


class Handout(BaseModel):
    """One `Hands out:` sentence, attributed to the plan item it ends."""

    item: str | None
    """The item the sentence belongs to, as the plan labels it ("2. The board
    reads it"); None when the sentence stands before any item."""
    role: str
    """The first word of the sentence, lower-cased: what the plan named."""
    what: str
    verifies: str | None
    """What the executing session checks before acting on the result; None
    when the sentence names nothing."""


class Handouts(BaseModel):
    """A card's handouts as the page shows them: what the plan named, and the
    board's one line when a named role is not one the machine has."""

    named: list[Handout]
    unknown: list[str]
    """Roles the plan names that the machine's roles file does not, in order, each once."""
    verdict: str | None
    """The board's line when a role is unknown, or when the machine names no
    roles at all and the plan's roles cannot be checked; None when every
    named role is the machine's, or nothing is named."""


class Dispatch(BaseModel):
    """One `Agent` tool use on a lane's main thread: the work it handed out."""

    role: str
    """The `subagent_type` the dispatch named; `claude` when it named none,
    as `machine burn` counts it."""
    session_id: str
    at: datetime | None
