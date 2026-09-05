"""What a card shares with what is running: the plan's footprint against
every live lane's declared footprint and actual edits — and, once lanes run,
whether two of them have drifted into each other's files.

Shared ground is a cost the card shows, never a door it closes (INTENT.md
lesson 4, rewritten 2026-09-05): a plan declares what it touches by naming
files in backticks; a lane's actual edits are what its checkout has changed.
Both are named on the Start door so the session rebases early, and the fold
— rebase, full suite, fast-forward — settles what they share. While lanes
run the board re-reads every live worktree's actual diff and names two
lanes editing the same file as colliding, on both cards, before the fold
(plan 07, item 2): that is about two lanes editing now, and stays. Pure: the
caller reads the files and the git state and hands them in.
"""

import re
from collections.abc import Callable

from domain.lane import Collision, CollisionVerdict

_NAMED_PATH = re.compile(r"`([\w.-]+(?:/[\w.-]+)+\.\w+)(?:::[\w.:]+|#[\w.-]+|:\d+)?`")
SECOND_TO_FOLD = "The second to fold rebases."


def footprint(text: str, exists: Callable[[str], bool]) -> set[str]:
    """The repository files a document names in backticks and that exist."""
    return {path for path in _NAMED_PATH.findall(text) if exists(path)}


def _shown(files: list[str]) -> str:
    return ", ".join(files[:3]) + ("…" if len(files) > 3 else "")


def _lane(number: int) -> str:
    return f"#{number}'s lane"


def verdict(
    mine: set[str],
    *,
    editing: dict[int, set[str]],
    declared: dict[int, set[str]],
) -> Collision:
    """`editing` and `declared` map a live lane's card to the files it is
    changing now, and to the files its plan names. Every lane on this
    plan's ground is named, an edit in progress before a plan's word, so
    the door says all of what the lane will rebase over."""
    if not mine:
        return Collision(
            verdict=CollisionVerdict.UNKNOWN,
            sentence="The plan names no files, so nothing can prove it runs beside the others.",
            files=[],
            cards=[],
        )
    clauses: list[str] = []
    files: set[str] = set()
    cards: set[int] = set()
    for who, theirs in editing.items():
        overlap = sorted(mine & theirs)
        if overlap:
            clauses.append(f"{_lane(who)} is editing {_shown(overlap)} right now")
            files |= set(overlap)
            cards.add(who)
    for who, theirs in declared.items():
        overlap = sorted((mine & theirs) - files)
        if overlap:
            clauses.append(f"{_lane(who)}'s plan names {_shown(overlap)} too")
            files |= set(overlap)
            cards.add(who)
    if clauses:
        return Collision(
            verdict=CollisionVerdict.COLLIDES,
            sentence="Shares ground: " + "; ".join(clauses) + f". {SECOND_TO_FOLD}",
            files=sorted(files),
            cards=sorted(cards),
        )
    return Collision(
        verdict=CollisionVerdict.CLEAR,
        sentence="No running lane or trunk session touches this plan's files.",
        files=[],
        cards=[],
    )


def drift(editing: dict[int, set[str]]) -> dict[int, Collision | None]:
    """For every live lane, the other live lanes editing a file it is also
    editing, or None when nothing overlaps. `editing` maps a lane's card to
    the files its worktree has changed right now. Every pair is named on
    both sides, so each card says who it collides with and on what."""
    out: dict[int, Collision | None] = {}
    for who, files in editing.items():
        clauses: list[str] = []
        overlapping: set[str] = set()
        others: list[int] = []
        for other, theirs in editing.items():
            if other == who:
                continue
            overlap = sorted(files & theirs)
            if overlap:
                clauses.append(f"{_lane(other)} is also editing {_shown(overlap)}")
                overlapping |= set(overlap)
                others.append(other)
        if clauses:
            out[who] = Collision(
                verdict=CollisionVerdict.COLLIDES,
                sentence="; ".join(clauses) + ".",
                files=sorted(overlapping),
                cards=sorted(others),
            )
        else:
            out[who] = None
    return out
