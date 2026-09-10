"""Every finding in a review record says its class, so the doctrine's loop can be read.

Card #60 rewrote the one text's verification rules as a thesis: the text and its
re-anchor will move the rate of verification-class findings per carded close.
The measure never depends on memory (`docs/HOW-WE-WORK.md` §7), and before that
card no finding line said what kind of finding it was, so the class could only
be sieved by keyword and judged by hand — a count of who looked, not who
slipped. The loop begins by creating the trace: from 2026-09-06 every
disposition line in `docs/reviews/` opens with one of five classes in brackets,
and this ratchet refuses a record that leaves one out, because an unclassed line
makes the count silently wrong.

The classes are the review's own lenses plus the one this loop reads:
`[feature]`, `[seam]`, `[boundary]`, `[verification]`, `[record]`
(`docs/reviews/README.md`). Records from before the rule are history and are
not rewritten; the date in the filename is what decides.
"""

import re
from datetime import date
from pathlib import Path

from board.parse import review_of
from board.review_rules import dated
from tests.ratchets.paths import REPO

REVIEWS = REPO / "docs" / "reviews"
FROM = date(2026, 9, 6)
CLASSES = ("feature", "seam", "boundary", "verification", "record")
FINDING = re.compile(r"^\s*(\d+)\.\s+(.*)$")
CLASSED = re.compile(r"^\[(" + "|".join(CLASSES) + r")\]\s+\S")


def dispositions(text: str) -> list[tuple[int, str]]:
    """(line number, text) of every finding under `## Dispositions`, as the
    one reader finds them (`board.parse.review_of`, card #110, ruling 4):
    the ratchet's own walk read fenced examples the reader strips and
    indented lists the reader does not count, so the two disagreed on what
    a disposition was. The text is the line's own, after its number, so the
    class is read where the writer put it."""
    lines = text.split("\n")
    found: list[tuple[int, str]] = []
    for disposition in review_of(text, "").dispositions:
        finding = FINDING.match(lines[disposition.line - 1])
        found.append((disposition.line, finding.group(2) if finding else ""))
    return found


def unclassed(records: list[Path], since: date) -> list[str]:
    faults: list[str] = []
    for record in records:
        when = dated(record.name)
        if when is None or when < since:
            continue
        for number, text in dispositions(record.read_text(encoding="utf-8")):
            if not CLASSED.match(text):
                faults.append(f"{record.name}:{number} {text[:60]!r}")
    return faults


def test_every_finding_says_its_class():
    faults = unclassed(sorted(REVIEWS.glob("*.md")), FROM)
    assert not faults, (
        "these findings name no class, so the doctrine's loop cannot count them: "
        + "; ".join(faults)
        + f" — open each with one of {', '.join(f'[{c}]' for c in CLASSES)}"
    )


# ── the refusal, rehearsed on fixtures ────────────────────────────────

RECORD = """# Review — a fixture

**Plan:** docs/plans/done/x.md

## The passes

1. **The feature.** words.

## Dispositions

1. [feature] The door opened twice — FIXED in abc1234
2. [verification] The README claimed a citation that did not exist — FIXED in abc1235

## What was checked
- 1. not a finding, a list item outside Dispositions
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_classed_record_passes_and_only_dispositions_are_read(tmp_path):
    record = _write(tmp_path, "2026-09-07-a-fixture.md", RECORD)
    assert unclassed([record], FROM) == []


def test_an_unclassed_finding_is_named_with_its_line(tmp_path):
    record = _write(
        tmp_path, "2026-09-07-a-fixture.md", RECORD.replace("2. [verification] ", "2. ")
    )
    faults = unclassed([record], FROM)
    assert len(faults) == 1 and faults[0].startswith("2026-09-07-a-fixture.md:12")


def test_a_word_outside_the_five_is_refused(tmp_path):
    record = _write(tmp_path, "2026-09-07-a-fixture.md", RECORD.replace("[feature]", "[bug]"))
    assert len(unclassed([record], FROM)) == 1


def test_records_from_before_the_rule_are_history(tmp_path):
    record = _write(tmp_path, "2026-09-05-a-fixture.md", RECORD.replace("[feature] ", ""))
    assert unclassed([record], FROM) == []
