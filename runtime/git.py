"""What git knows about a project and its lanes, read through the machine door.

The fold reaches origin and the checkout follows (plan 03, item 6): a lane
folds by a fast-forward push to `origin/develop` from its own worktree, and
the runtime keeps every registered project's main checkout level with it,
refusing — and saying so — when that checkout holds uncommitted work. Fold
evidence for a lane is read the way 0.1 learned to read it: the branch's tip
is an ancestor of the trunk and has moved from its birth, never bare
ancestry (a zero-commit branch is an ancestor from birth).
"""

import re
from pathlib import Path

from pydantic import BaseModel

from runtime import machine

TRUNK = "develop"
STABLE = "main"
REMOTE = "origin"
GIT_SECONDS = 30.0
FETCH_SECONDS = 90.0

_LANE_BRANCH = re.compile(r"card-(\d+)-")


class GitFailed(Exception):
    """git could not run or refused; the message is its own words."""


def _git(cwd: str | Path, *args: str, timeout: float = GIT_SECONDS) -> str:
    try:
        done = machine.run([machine.which("git"), *args], cwd=cwd, timeout=timeout)
    except (OSError, machine.Timeout, machine.CommandMissing) as error:
        raise GitFailed(f"git {' '.join(args)}: {error}") from error
    if done.returncode != 0:
        said = (done.stderr or done.stdout).strip().splitlines()
        raise GitFailed(f"git {' '.join(args[:2])}: {said[-1] if said else 'failed'}")
    return done.stdout


def _try(cwd: str | Path, *args: str, timeout: float = GIT_SECONDS) -> str | None:
    try:
        return _git(cwd, *args, timeout=timeout)
    except GitFailed:
        return None


# ── worktrees and lanes ────────────────────────────────────────────────


def worktrees(repo: str | Path) -> dict[str, str | None]:
    """Every checkout of the repository, path → branch (None when detached)."""
    out = _try(repo, "worktree", "list", "--porcelain")
    if out is None:
        return {}
    found: dict[str, str | None] = {}
    path = ""
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree ") :]
            found[path] = None
        elif path and line.startswith("branch "):
            found[path] = line[len("branch ") :].removeprefix("refs/heads/")
    return found


def card_of_branch(branch: str | None) -> int | None:
    match = _LANE_BRANCH.search(branch or "")
    return int(match.group(1)) if match else None


def head(checkout: str | Path) -> str | None:
    out = _try(checkout, "rev-parse", "HEAD")
    return out.strip() if out else None


