"""What a review record owes before its card can close (card #110).

`docs/HOW-WE-WORK.md` §13 says a repair names who else it reaches and what
it assumes, that a cold reader of another make tries to break both before
the round ships, and that its verdict is on the record. This module is the
one place that reads a parsed record (`board.parse.review_of`) against
those words: the close door refuses on its faults for every project on the
board, and Needle's own ratchet reads its records through the same rules,
so the two cannot disagree on what a line owes. The record's filename date
decides whether the rules apply at all (ruling 3): a record dated on or
before the day this card folded was written under the old form and is
history.

Two kinds of fault: those the record alone shows — a fix line without a
half, a round with no verdict, a broken address nobody answered, a
structure the address grammar cannot stand on — and those only the board's
call table can show — a verdict naming a call the board has no row for, a
reader of the lane's own kind, an answer that never landed. The first are
pure over the `Review`; the second take a lookup, so the door supplies the
store and a ratchet without one still reads what it can.
"""

import re
from collections.abc import Callable
from datetime import date

from domain.call import Call
from domain.document import Fate, Review
from domain.slot import Make

HELD_FROM = date(2026, 9, 11)
"""The first filename date a record is held to the fix-line, verdict and
repair-mark forms: the day after card #110 folded (2026-09-10). A record
dated on or before the fold's day closes as it did before, whatever passes
it runs afterwards — the fold's day is exempt whole because a same-day
record cannot say from its name whether it began before or after the
fold (ruling 3)."""

_DATED = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-")


def dated(name: str) -> date | None:
    """The date a record's filename opens with, or None when it has none —
    which is not the README's shape."""
    head = _DATED.match(name)
    if head is None:
        return None
    try:
        return date(int(head[1]), int(head[2]), int(head[3]))
    except ValueError:
        return None


def held(name: str, since: date = HELD_FROM) -> bool:
    """Whether a record by this name is held to the forms."""
    when = dated(name)
    return when is not None and when >= since


def record_faults(review: Review, name: str) -> list[str]:
    """Every fault the record alone shows, each naming the record and the
    line, in the order the door and the ratchet report them:

    - a FIXED line with no passes section to sit under, or under no `###
      Pass N` heading, is structure the address grammar cannot stand on;
    - a FIXED line lacking `reaches` or `assumes` (item 1);
    - a pass whose findings hold a FIXED line and no verdict under it (item
      2) — a round of repairs nobody read cold;
    - a verdict line not in the README's form;
    - an address a verdict broke with no later disposition marked `[repair
      of <address>]` (item 2) — a broken claim nobody answered.
    """
    faults: list[str] = []
    fixes = [d for d in review.dispositions if d.fate == Fate.FIXED]
    if fixes and not review.passes:
        faults.append(
            f"{name}: {len(fixes)} FIXED line(s) and no `## The passes` section — the record "
            "is not in docs/reviews/README.md's shape, so no round can be told from another"
        )
        return faults
    for fix in fixes:
        if fix.pass_number is None:
            faults.append(
                f"{name}:{fix.line} FIXED under no `### Pass N` heading — a fix line's address "
                "is its pass and its number, so its verdict and its repairs can name it"
            )
    for fix in fixes:
        missing = [
            half
            for half, value in (("reaches", fix.reaches), ("assumes", fix.assumes))
            if not value
        ]
        if missing:
            faults.append(
                f"{name}:{fix.line} FIXED says no {' or '.join(missing)} — a fix line ends "
                "`FIXED in <sha>; reaches <who else>; assumes <what>` (docs/reviews/README.md)"
            )
    verdicts_by_pass: dict[int, list] = {}
    for verdict in review.verdicts:
        verdicts_by_pass.setdefault(verdict.pass_number, []).append(verdict)
        if not verdict.call:
            faults.append(
                f"{name}:{verdict.line} a verdict not in the form `Read cold by <who> on <sha>, "
                "call <n>: complete` or `…: broke <pass.finding>, … — <its words>`"
            )
    rounds = sorted({fix.pass_number for fix in fixes if fix.pass_number is not None})
    for number in rounds:
        if number not in verdicts_by_pass:
            faults.append(
                f"{name}: pass {number}'s round has FIXED lines and no verdict under it — every "
                "round's repairs are read cold before they ship (HOW-WE-WORK §13)"
            )
    answered = {d.repair_of for d in review.dispositions if d.repair_of is not None}
    for verdict in review.verdicts:
        for address in verdict.broke:
            if address not in answered:
                faults.append(
                    f"{name}:{verdict.line} broke {address} and no disposition is marked "
                    f"`[repair of {address}]` — every claim the reader broke gets a disposition: "
                    "a fix with its own line, or a record-only correction"
                )
    return faults


def verdict_faults(
    review: Review,
    name: str,
    *,
    call_of: Callable[[int], Call | None],
    lane_slot: str | None,
    landed: Callable[[Call], bool],
) -> list[str]:
    """The faults only the board's call table shows (item 2, ruling 5): a
    verdict's call has a row, its colleague is of the other kind — `codex`
    for a lane of Claude's, anything else for a Codex lane — and its answer
    landed after the call. `lane_slot` is the slot of the session that held
    the lane, None when the board never saw one, which reads as a lane of
    Claude's."""
    faults: list[str] = []
    own_kind_is_codex = lane_slot == Make.CODEX
    for verdict in review.verdicts:
        if not verdict.call:
            continue
        call = call_of(verdict.call)
        if call is None:
            faults.append(
                f"{name}:{verdict.line} names call {verdict.call}, which the board has no row "
                "for — a cold read goes through `needle call` so the call is a row, not a launch"
            )
            continue
        reader_is_codex = call.slot == Make.CODEX
        if reader_is_codex == own_kind_is_codex:
            faults.append(
                f"{name}:{verdict.line} call {verdict.call} reached {call.name} on {call.slot}, "
                "a colleague of the lane's own kind — the cold reader is of the other make"
            )
        if not landed(call):
            faults.append(
                f"{name}:{verdict.line} call {verdict.call}'s answer never landed after the "
                "call — a verdict quotes an answer the board saw arrive"
            )
    return faults
