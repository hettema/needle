"""Minimum evidence at the close door, without prescribing another review.

The owner's 2026-09-11 ruling replaces recursive repair reviews with one
independent review, disposition of its findings, and verification of repairs.
The record carries the evidence; the close checks that it is present, not a
reviewer's word count, number of passes, model, or call-table location.
Historical pass and verdict parsing remains available for the board's display.
"""

import re
from datetime import date

from board.parse import head_fields_of

HELD_FROM = date(2026, 9, 11)
"""Records before this date could identify their card without a Plan head."""

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


def record_faults(text: str, name: str) -> list[str]:
    """Require an identified reader and recorded checks, in either record form.

    This is a presence check, not proof that the reader was independent or
    that the checks passed: those judgments belong to the review and its
    author. The older `What was checked` section remains valid evidence,
    including for unfinished records closing under the new doctrine.
    """
    evidence_names = {
        "verification",
        "verification evidence",
        "what was checked",
        "tests",
        "evidence",
    }
    # Fenced metadata examples cannot identify a reader or open a section.
    # Commands and output fenced inside a real evidence section still count.
    lines: list[str] = []
    fence: str | None = None
    collecting = False
    evidence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            if collecting and stripped:
                evidence = True
            continue
        lines.append(line)
        if line.startswith("## "):
            collecting = line[3:].strip().casefold() in evidence_names
        elif collecting and stripped and not line.startswith("#"):
            evidence = True
    fields = head_fields_of("\n".join(lines))
    faults: list[str] = []
    if not any(f.key.casefold() == "reviewer" and f.value.strip() for f in fields):
        faults.append(f"{name}: name the independent reader in a nonempty `**Reviewer:**` head")
    evidence = evidence or any(
        f.key.casefold() in evidence_names and f.value.strip() for f in fields
    )
    if not evidence:
        faults.append(
            f"{name}: record verification evidence in `**Verification:**` or a nonempty "
            "Verification, What was checked, Tests, or Evidence section"
        )
    return faults
