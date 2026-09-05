"""A doctrine edit lands on a card, never as a tidy.

`docs/HOW-WE-WORK.md` is the one text every project on every machine reads at
its next session start, and `docs/INTENT.md` is the fixed point it serves. An
edit to either is intent-bearing by definition (plan 18, ruling 6), so it
travels as a suggestion marked `**Fix:** his`, becomes a card, and lands on that
card's close. `hooks/commit-msg` refuses the other route at commit time.

A hook is only as good as its arming, and it can be bypassed with
`--no-verify`, disarmed by a clone that never ran `needle hook install`, or
outrun by a lane whose `core.hooksPath` was set relative. So this reads the
effect rather than the mechanism: every commit since the hook was born that
touched either file and names no card. The machine repo's
`changes_without_a_card()` is the shape, and its reasoning holds here — commits
from before the rule are not its business.

Deliberately NOT a test that `core.hooksPath` is armed: a fresh clone has not
run the installer, and a suite that goes red on clone teaches a session to
ignore it. The bypass reader catches the same class one commit later, which is
the earliest moment the failure is real rather than potential.
"""

import subprocess

import pytest

from tests.ratchets.paths import REPO

DOCTRINE = ["docs/HOW-WE-WORK.md", "docs/INTENT.md"]
CARD = r"(#|\bcard )[0-9]+\b"
HOOK = "hooks/commit-msg"
RECORD = "\x1e"
FIELD = "\x1f"


def _git(repo, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""


def doctrine_edits_without_a_card(repo) -> list[str]:
    """Commits since the hook was born that edited the one text and name no card."""
    import re

    born = _git(repo, "log", "--diff-filter=A", "--format=%H", "--", HOOK).split()
    if not born:
        return []
    log = _git(
        repo,
        "log",
        f"{born[-1]}..HEAD",
        f"--format=%H{FIELD}%s{FIELD}%b{RECORD}",
        "--",
        *DOCTRINE,
    )
    bypassed = []
    for record in log.split(RECORD):
        if not record.strip():
            continue
        sha, subject, body = (record.strip("\n").split(FIELD) + ["", ""])[:3]
        if re.search(CARD, f"{subject}\n{body}", re.I):
            continue
        bypassed.append(f"{sha[:7]} {subject[:60]}")
    return bypassed


def test_no_doctrine_edit_bypassed_the_hook():
    bypassed = doctrine_edits_without_a_card(REPO)
    assert not bypassed, (
        "these commits edited the one text and no card knows about them: "
        + "; ".join(bypassed)
        + " — file the learning as a suggestion with **Fix:** his and name its card in a "
        "follow-up commit"
    )


@pytest.fixture
def fixture_repo(tmp_path):
    """A throwaway repository with the hook armed, so the rule is rehearsed on a
    fixture before it is trusted live (HOW-WE-WORK: rehearse destructive work on
    a fixture)."""
    repo = tmp_path / "corpus"
    (repo / "docs").mkdir(parents=True)
    (repo / "hooks").mkdir()
    (repo / "hooks" / "commit-msg").write_bytes((REPO / HOOK).read_bytes())
    (repo / "hooks" / "commit-msg").chmod(0o755)
    _git(repo.parent, "init", "-q", str(repo))
    for key, value in [
        ("user.email", "fixture@example.com"),
        ("user.name", "Fixture"),
        ("core.hooksPath", str(repo / "hooks")),
        ("commit.gpgsign", "false"),
    ]:
        _git(repo, "config", key, value)
    (repo / "docs" / "HOW-WE-WORK.md").write_text("the one text\n")
    (repo / "docs" / "INTENT.md").write_text("the fixed point\n")
    (repo / "docs" / "other.md").write_text("something else\n")
    return repo


def _commit(repo, message: str, *paths: str, bypass: bool = False) -> bool:
    subprocess.run(["git", "-C", str(repo), "add", *paths], check=True, capture_output=True)
    done = subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", *(["--no-verify"] if bypass else []), "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def test_the_hook_refuses_a_cardless_doctrine_commit(fixture_repo):
    assert not _commit(fixture_repo, "docs(doctrine): tidy a sentence", "docs/HOW-WE-WORK.md")
    assert not _commit(fixture_repo, "docs: move the fixed point", "docs/INTENT.md")


def test_the_hook_accepts_a_doctrine_commit_naming_a_card(fixture_repo):
    assert _commit(fixture_repo, "docs(doctrine): tidy a sentence (#54)", "docs/HOW-WE-WORK.md")
    (fixture_repo / "docs" / "INTENT.md").write_text("the fixed point, moved\n")
    assert _commit(fixture_repo, "docs: move the fixed point, on card 54", "docs/INTENT.md")


def test_the_hook_lets_every_other_commit_through(fixture_repo):
    assert _commit(fixture_repo, "docs: something else entirely", "docs/other.md")


def test_the_reader_names_a_bypassed_commit_and_only_that_one(fixture_repo):
    assert _commit(fixture_repo, "chore: the hook itself", "hooks/commit-msg")
    assert _commit(fixture_repo, "docs(doctrine): a ruled edit (#54)", "docs/HOW-WE-WORK.md")
    assert _commit(fixture_repo, "docs: unrelated", "docs/other.md")
    (fixture_repo / "docs" / "HOW-WE-WORK.md").write_text("the one text, tidied\n")
    assert _commit(fixture_repo, "docs: a tidying pass", "docs/HOW-WE-WORK.md", bypass=True)

    named = doctrine_edits_without_a_card(fixture_repo)
    assert len(named) == 1, named
    assert "a tidying pass" in named[0]


def test_the_reader_is_silent_before_the_hook_was_born(fixture_repo):
    """Commits from before the rule are not its business — otherwise adopting the
    hook would turn the whole history red and the finding would be ignored."""
    assert _commit(fixture_repo, "docs: an edit from before the rule", "docs/HOW-WE-WORK.md", bypass=True)
    assert doctrine_edits_without_a_card(fixture_repo) == []
