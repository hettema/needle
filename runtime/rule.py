"""Where work runs next: asked of `claude-acct best`, never decided here.

The one rule on this machine lives in `claude-acct` (plan 02, ruling 1):
the slot with headroom on the strongest rung first, a weaker rung only when
no slot has a strong one, a slot holding the wrong identity or a spent
window refused. This module turns its JSON answer into a typed placement and
its refusal into a reason, and nothing more. `cached` reads the rule over the
per-slot cache the statusline keeps fresh (sub-second, for a card's
preview); a start asks it live.

The answer may name a make, a model and the tier the owner's ruling put the
rung in (card #63). None of the three is required: an answer without a make
is Claude's, the only make the rule knew when it was written, and an answer
without a tier is a rung shown without one. A make this runtime has no
launcher for is refused by the word the rule used, never run as the make we
happen to know.
"""

import json
from datetime import date

from domain.slot import Make, Placement, Rung, Tier, Where
from runtime import machine, slots


def _tried_argument(tried: list[Rung]) -> str:
    """`slot:model` for one rung, a bare `slot` for every rung on it."""
    return ",".join(r.slot if r.model is None else f"{r.slot}:{r.model}" for r in tried)


def _nowhere(reason: str) -> Where:
    return Where(placement=None, reason=reason)


def _tier(answer: dict[str, object]) -> Tier | None:
    """The owner's dated tier ruling for this rung, when the rule carried
    one whole. A partial tier — a rank with no date, a date that is not a
    date — is no tier: the board shows the rung without it rather than a
    ruling nobody can look up."""
    rank, ruled, why = answer.get("tier"), answer.get("tier_ruled_on"), answer.get("tier_why")
    if not isinstance(rank, int) or isinstance(rank, bool) or not isinstance(ruled, str):
        return None
    try:
        on = date.fromisoformat(ruled)
    except ValueError:
        return None
    return Tier(rank=rank, ruled_on=on, why=str(why or "").strip())


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
    named_make = answer.get("make")
    if named_make is None:
        make = Make.CLAUDE
    elif isinstance(named_make, str) and named_make in {m.value for m in Make}:
        make = Make(named_make)
    else:
        return _nowhere(
            f"`claude-acct best` named the make {named_make!r}, which this runtime has no "
            f"launcher for; it can launch {', '.join(m.value for m in Make)}"
        )
    named_model = answer.get("model")
    if named_model is not None and not isinstance(named_model, str):
        return _nowhere(
            f"`claude-acct best` named the model {named_model!r}, which is not a model's name"
        )
    model = named_model or None
    if make is Make.CLAUDE:
        slot = slots.slot_named(answer["slot"])
        if slot is None:
            return _nowhere(
                f"`claude-acct best` named {answer['slot']!r}, which accounts.json does not declare"
            )
        name, config_dir = slot.name, slot.config_dir
    else:
        # A make with no subscription ladder declares no slot in
        # accounts.json; its config directory is the make's own home.
        name, config_dir = answer["slot"], str(machine.codex_home())
    why = str(answer.get("why") or "").strip() or f"{model or 'the top rung'} on {name}"
    return Where(
        placement=Placement(
            slot=name,
            make=make,
            model=model,
            config_dir=config_dir,
            why=why,
            tier=_tier(answer),
        ),
        reason=why,
    )
