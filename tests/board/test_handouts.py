"""What a plan hands out, against the machine's roles and the lane's dispatches (plan 12)."""

from datetime import UTC, datetime

from board.handouts import handouts_for, handouts_row
from board.parse import handouts_of, parse_document
from domain.document import DocumentKind
from domain.handout import Dispatch, Handout

AT = datetime(2026, 9, 5, tzinfo=UTC)

PLAN = """# The booking office stops growing into one file

**Status:** PENDING
**Effort gate:** xhigh — seams nobody has named.

## Intent

One file becomes many.

## Items

### 1. Name the seams
Read every path. Done means: a list. Hands out: search — every function in
`office/bookings.py` and every caller; verifies the file at each line named.

### 2. Split along them
Move each path. Done means: nothing over 400 lines.
**Hands out:** `execution` — the move of each path, and the suite after each
move; verify: the suite's own output by re-running the failing test it names.

3. **The judgment.** Which seams are real is decided here.

```
Hands out: search — a fenced example, not a handout
```
"""


def test_every_hands_out_sentence_is_read_with_its_item_role_what_and_verification():
    found = handouts_of(PLAN)
    assert found == [
        Handout(
            item="1. Name the seams",
            role="search",
            what="every function in office/bookings.py and every caller",
            verifies="the file at each line named",
        ),
        Handout(
            item="2. Split along them",
            role="execution",
            what="the move of each path, and the suite after each move",
            verifies="the suite's own output by re-running the failing test it names",
        ),
    ]
    document = parse_document(
        PLAN, kind=DocumentKind.PLAN, path="docs/plans/p.md", archived=False, read_at=AT
    )
    assert document.handouts == found


def test_a_sentence_before_any_item_and_one_naming_no_verification_are_still_read():
    found = handouts_of("# T\n\nHands out: search — the log read.\n\n1. **Item.** x\n")
    assert found == [Handout(item=None, role="search", what="the log read", verifies=None)]
    listed = handouts_of("# T\n\n1. **Item.** x. Hands out: execution — the sweep\n")
    assert listed == [Handout(item="1. Item", role="execution", what="the sweep", verifies=None)]


def test_the_verification_is_read_however_the_sentence_introduces_it():
    """Plan 13's own sentence, written before the README fixed the form."""
    found = handouts_of(
        "# T\n\n### 1. The grammar\nx. Hands out: `execution` runs the reader over the archive "
        "and tables the counts; the lane verifies by opening three plans the table says are "
        "marked and one it says are not.\n"
    )
    assert found == [
        Handout(
            item="1. The grammar",
            role="execution",
            what="runs the reader over the archive and tables the counts",
            verifies="opening three plans the table says are marked and one it says are not",
        )
    ]


def test_a_plan_that_hands_nothing_out_has_no_handouts():
    assert handouts_of("# T\n\n## Intent\n\nJudgment only. Hands are on deck.\n") == []


def test_a_mention_of_the_sentence_in_prose_is_not_a_handout():
    """Plan 12's own item 1 says an item "ends with a `Hands out:` sentence
    naming the role"; read anywhere on the line, that was a handout to the
    role "sentence" (review pass 1). Only a sentence of its own counts."""
    prose = (
        "# T\n\n### 1. The grammar\nThe README says an item ends with a `Hands out:` sentence "
        "naming the role, what it hands out, and what is verified.\n"
        "A plan says what it hands out. Nothing here is handed out: judgment.\n"
    )
    assert handouts_of(prose) == []
    ends_a_sentence = handouts_of(
        "# T\n\n### 1. A\nRead it all. Hands out: search — the callers.\n"
        "- a bullet that follows is not part of the sentence\n"
    )
    assert ends_a_sentence == [
        Handout(item="1. A", role="search", what="the callers", verifies=None)
    ]


def _document(*handouts: Handout):
    document = parse_document(
        "# T\n\n## Intent\n\nx\n",
        kind=DocumentKind.PLAN,
        path="docs/plans/p.md",
        archived=False,
        read_at=AT,
    )
    document.handouts = list(handouts)
    return document


SEARCH = Handout(item="1. A", role="search", what="w", verifies="v")
EXECUTION = Handout(item="2. B", role="execution", what="w", verifies=None)
PILOT = Handout(item="3. C", role="harbour-pilot", what="w", verifies="v")


def test_a_role_the_machine_names_passes_and_one_it_does_not_is_the_boards_line():
    known = handouts_for(_document(SEARCH, EXECUTION), ["top", "execution", "search"])
    assert known.named == [SEARCH, EXECUTION] and known.unknown == [] and known.verdict is None
    unknown = handouts_for(_document(SEARCH, PILOT, PILOT), ["execution", "search"])
    assert unknown.unknown == ["harbour-pilot"]
    assert unknown.verdict is not None
    assert '"harbour-pilot"' in unknown.verdict and "execution, search" in unknown.verdict


def test_with_no_roles_file_the_roles_cannot_be_checked_and_the_board_says_so():
    none = handouts_for(_document(SEARCH), None)
    assert none.unknown == ["search"]
    assert none.verdict is not None and "names no roles" in none.verdict
    assert handouts_for(_document(), None).verdict is None
    assert handouts_for(None, ["search"]).named == []


def _dispatch(role: str) -> Dispatch:
    return Dispatch(role=role, session_id="s", at=AT)


def test_the_row_counts_dispatched_against_named_per_role():
    row = handouts_row(
        [SEARCH, SEARCH, EXECUTION],
        [_dispatch("search"), _dispatch("search"), _dispatch("search")],
        "/srv/p/.claude/worktrees/card-1-x",
    )
    assert row == (
        "search ×3 (named 2), execution ×0 (named 1) — execution named and never dispatched"
    )


def test_an_unnamed_dispatch_is_said_and_nothing_is_written_for_nothing():
    row = handouts_row([SEARCH], [_dispatch("search"), _dispatch("Explore".lower())], "/w")
    assert row == "search ×1 (named 1), explore ×1 (named 0) — explore dispatched and never named"
    assert handouts_row([], [], "/w") is None
    assert handouts_row([], None, "/w") is None


def test_a_named_handout_with_no_transcript_to_read_says_nothing_was_counted():
    row = handouts_row([SEARCH], None, "/w")
    assert row == (
        "search ×? (named 1) — no transcript of the lane was found at /w, so nothing was counted"
    )
    assert handouts_row([SEARCH], None, None) == (
        "search ×? (named 1) — the board knows no lane for this card, so nothing was counted"
    )
