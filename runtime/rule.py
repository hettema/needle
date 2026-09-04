"""Where work runs next: asked of `claude-acct best`, never decided here.

The one rule on this machine lives in `claude-acct` (plan 02, ruling 1):
the slot with Fable headroom first, Opus only when no slot has Fable, a slot
holding the wrong identity or a spent window refused. This module turns its
JSON answer into a typed placement and its refusal into a reason, and nothing
more. `cached` reads the rule over the per-slot cache the statusline keeps
fresh (sub-second, for a card's preview); a start asks it live.
"""

import json

from domain.slot import Model, Placement, Rung, Where
from runtime import machine, slots


def _tried_argument(tried: list[Rung]) -> str:
    """`slot:model` for one rung, a bare `slot` for every rung on it."""
    return ",".join(r.slot if r.model is None else f"{r.slot}:{r.model.value}" for r in tried)


def _nowhere(reason: str) -> Where:
    return Where(placement=None, reason=reason)


def where(from_slot: str | None, tried: list[Rung], *, cached: bool) -> Where:
    try:
        argv = [machine.which("claude-acct"), "best", "--json"]
    except machine.CommandMissing as missing:
        return _nowhere(f"the rule cannot be asked: {missing}")
    if cached:
        argv.append("--cached")
    if from_slot:
        argv += ["--from", from_slot]
    if tried:
        argv += ["--tried", _tried_argument(tried)]
    try:
        done = machine.run(argv, timeout=90)
    except OSError as error:
        return _nowhere(f"`claude-acct best` could not run: {error}")
    if done.returncode != 0:
        said = (
            done.stderr.strip() or done.stdout.strip() or f"exit {done.returncode}"
        ).splitlines()
        return _nowhere(f"`claude-acct best` found nowhere to run: {said[0]}")
    try:
        answer = json.loads(done.stdout)
    except json.JSONDecodeError:
        return _nowhere(f"`claude-acct best` answered {done.stdout.strip()!r}, which is not JSON")
    if not isinstance(answer, dict) or not isinstance(answer.get("slot"), str):
        return _nowhere(f"`claude-acct best` answered {done.stdout.strip()!r}, which names no slot")
    named = answer.get("model")
    if named is None:
        model = Model.FABLE
    elif isinstance(named, str) and named in {m.value for m in Model}:
        model = Model(named)
    else:
        return _nowhere(
            f"`claude-acct best` named the model {named!r}, which the runtime cannot run"
        )
    slot = slots.slot_named(answer["slot"])
    if slot is None:
        return _nowhere(
            f"`claude-acct best` named {answer['slot']!r}, which accounts.json does not declare"
        )
    why = str(answer.get("why") or "").strip() or f"{slot.name} with {model.value}"
    return Where(
        placement=Placement(slot=slot.name, model=model, config_dir=slot.config_dir, why=why),
        reason=why,
    )
