"""Every fix in a review record says who else it reaches and what it assumes,
every round of repairs carries a cold reader's verdict, and every claim the
reader broke has a disposition — so the record proves the read that
`docs/HOW-WE-WORK.md` §13 asks for ran (card #110).

The close door holds this for every project on the board, reading the record
it is given through `board.review_rules`; this ratchet holds Needle's own
records through the same rules, so a record that would refuse at the close
is red in the suite first, and so the rules the door applies to Hello
Revenue's records are the rules Needle's own records pass. The filename date
decides (ruling 3): a record dated on or before the day that card folded is
history and is not rewritten. What the ratchet cannot read — that a verdict's
call is a row the board holds, of the other make, whose answer landed — is
the door's alone, since a ratchet reads the repository and not the store.
"""

from pathlib import Path

from board.parse import review_of
from board.review_rules import held, record_faults
from tests.ratchets.paths import REPO

REVIEWS = REPO / "docs" / "reviews"


def faults_of(records: list[Path]) -> list[str]:
    faults: list[str] = []
    for record in records:
        if record.name == "README.md" or not held(record.name):
            continue
        review = review_of(record.read_text(encoding="utf-8"), record.name)
        faults.extend(record_faults(review, record.name))
    return faults


def test_every_fix_says_who_else_it_reaches():
    faults = faults_of(sorted(REVIEWS.glob("*.md")))
    assert not faults, (
        "these records skip the read HOW-WE-WORK §13 asks for, and the close would refuse "
        "them: " + "; ".join(faults)
    )


# ── the refusal, rehearsed on fixtures ────────────────────────────────

RECORD = """# Review — a fixture

**Plan:** docs/plans/done/x.md

## The passes

1. **The feature.** words.
Read cold by Codex (01a08a3a) on abc1234, call 3: complete

## Dispositions

### Pass 1's findings

1. [feature] The door opened twice — FIXED in abc1234; reaches the two doors that share the
   latch; assumes nobody opens one while the other is open
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_record_in_the_form_is_green_and_a_bare_line_is_red(tmp_path):
    assert faults_of([_write(tmp_path, "2026-09-11-a-fixture.md", RECORD)]) == []
    bare = RECORD.replace(
        "; reaches the two doors that share the\n   latch; assumes nobody opens one while the "
        "other is open",
        "",
    )
    faults = faults_of([_write(tmp_path, "2026-09-11-a-fixture.md", bare)])
    assert len(faults) == 1 and faults[0].startswith("2026-09-11-a-fixture.md:14 FIXED says no")


def test_a_record_dated_on_or_before_the_fold_is_history(tmp_path):
    bare = RECORD.replace("; reaches", "; formerly")
    assert faults_of([_write(tmp_path, "2026-09-10-a-fixture.md", bare)]) == []
    assert faults_of([_write(tmp_path, "a-fixture.md", bare)]) == []
