"""A release the board would not make without the owner is decided on what
the release would carry, never on what the folding session itself changed
(card #139, item 6).

*The leak, 2026-09-12.* Hello Revenue's archive gate refuses to file a
finished plan while production paths on the shared branch have not reached
the stable one, and its documented way past that refusal is to promote the
stable branch. That gate reads a *range*. So a rule that asked "did this
session touch the migrations folder?" would hold the first night's schema
change and then let the very next ordinary fix — a typo, a copy change,
anything — promote it to get past a refusal it did not cause. One in five
migrations that reach that branch rewrite or delete live rows on the
container's next boot, and the suite has never seen those rows. The narrow
read is not a weaker version of this rule; it is the defect with a check in
front of it.

*What this holds, and how.* It drives the real fold, on real git, in the
state where the two readings disagree: the session folding here changed one
ordinary file and nothing else, so a decision made on its own change would
promote, and the promotion must not happen. It also asserts the disagreement
itself, so a later reader can see which of the two readings is load-bearing
without running anything.

An earlier version of this file built both inputs by hand and asserted they
differed, touching none of the code that decides — so narrowing the
production read would have left it green while its own docstring claimed the
opposite. That was caught by the independent read of 2026-09-13 (finding 5)
and is why this one goes through the verb. No function, call or procedure is
named in the assertions: a better mechanism may replace today's as long as
the wider read is what decides.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from board.release import carried
from runtime import git
from tests.api import test_doors as doors
from tests.api.test_a_release_waits_for_the_owner import (
    CANNOT_UNDO,
    SLUG,
    code,
    declare,
    lane_for,
    touch,
)
from tests.api.test_dial import number_of

client = doors.client
repo = doors.repo
quick = doors.quick
code = code

PRICING = "The pricing rule, judged against a real season"
TIDES = "The tide table is the harbour's own"


def test_an_ordinary_fix_does_not_promote_the_change_to_stored_data_beside_it(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    stable = doors.git(code, "rev-parse", "origin/main")

    # One session the board started leaves a change to stored data on the
    # shared branch. However it got there is not this test's subject.
    first = lane_for(client, code, number_of(client, PRICING), "the-pricing-rule")
    touch(first, CANNOT_UNDO, "RATE = 2\n")
    doors.git(first, "push", "-q", "origin", "HEAD:develop")
    doors.git(code, "fetch", "-q", "origin")

    # The ordinary fix that follows changed one file, and not that one.
    second = lane_for(client, code, number_of(client, TIDES), "the-tide-table")
    doors.git(second, "merge", "-q", "--ff-only", "origin/develop")
    touch(second, "README.md", "spelled right\n")

    its_own = sorted(git.lane_files(second, birth=None, tip=None))
    assert CANNOT_UNDO not in its_own
    assert carried(its_own, [CANNOT_UNDO]) == []  # a narrow read sees nothing to wait for

    would_carry = git.release(second, ahead="HEAD")
    assert would_carry.read
    assert carried(would_carry.files, [CANNOT_UNDO]) == [CANNOT_UNDO]  # the range does

    # The verb, for real. The stable branch must not have moved.
    assert main(["fold", "--worktree", str(second), "--main"]) == 0
    said = capsys.readouterr().out
    assert "main not promoted" in said
    assert doors.git(code, "rev-parse", "origin/main") == stable


def test_a_night_that_carries_nothing_of_that_shape_still_ships(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    """The other direction, which is the outcome the owner rejected on
    evidence: a rule that holds every release stops the switch shipping
    anything at all."""
    declare(client, CANNOT_UNDO)
    lane = lane_for(client, code, number_of(client, TIDES), "the-tide-table")
    touch(lane, "README.md", "spelled right\n")
    assert main(["fold", "--worktree", str(lane), "--main"]) == 0
    assert "main promoted" in capsys.readouterr().out
    assert doors.git(code, "rev-parse", "origin/main") == doors.git(lane, "rev-parse", "HEAD")
