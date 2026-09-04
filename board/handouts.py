"""What a plan hands out, read against the machine's roles and the lane's
dispatches (plan 12, items 2 and 3).

Two pure judgments. Before the work: does every role the plan names exist on
this machine? A role it does not is a line on the card in the board's own
voice, as a plan with no gate is. After the work: what did the lane dispatch
against what the plan named, per role, in one row the close writes.
"""

from collections import Counter

from domain.document import Document
from domain.handout import Dispatch, Handout, Handouts


def handouts_for(document: Document | None, roles: list[str] | None) -> Handouts:
    """`roles` is what the machine's roles file names, as the runtime last
    read it; None when the machine has no such file."""
    named = document.handouts if document is not None else []
    if not named:
        return Handouts(named=[], unknown=[], verdict=None)
    wanted: list[str] = []
    for handout in named:
        if handout.role not in wanted:
            wanted.append(handout.role)
    if roles is None:
        return Handouts(
            named=named,
            unknown=wanted,
            verdict=(
                "This machine names no roles, so the roles this plan hands out to "
                f"({', '.join(wanted)}) cannot be checked; a plan names roles the machine's "
                "roles file defines."
            ),
        )
    unknown = [role for role in wanted if role not in roles]
    if not unknown:
        return Handouts(named=named, unknown=[], verdict=None)
    return Handouts(
        named=named,
        unknown=unknown,
        verdict=(
            f"This plan hands out to {_quoted(unknown)}, which this machine has not defined; "
            f"its roles are {', '.join(roles) if roles else 'none'}. A role is named in the "
            "machine's roles file before a plan names it."
        ),
    )


def _quoted(roles: list[str]) -> str:
    return ", ".join(f'"{role}"' for role in roles)


def handouts_row(
    named: list[Handout], dispatched: list[Dispatch] | None, where: str | None
) -> str | None:
    """The HANDED OUT row's text: what the plan named against what the lane
    dispatched, per role, in `machine burn`'s form. None when the plan named
    nothing and the lane dispatched nothing — nothing to say. `dispatched`
    is None when no transcript of the lane could be read at `where`, and
    `where` is None when the board knows no lane for the card."""
    counted = Counter(h.role for h in named)
    seen = Counter(d.role for d in dispatched) if dispatched is not None else None
    if not counted and not seen:
        return None
    roles: list[str] = []
    for role in [h.role for h in named] + [d.role for d in dispatched or []]:
        if role not in roles:
            roles.append(role)
    if seen is None:
        cells = ", ".join(f"{role} ×? (named {counted[role]})" for role in roles)
        why = (
            f"no transcript of the lane was found at {where}"
            if where is not None
            else "the board knows no lane for this card"
        )
        return f"{cells} — {why}, so nothing was counted"
    cells = ", ".join(f"{role} ×{seen[role]} (named {counted[role]})" for role in roles)
    never = [role for role in roles if counted[role] and not seen[role]]
    unnamed = [role for role in roles if seen[role] and not counted[role]]
    notes: list[str] = []
    if never:
        notes.append(f"{', '.join(never)} named and never dispatched")
    if unnamed:
        notes.append(f"{', '.join(unnamed)} dispatched and never named")
    return cells + (f" — {'; '.join(notes)}" if notes else "")
