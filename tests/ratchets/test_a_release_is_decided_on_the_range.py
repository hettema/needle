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
read is not a weaker version of this rule; it is the defect with a check
in front of it.

This test feeds the decision the two inputs and pins which one it uses. It
fails the moment the read narrows to the session's own change, whatever the
code around it looks like — no function name, no call, no procedure is
named here, so a better mechanism is free to arrive as long as the wider
read is what decides.
"""

import subprocess
from pathlib import Path

import pytest

from board.release import carried
from runtime import git

DECLARED = ["alembic/versions"]


def sh(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(cwd),
        },
    )
    return done.stdout.strip()


@pytest.fixture
def someone_elses_schema_change(tmp_path: Path) -> tuple[Path, Path]:
    """The night as it actually goes: one session's change to stored data is
    already on the shared branch and not on the stable one, and a second
    session — the ordinary fix — is about to fold something else entirely.

    Answers (the second session's own checkout, its worktree)."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    sh(origin, "init", "--bare", "-b", "develop")
    checkout = tmp_path / "checkout"
    sh(tmp_path, "clone", "-q", str(origin), str(checkout))
    sh(checkout, "checkout", "-q", "-b", "develop")
    (checkout / "README.md").write_text("one\n")
    sh(checkout, "add", "README.md")
    sh(checkout, "commit", "-q", "-m", "one")
    sh(checkout, "push", "-q", "origin", "develop", "develop:main")

    # The first session's schema change lands on the shared branch.
    versions = checkout / "alembic" / "versions"
    versions.mkdir(parents=True)
    (versions / "210_rewrite.py").write_text("op.execute('UPDATE campaigns SET strategy = …')\n")
    sh(checkout, "add", "-A")
    sh(checkout, "commit", "-q", "-m", "the first session's schema change")
    sh(checkout, "push", "-q", "origin", "develop")
    sh(checkout, "fetch", "-q", "origin")

    # The second session — an ordinary fix — touches nothing of that shape.
    lane = checkout / ".claude" / "worktrees" / "card-9-an-ordinary-fix"
    sh(checkout, "worktree", "add", "-q", "-b", "card-9-an-ordinary-fix", str(lane))
    (lane / "README.md").write_text("one, spelled right\n")
    sh(lane, "add", "README.md")
    sh(lane, "commit", "-q", "-m", "an ordinary fix")
    return checkout, lane


def test_the_ordinary_fix_is_refused_the_release_the_first_session_left(
    someone_elses_schema_change: tuple[Path, Path],
):
    checkout, lane = someone_elses_schema_change

    # Fed the session's own change, the decision sees nothing to wait for.
    its_own = sorted(git.lane_files(lane, birth=None, tip=None))
    assert its_own == ["README.md"]
    assert carried(its_own, DECLARED) == []

    # Fed the range the promotion would carry, it sees the waiting change —
    # put there by someone else, which is the whole point.
    would_carry = git.release(lane, ahead="HEAD")
    assert would_carry.read
    assert carried(would_carry.files, DECLARED) == ["alembic/versions"]

    # The two disagree, and the wider one is what the rule is decided on.
    assert carried(its_own, DECLARED) != carried(would_carry.files, DECLARED)


def test_a_release_that_carries_nothing_declared_is_not_held(tmp_path: Path):
    """The other direction, which is the outcome the owner rejected on
    evidence: a rule that holds every release stops the switch shipping
    anything. An ordinary night carries no declared path and waits for
    nobody."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    sh(origin, "init", "--bare", "-b", "develop")
    checkout = tmp_path / "checkout"
    sh(tmp_path, "clone", "-q", str(origin), str(checkout))
    sh(checkout, "checkout", "-q", "-b", "develop")
    (checkout / "README.md").write_text("one\n")
    sh(checkout, "add", "README.md")
    sh(checkout, "commit", "-q", "-m", "one")
    sh(checkout, "push", "-q", "origin", "develop", "develop:main")
    sh(checkout, "fetch", "-q", "origin")
    lane = checkout / ".claude" / "worktrees" / "card-9-an-ordinary-fix"
    sh(checkout, "worktree", "add", "-q", "-b", "card-9-an-ordinary-fix", str(lane))
    (lane / "README.md").write_text("one, spelled right\n")
    sh(lane, "add", "README.md")
    sh(lane, "commit", "-q", "-m", "an ordinary fix")

    would_carry = git.release(lane, ahead="HEAD")
    assert would_carry.read and would_carry.files == ["README.md"]
    assert carried(would_carry.files, DECLARED) == []
