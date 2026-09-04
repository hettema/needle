"""Whether a card can run beside what is running: the plan's footprint against
every live lane's declared footprint and actual edits.

Concurrency is visible before Start (INTENT.md lesson 4). A plan declares
what it touches by naming files in backticks; a lane's actual edits are what
its checkout has changed. Both count, and the stronger reason — an edit in
progress — is reported first. Pure: the caller reads the files and the git
state and hands them in.
"""

import re
from collections.abc import Callable

from domain.lane import Collision, CollisionVerdict

_NAMED_PATH = re.compile(r"`([\w.-]+(?:/[\w.-]+)+\.\w+)(?:::[\w.:]+|#[\w.-]+|:\d+)?`")


def footprint(text: str, exists: Callable[[str], bool]) -> set[str]:
    """The repository files a document names in backticks and that exist."""
    return {path for path in _NAMED_PATH.findall(text) if exists(path)}


def _shown(files: list[str]) -> str:
    return ", ".join(files[:3]) + ("…" if len(files) > 3 else "")


def verdict(
    mine: set[str],
    *,
    editing: dict[str, set[str]],
    declared: dict[str, set[str]],
) -> Collision:
    """`editing` and `declared` map a lane's label (its card, or 'the trunk')
    to the files it is changing now, and to the files its plan names."""
    if not mine:
        return Collision(
            verdict=CollisionVerdict.UNKNOWN,
            sentence="The plan names no files, so nothing can prove it runs beside the others.",
            files=[],
        )
    for who, files in editing.items():
        overlap = sorted(mine & files)
        if overlap:
            return Collision(
                verdict=CollisionVerdict.COLLIDES,
                sentence=f"{who} is editing {_shown(overlap)} right now.",
                files=overlap,
            )
    for who, files in declared.items():
        overlap = sorted(mine & files)
        if overlap:
            return Collision(
                verdict=CollisionVerdict.COLLIDES,
                sentence=(
                    f"{who} has not opened {_shown(overlap)} yet, but its plan names the "
                    "same ground."
                ),
                files=overlap,
            )
    return Collision(
        verdict=CollisionVerdict.CLEAR,
        sentence="No running lane or trunk session touches this plan's files.",
        files=[],
    )
