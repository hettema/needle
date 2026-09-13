"""The fold reaches origin and the checkout follows (plan 03, item 6), on
real git in temporary repositories: a bare origin, a main checkout on
develop, and a lane worktree."""

import subprocess
from pathlib import Path

import pytest

from runtime import git


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
def repos(tmp_path: Path) -> tuple[Path, Path]:
    """(origin, checkout): origin holds develop and main; the checkout is on develop."""
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
    return origin, checkout


def lane(checkout: Path, name: str) -> Path:
    path = checkout / ".claude" / "worktrees" / name
    sh(checkout, "worktree", "add", "-q", "-b", name, str(path))
    return path


def test_worktrees_and_edits_are_read_from_git(repos: tuple[Path, Path]):
    _, checkout = repos
    path = lane(checkout, "card-7-the-thing")
    trees = git.worktrees(checkout)
    assert trees[str(checkout)] == "develop" and trees[str(path)] == "card-7-the-thing"
    assert git.card_of_branch("card-7-the-thing") == 7 and git.card_of_branch("develop") is None
    (path / "a.py").write_text("x\n")
    (path / "README.md").write_text("two\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "two")
    assert git.changed_files(path) == {"README.md", "a.py"}
    assert git.tracked_changes(path) == []
    (path / "README.md").write_text("three\n")
    assert git.tracked_changes(path) == ["M README.md"]


def test_a_fold_is_proved_by_origin_develop_equalling_head_and_the_checkout_follows(
    repos: tuple[Path, Path],
):
    origin, checkout = repos
    path = lane(checkout, "card-7-the-thing")
    tip_before = git.head(path)
    assert git.lane_folded(checkout, "card-7-the-thing", tip_before) is False, (
        "a zero-commit branch is an ancestor from birth and must never read as folded"
    )
    (path / "README.md").write_text("two\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "two")
    folded = git.fold(path, promote_main=False)
    assert folded.pushed and folded.tip == git.head(path) and folded.main_pushed is None
    assert sh(origin, "rev-parse", "develop") == folded.tip
    assert git.lane_folded(checkout, "card-7-the-thing", folded.tip) is True

    levelled = git.level(checkout)
    assert levelled.level is True and levelled.behind == 0 and levelled.note is None
    assert git.head(checkout) == folded.tip

    promoted = git.fold(path, promote_main=True)
    assert promoted.pushed and promoted.main_pushed is True
    assert sh(origin, "rev-parse", "main") == folded.tip
    assert git.level(checkout).main_updated
    assert git.is_ancestor(checkout, folded.tip, "origin/main") is True
    # The branch deleted at the fold: the recorded birth is what still proves it.
    sh(checkout, "worktree", "remove", str(path))
    sh(checkout, "branch", "-D", "card-7-the-thing")
    assert git.lane_folded(checkout, "card-7-the-thing", folded.tip) is None
    assert git.lane_folded(checkout, "card-7-the-thing", folded.tip, tip_before) is True
    assert git.lane_folded(checkout, "card-7-the-thing", tip_before, tip_before) is False


def test_a_dirty_worktree_does_not_fold_and_a_dirty_checkout_is_not_touched(
    repos: tuple[Path, Path],
):
    _, checkout = repos
    path = lane(checkout, "card-8-dirty")
    (path / "README.md").write_text("dirty\n")
    refused = git.fold(path, promote_main=False)
    assert not refused.pushed and "uncommitted work: README.md" in refused.words

    (path / "README.md").write_text("two\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "two")
    assert git.fold(path, promote_main=False).pushed
    (checkout / "README.md").write_text("owner's edit\n")
    levelled = git.level(checkout)
    assert levelled.level is False and levelled.behind == 1
    assert "uncommitted work that is not the runtime's (README.md)" in (levelled.note or "")
    assert (checkout / "README.md").read_text() == "owner's edit\n"


def test_a_checkout_off_develop_is_named_not_moved(repos: tuple[Path, Path]):
    _, checkout = repos
    sh(checkout, "checkout", "-q", "-b", "elsewhere")
    levelled = git.level(checkout)
    assert levelled.level is True and "on elsewhere, not develop" in (levelled.note or "")


def test_a_checkout_ahead_of_origin_is_rebased_and_pushed_when_clean(repos: tuple[Path, Path]):
    origin, checkout = repos
    path = lane(checkout, "card-9-lane")
    (path / "README.md").write_text("lane\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "lane")
    assert git.fold(path, promote_main=False).pushed
    # The owner's session committed in the main checkout and never pushed.
    (checkout / "OWNER.md").write_text("main thread\n")
    sh(checkout, "add", "OWNER.md")
    sh(checkout, "commit", "-q", "-m", "main thread")
    levelled = git.level(checkout)
    assert levelled.level is True and levelled.behind == 0
    assert "rebased and pushed 1 local commit(s)" in (levelled.note or "")
    assert sh(origin, "rev-parse", "develop") == git.head(checkout)
    assert (checkout / "README.md").read_text() == "lane\n"


def test_a_checkout_ahead_of_origin_with_a_conflict_is_left_and_named(repos: tuple[Path, Path]):
    origin, checkout = repos
    path = lane(checkout, "card-9-lane")
    (path / "README.md").write_text("lane\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "lane")
    assert git.fold(path, promote_main=False).pushed
    (checkout / "README.md").write_text("owner\n")
    sh(checkout, "commit", "-q", "-am", "owner")
    before = git.head(checkout)
    levelled = git.level(checkout)
    assert levelled.level is False and "rebase conflicts" in (levelled.note or "")
    assert git.head(checkout) == before and git.tracked_changes(checkout) == []
    assert sh(origin, "rev-parse", "develop") != before


# ── what a release would carry (card #139, item 1) ─────────────────────


def test_a_release_reads_the_range_between_the_stable_and_the_shared_branch(
    repos: tuple[Path, Path],
):
    """Level, ahead, and the same question asked of a lane's own HEAD. The
    verb decides nothing; it answers what a promotion would carry."""
    _, checkout = repos
    level = git.release(checkout)
    assert level.read and level.files == [] and level.commits == 0 and level.note is None

    path = lane(checkout, "card-9-lane")
    (path / "alembic").mkdir()
    (path / "alembic" / "210_rewrite.py").write_text("UPDATE campaigns\n")
    (path / "notes.md").write_text("two\n")
    sh(path, "add", "-A")
    sh(path, "commit", "-q", "-m", "two")
    # Before the fold, the lane asks what its own promotion would carry.
    mine = git.release(path, ahead="HEAD")
    assert mine.read and mine.commits == 1
    assert sorted(mine.files) == ["alembic/210_rewrite.py", "notes.md"]

    assert git.fold(path, promote_main=False).pushed
    git.fetch(checkout)
    ahead = git.release(checkout)
    assert ahead.read and ahead.commits == 1
    assert sorted(ahead.files) == ["alembic/210_rewrite.py", "notes.md"]
    assert sorted(ahead.files) == sorted(
        line for line in sh(checkout, "diff", "--name-only", "origin/main...origin/develop").split()
    )


def test_a_checkout_with_no_stable_branch_says_so_rather_than_answering_empty(tmp_path: Path):
    """"Nothing to carry" and "nothing could be seen" are the two sides the
    refusal must tell apart; a project with no stable branch is the second."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    sh(origin, "init", "--bare", "-b", "develop")
    checkout = tmp_path / "checkout"
    sh(tmp_path, "clone", "-q", str(origin), str(checkout))
    sh(checkout, "checkout", "-q", "-b", "develop")
    (checkout / "README.md").write_text("one\n")
    sh(checkout, "add", "README.md")
    sh(checkout, "commit", "-q", "-m", "one")
    sh(checkout, "push", "-q", "origin", "develop")
    sh(checkout, "fetch", "-q", "origin")
    found = git.release(checkout)
    assert not found.read and found.files == [] and "origin/main" in (found.note or "")


def test_a_checkout_that_cannot_be_read_at_all_is_not_a_missing_stable_branch(tmp_path: Path):
    """The two unreadable cases say different things: a reader told "there is
    no origin/main here" about a directory that does not exist would go
    looking for a branch (the four-state run for item 1, 2026-09-13)."""
    nowhere = git.release(tmp_path / "nowhere")
    assert not nowhere.read and "is not a checkout this machine can read" in (nowhere.note or "")


def test_a_fold_that_holds_the_release_carries_the_hold_in_the_same_push(
    repos: tuple[Path, Path],
):
    """One push carries the work and the standing hold that keeps the work
    finishing behind it from stalling (item 3); a hold already standing is
    left exactly as it is, because the owner is about to read its reason."""
    _, checkout = repos
    path = lane(checkout, "card-9-lane")
    (path / "notes.md").write_text("two\n")
    sh(path, "add", "notes.md")
    sh(path, "commit", "-q", "-m", "two")
    folded = git.fold(path, promote_main=False, hold="docs/board/HOLD.md", why="a reason")
    assert folded.pushed and folded.held == "docs/board/HOLD.md"
    assert (path / "docs" / "board" / "HOLD.md").read_text().endswith("a reason\n")
    assert git.tracked_changes(path) == []

    second = lane(checkout, "card-10-lane")
    sh(second, "merge", "-q", "--ff-only", "origin/develop")
    assert (second / "docs" / "board" / "HOLD.md").read_text().endswith("a reason\n")
    (second / "more.md").write_text("three\n")
    sh(second, "add", "more.md")
    sh(second, "commit", "-q", "-m", "three")
    again = git.fold(second, promote_main=False, hold="docs/board/HOLD.md", why="another reason")
    assert again.pushed and again.held is None
    assert (second / "docs" / "board" / "HOLD.md").read_text().endswith("a reason\n")


def test_a_fold_that_could_not_push_leaves_no_hold_commit_behind(repos: tuple[Path, Path]):
    """A hold commit stranded in a lane rides the next fold, and if the owner
    promoted in between the shared branch carries a standing hold no release
    asked for — which makes a project's archive gate stand aside for good."""
    _, checkout = repos
    path = lane(checkout, "card-9-lane")
    (path / "notes.md").write_text("two\n")
    sh(path, "add", "notes.md")
    sh(path, "commit", "-q", "-m", "two")
    # Another lane lands first, so this one's push is not a fast-forward.
    other = lane(checkout, "card-10-lane")
    (other / "other.md").write_text("three\n")
    sh(other, "add", "other.md")
    sh(other, "commit", "-q", "-m", "three")
    assert git.fold(other, promote_main=False).pushed

    was = git.head(path)
    folded = git.fold(path, promote_main=False, hold="docs/board/HOLD.md", why="a reason")
    assert not folded.pushed and folded.held is None
    assert git.head(path) == was
    assert not (path / "docs" / "board" / "HOLD.md").exists()
    assert git.tracked_changes(path) == []


def test_a_hold_path_that_leaves_the_project_is_refused(repos: tuple[Path, Path]):
    """The declaration is the owner's words; a path climbing out of the
    project would have the fold write outside the repository it is folding."""
    _, checkout = repos
    path = lane(checkout, "card-9-lane")
    (path / "notes.md").write_text("two\n")
    sh(path, "add", "notes.md")
    sh(path, "commit", "-q", "-m", "two")
    folded = git.fold(path, promote_main=False, hold="../../escaped.md", why="a reason")
    assert folded.pushed and "not a place inside this project" in (folded.held or "")
    assert not (Path(checkout).parent / "escaped.md").exists()