def current_branch(checkout: str | Path) -> str | None:
    out = _try(checkout, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if out else None


def changed_files(checkout: str | Path, *, against: str = f"{REMOTE}/{TRUNK}") -> set[str]:
    """What a checkout is editing: committed ahead of the trunk, plus uncommitted."""
    files: set[str] = set()
    diff = _try(checkout, "diff", "--name-only", f"{against}...HEAD")
    if diff:
        files |= {line.strip() for line in diff.splitlines() if line.strip()}
    porcelain = _try(checkout, "status", "--porcelain")
    if porcelain:
        files |= {line[3:].strip() for line in porcelain.splitlines() if line.strip()}
    return files


def lane_files(checkout: str | Path, *, birth: str | None, tip: str | None) -> set[str]:
    """Every file a lane changed from the commit it was born at to its tip,
    plus what the checkout holds uncommitted (plan 11, item 1). After a fold
    the diff against the trunk is empty — the lane's HEAD is the trunk — so
    the lane's own birth is the base; with no birth known, the trunk is,
    which is what the collision read uses while the lane runs."""
    files: set[str] = set()
    head_ref = tip or "HEAD"
    if birth:
        diff = _try(checkout, "diff", "--name-only", f"{birth}..{head_ref}")
    else:
        diff = _try(checkout, "diff", "--name-only", f"{REMOTE}/{TRUNK}...{head_ref}")
    if diff:
        files |= {line.strip() for line in diff.splitlines() if line.strip()}
    porcelain = _try(checkout, "status", "--porcelain")
    if porcelain:
        files |= {line[3:].strip() for line in porcelain.splitlines() if line.strip()}
    return files


def reverted(repo: str | Path, tip: str) -> bool:
    """Whether a commit on the trunk reverts the lane's tip: git's own revert
    message names the commit it undoes ("This reverts commit <sha>"), and the
    trunk is searched for that sentence with the tip's full or short sha."""
    trunk = f"{REMOTE}/{TRUNK}"
    out = _try(repo, "log", f"--grep=This reverts commit {tip[:10]}", "--format=%H", trunk)
    return bool(out and out.strip())


def tracked_changes(checkout: str | Path) -> list[str]:
    """Uncommitted changes to tracked files; untracked files are not work in progress."""
    porcelain = _try(checkout, "status", "--porcelain", "--untracked-files=no")
    return [line.strip() for line in (porcelain or "").splitlines() if line.strip()]


def is_ancestor(repo: str | Path, sha: str, ref: str) -> bool | None:
    try:
        done = machine.run(
            [machine.which("git"), "merge-base", "--is-ancestor", sha, ref],
            cwd=repo,
            timeout=GIT_SECONDS,
        )
    except (OSError, machine.Timeout, machine.CommandMissing):
        return None
    if done.returncode == 0:
        return True
    if done.returncode == 1:
        return False
    return None


def branch_birth(repo: str | Path, branch: str) -> str | None:
    """The commit the branch was created at: its oldest reflog entry."""
    out = _try(repo, "reflog", "show", "--format=%H", branch)
    lines = [ln for ln in (out or "").splitlines() if ln.strip()]
    return lines[-1] if lines else None


def lane_folded(
    repo: str | Path, branch: str | None, tip: str | None, birth: str | None = None
) -> bool | None:
    """Is the lane's work in the trunk? True on positive evidence: the tip is
    an ancestor of origin/develop AND has moved from the commit the lane was
    born at (a zero-commit branch is an ancestor from birth). False when the
    tip is not in the trunk. None when nothing can be proved: no tip, no
    copy of the trunk here, or no birth known for a branch whose reflog is
    gone."""
    trunk = f"{REMOTE}/{TRUNK}"
    if head_of(repo, trunk) is None:
        return None
    if branch and tip is None:
        out = _try(repo, "rev-parse", branch)
        tip = out.strip() if out else None
    if tip is None:
        return None
    contained = is_ancestor(repo, tip, trunk)
    if not contained:
        return False if contained is False else None
    if branch and birth is None:
        birth = branch_birth(repo, branch)
    if birth is None:
        return None
    return tip != birth


def head_of(repo: str | Path, ref: str) -> str | None:
    out = _try(repo, "rev-parse", "--verify", "--quiet", ref)
    return out.strip() if out else None


def arm_hooks_path(repo: str | Path, hooks: Path) -> str:
    """Point the repository's git at `hooks`, and say what it pointed at before.

    Absolute, always: the setting lives in the shared config that every
    worktree of the repository reads, and a relative value resolves against
    each worktree's own root — so a lane under `.claude/worktrees/` would
    silently run no hook, which is exactly where the commits are made (plan 18,
    item 5; the machine repo learned the same thing on its own hook).
    """
    if not hooks.is_absolute():
        raise GitFailed(f"{hooks} is relative; a lane's worktree would not find it")
    was = (_try(repo, "config", "--get", "core.hooksPath") or "").strip()
    if was != str(hooks):
        _git(repo, "config", "core.hooksPath", str(hooks))
    return was


# ── the trunk ──────────────────────────────────────────────────────────


class Levelled(BaseModel):
    """What a sync of the main checkout found and did."""

    level: bool | None
    behind: int
    note: str | None
    fetched: bool
    main_updated: bool


def fetch(repo: str | Path) -> str | None:
    """Fetch the trunk and the stable branch; None on success, else why not."""
    try:
        _git(repo, "fetch", "--quiet", REMOTE, TRUNK, STABLE, timeout=FETCH_SECONDS)
    except GitFailed as error:
        try:
            _git(repo, "fetch", "--quiet", REMOTE, TRUNK, timeout=FETCH_SECONDS)
        except GitFailed:
            return str(error)
    return None


def behind_count(repo: str | Path) -> int:
    out = _try(repo, "rev-list", "--count", f"HEAD..{REMOTE}/{TRUNK}")
    return int(out.strip()) if out and out.strip().isdigit() else 0


def level(repo: str | Path) -> Levelled:
    """Bring the main checkout level with origin/develop by fast-forward,
    refusing a checkout with uncommitted tracked work or one not on develop.
    The local stable branch follows origin/main when it is not checked out."""
    why = fetch(repo)
    if why is not None:
        return Levelled(
            level=None, behind=0, note=f"could not fetch: {why}", fetched=False, main_updated=False
        )
    main_updated = (
        _try(repo, "fetch", "--quiet", REMOTE, f"{STABLE}:{STABLE}", timeout=FETCH_SECONDS)
        is not None
    )
    behind = behind_count(repo)
    branch = current_branch(repo)
    if branch != TRUNK:
        return Levelled(
            level=behind == 0,
            behind=behind,
            note=f"the checkout is on {branch or 'a detached HEAD'}, not {TRUNK}; not touched",
            fetched=True,
            main_updated=main_updated,
        )
    dirty = tracked_changes(repo)
    if dirty:
        shown = ", ".join(line.split()[-1] for line in dirty[:3]) + ("…" if len(dirty) > 3 else "")
        return Levelled(
            level=behind == 0,
            behind=behind,
            note=(
                None
                if behind == 0
                else (
                    f"the checkout has uncommitted work that is not the runtime's ({shown}); "
                    "not touched"
                )
            ),
            fetched=True,
            main_updated=main_updated,
        )
    if behind == 0:
        return Levelled(level=True, behind=0, note=None, fetched=True, main_updated=main_updated)
    try:
        _git(repo, "merge", "--ff-only", f"{REMOTE}/{TRUNK}")
    except GitFailed as error:
        return _rebase_ahead(repo, behind, main_updated, error)
    return Levelled(level=True, behind=0, note=None, fetched=True, main_updated=main_updated)


def ahead_count(repo: str | Path) -> int:
    out = _try(repo, "rev-list", "--count", f"{REMOTE}/{TRUNK}..HEAD")
    return int(out.strip()) if out and out.strip().isdigit() else 0


def _rebase_ahead(repo: str | Path, behind: int, main_updated: bool, error: GitFailed) -> Levelled:
    """A trunk that is ahead of origin cannot fast-forward: a main-thread
    session committed in the main checkout and never pushed while a lane
    folded. Until 2026-09-05 this stopped every fold and every close that
    reads the corpus until a human ran `git pull --rebase` (omarchy, twice).
    The machine repo's post-commit hook pushes at commit time; this is the
    recovery when it could not. A clean rebase is pushed and the trunk is
    level; a conflict is aborted and named, the commits left in place."""
    ahead = ahead_count(repo)
    if ahead == 0:
        return Levelled(
            level=False, behind=behind, note=f"could not fast-forward: {error}", fetched=True,
            main_updated=main_updated,
        )
    try:
        _git(repo, "rebase", "--quiet", "--autostash", f"{REMOTE}/{TRUNK}")
    except GitFailed as conflict:
        _try(repo, "rebase", "--abort")
        return Levelled(
            level=False,
            behind=behind,
            note=(
                f"the checkout is {ahead} commit(s) ahead of {REMOTE}/{TRUNK} and the rebase "
                f"conflicts ({conflict}); left as it was — resolve with git pull --rebase there"
            ),
            fetched=True,
            main_updated=main_updated,
        )
    try:
        _git(repo, "push", "--quiet", REMOTE, TRUNK, timeout=FETCH_SECONDS)
    except GitFailed as refused:
        return Levelled(
            level=False,
            behind=0,
            note=(
                f"rebased {ahead} local commit(s) onto {REMOTE}/{TRUNK} but the push was refused "
                f"({refused}); the checkout is level, {REMOTE} is not"
            ),
            fetched=True,
            main_updated=main_updated,
        )
    return Levelled(
        level=True,
        behind=0,
        note=f"rebased and pushed {ahead} local commit(s) that were ahead of {REMOTE}/{TRUNK}",
        fetched=True,
        main_updated=main_updated,
    )


# ── the fold ───────────────────────────────────────────────────────────


class Folded(BaseModel):
    pushed: bool
    words: str
    tip: str | None
    main_pushed: bool | None
    """None when main was not asked for."""


def fold(worktree: str | Path, *, promote_main: bool) -> Folded:
    """Push the lane's HEAD to origin/develop by fast-forward, proved by
    origin/develop equalling HEAD after a fetch; with `promote_main`, push
    the same commit to origin/main afterwards."""
    dirty = tracked_changes(worktree)
    if dirty:
        return Folded(
            pushed=False,
            words=(
                "the worktree has uncommitted work: "
                + ", ".join(line.split()[-1] for line in dirty[:3])
            ),
            tip=head(worktree),
            main_pushed=None,
        )
    tip = head(worktree)
    if tip is None:
        return Folded(pushed=False, words="no HEAD to push", tip=None, main_pushed=None)
    try:
        _git(worktree, "push", REMOTE, f"HEAD:{TRUNK}", timeout=FETCH_SECONDS)
    except GitFailed as error:
        return Folded(pushed=False, words=str(error), tip=tip, main_pushed=None)
    why = fetch(worktree)
    if why is not None:
        return Folded(
            pushed=False,
            words=f"pushed, but could not fetch to prove it: {why}",
            tip=tip,
            main_pushed=None,
        )
    landed = head_of(worktree, f"{REMOTE}/{TRUNK}")
    if landed != tip:
        return Folded(
            pushed=False,
            words=f"pushed, but {REMOTE}/{TRUNK} reads {landed} and HEAD is {tip}",
            tip=tip,
            main_pushed=None,
        )
    if not promote_main:
        return Folded(
            pushed=True, words=f"{REMOTE}/{TRUNK} is {tip[:10]}", tip=tip, main_pushed=None
        )
    try:
        _git(worktree, "push", REMOTE, f"HEAD:{STABLE}", timeout=FETCH_SECONDS)
    except GitFailed as error:
        return Folded(
            pushed=True,
            words=f"{REMOTE}/{TRUNK} is {tip[:10]}; main not promoted: {error}",
            tip=tip,
            main_pushed=False,
        )
    return Folded(
        pushed=True,
        words=f"{REMOTE}/{TRUNK} and {REMOTE}/{STABLE} are {tip[:10]}",
        tip=tip,
        main_pushed=True,
    )
