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
