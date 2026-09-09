"""A subscription slot, the makes the runtime can launch, and where the one
rule says work runs next.

A slot is one config directory holding one login. Which slot has headroom,
which identity it holds and which rung runs there is `claude-acct`'s
knowledge (ruling 1, 2026-09-04): the runtime asks `claude-acct best` and
never re-implements the rule. What the runtime keeps of a slot is what it
needs to reach it: its name and its directory.

A rung is a make, a model and a tier, and none of the three is enumerated
here (card #63). The models were an enum — `fable | opus` — until the day a
card could be driven by a colleague of another make, which no Claude model
name can hold; a rung's model is now whatever word the rule answered, kept
as it was given and never guessed. The tier is the owner's dated ruling
about which rungs are the strong ones, carried on the answer so the board
can show what selected the outcome and when he ruled it. What stays code is
`Make`: a make the runtime can launch needs a launcher, so the set of makes
this runtime *can* run is code and the set it may be *told about* is not — a
rule naming a make with no launcher here is refused by that name.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.ending import Cause


class Make(StrEnum):
    """The makes this runtime has a launcher for. Not the makes that exist:
    the rule may name any word, and one that is not here is refused with the
    word it used, so a third make is a launcher and a row of data, never a
    silent fallback onto the make we happen to know."""

    CLAUDE = "claude"
    CODEX = "codex"


class Tier(BaseModel):
    """Which band of the ladder a rung stands in, as the owner ruled it.

    Rank 1 is the top band; a lower band is a weaker model. The ruling is
    the owner's and is dated, because the evidence may move it: #58's
    reader and the machine's baseline can argue a rung up or down, and the
    move is a dated edit of the ruling rather than a fact the code asserts
    (card #63, the two rulings of 2026-09-05).
    """

    rank: int
    ruled_on: date
    why: str
    """The ruling's own words, shown where the rung is shown."""


class Slot(BaseModel):
    name: str
    config_dir: str
    """Where the slot's registry, daemon and credentials live."""


class Rung(BaseModel):
    """One place work can run: a slot and a model. A wall spends one rung
    (a Fable limit) or every rung on a slot (a session or weekly limit).
    The slot carries the make's own name for a make with no subscription
    ladder, which is how a Codex rung has always been recorded."""

    slot: str
    model: str | None
    """None means every rung on the slot, or a make whose rung has no model
    name of its own."""


class Placement(BaseModel):
    """Where work runs next, as `claude-acct best` answered it."""

    slot: str
    make: Make
    """Which launcher runs it. Absent from the answer means Claude, the only
    make the rule knew when it was written."""
    model: str | None
    """The rung's model, in the rule's own word; None when the rule named
    none and the make's own default is to run — never a guess."""
    config_dir: str
    why: str
    """The command's own words: its output line, or its reason for refusing."""
    tier: Tier | None = None
    """The owner's dated ruling that put this rung where it is, when the rule
    said; None when it did not, and the board says the rung without a tier
    rather than inventing one. A rung with no tier is a real state the board
    shows, while a rung with no make is a guess about who drives the card,
    which is the guess this card ended."""
    machine: str = ""
    """The machine the rule was asked on, by the board's name for it (card
    #83): stamped by the board's runtime after it chose the machine, never
    by the rule, which knows only its own machine. Empty when the rule was
    asked by a runtime that has not been told its own name."""


class Where(BaseModel):
    placement: Placement | None
    """None when the rule found nowhere to run; `reason` says so in its words."""
    reason: str


def rung_words(model: str | None, slot: str) -> str:
    """A rung as every face says it: the model and the slot when a model is
    named, the slot alone when none is. The one place that sentence is
    built, so no reader has to decide what to say for a rung with no model
    and none of them can go back to guessing `fable` (card #63)."""
    return f"{model} on {slot}" if model else slot


RECOVERED_WHY = "connection back after a transient death"
"""`claude-acct recover`'s `why`, verbatim (its line 1803 on 2026-09-09)."""
STRONGER_MODEL_WHY = "; back on Fable"
"""How `claude-acct`'s switch-back closes its `why` (line 1690, same day)."""


class Handoff(BaseModel):
    """The wall detector's file for a background session, read verbatim.

    Written by the `StopFailure` hook (`claude-acct handoff`) at
    `<cache>/handoff/bg/<session_id>.json` the moment a turn dies on a limit.
    The runtime acts on it — stop where it ran, resume where it names — and
    never reads the limit message for meaning; `reason` is shown, not parsed.
    """

    session_id: str
    short_id: str | None
    from_slot: str
    account: str
    """The slot the rule chose."""
    model: str | None
    """The model the rule chose; None is the default, the top rung."""
    prompt: str
    reason: str
    at: datetime
    cwd: str | None
    worktree: str | None
    pid: int | None
    stopped: bool | None
    """Whether the hook already stopped the session; None when the file does not say."""
    path: str
    """Where the file is, so a done move can remove it."""
    why: str = ""
    """Why the file was written, in `claude-acct`'s own words: the rule's
    reason for the rung it chose on a wall, `connection back after a
    transient death` from its recover timer, `…; back on Fable` from its
    switch-back. Three writers share one file shape (verified 2026-09-09),
    and this is the field that tells them apart (plan 68, item 3)."""

    @property
    def cause(self) -> Cause:
        """What the handoff asks for. The machine's connection recovery and
        its switch-back to the stronger model write the same background
        handoff file as a wall, and until plan 68 every one of them moved
        the lane as "ran out of allowance", and a second within the hour
        parked it as "hit a limit again". The writer says why in its own
        field; anything else is the wall detector's."""
        why = self.why.strip()
        if why == RECOVERED_WHY:
            return Cause.RECOVERED
        if why.endswith(STRONGER_MODEL_WHY):
            return Cause.STRONGER_MODEL
        return Cause.WALL


class Limits(BaseModel):
    """One subscription's last limits reading, as `claude-acct` cached it:
    what share of each allowance is spent and when each comes back (plan
    68, item 3). Read for a park's end; the rule itself is never
    re-implemented here."""

    slot: str
    fetched_at: datetime
    spent: dict[str, float]
    """By the allowance's own label (`Fable Weekly`, `Session (5-hour)`), the
    share used, 1.0 when it is gone."""
    resets: dict[str, datetime]
    """By the same label, when the allowance returns, for those that say."""


class LimitsRead(BaseModel):
    """One machine's answer for a slot's last limits reading (card #83):
    the reading, or None when that machine's `claude-acct` has none."""

    limits: Limits | None


class Expired(BaseModel):
    """Whether a handoff file on one machine was removed (card #83)."""

    session_id: str
    removed: bool
