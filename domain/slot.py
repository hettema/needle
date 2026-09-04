"""A subscription slot, and where the one rule says work runs next.

A slot is one Claude Code config directory holding one login. Which slot has
headroom, which identity it holds and which model runs there is
`claude-acct`'s knowledge (ruling 1, 2026-09-04): the runtime asks
`claude-acct best` and never re-implements the rule. What the runtime keeps
of a slot is what it needs to reach it: its name and its directory.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Model(StrEnum):
    """The rungs the rule can name. `claude-acct best` prints the slot alone
    for the top rung and `--model opus` when no slot has Fable left."""

    FABLE = "fable"
    OPUS = "opus"


class Slot(BaseModel):
    name: str
    config_dir: str
    """Where the slot's registry, daemon and credentials live."""


class Rung(BaseModel):
    """One place work can run: a slot and a model. A wall spends one rung
    (a Fable limit) or every rung on a slot (a session or weekly limit)."""

    slot: str
    model: Model | None
    """None means every rung on the slot."""


class Placement(BaseModel):
    """Where work runs next, as `claude-acct best` answered it."""

    slot: str
    model: Model
    config_dir: str
    why: str
    """The command's own words: its output line, or its reason for refusing."""


class Where(BaseModel):
    placement: Placement | None
    """None when the rule found nowhere to run; `reason` says so in its words."""
    reason: str


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
    model: Model | None
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
