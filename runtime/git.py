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

from domain.release import Release
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


def add_worktree(repo: str | Path, path: str | Path, branch: str) -> str | None:
    """Lay a lane's worktree on a branch of its own, off the trunk. What
    `claude --bg --worktree` does for a Claude lane, done here for a make
    whose launcher has no such flag (card #63): the same place, the same
    branch name, so the board reads both lanes the same way. Answers None
    when it worked, else git's own words.

    The branch is started from `origin/develop` rather than from whatever
    the main checkout has checked out, which is what the effort gate's click
    means by "started from the card": a lane begins level with the trunk.
    """
    start = f"{REMOTE}/{TRUNK}" if head_of(repo, f"{REMOTE}/{TRUNK}") else "HEAD"
    try:
        _git(repo, "worktree", "add", "-b", branch, str(path), start)
    except GitFailed as error:
        return str(error)
    return None


def remove_worktree(repo: str | Path, path: str | Path, branch: str) -> str | None:
    """Take back a worktree whose lane never started, and the branch with
    it. Only ever called for a launch that died: git refuses to remove a
    worktree with work in it, and the caller has just proved there is none.
    Answers None when it worked, else git's own words."""
    try:
        _git(repo, "worktree", "remove", "--force", str(path))
    except GitFailed as error:
        return str(error)
    _try(repo, "branch", "-D", branch)
    return None


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


FIXES_AFTER_DAYS = 7


def fixes_after(repo: str | Path, tip: str, number: int) -> int:
    """How many commits landed on the trunk after the lane's tip, within a
    week of it, naming the card (`#N`) in their message: the rework a fold
    needed, read the way the card's history and the review record already
    name a card (card #58, item 2). A revert is counted by `reverted`, not
    here, and a message naming the number as part of a larger one is not
    a match."""
    when = _try(repo, "log", "-1", "--format=%ct", tip)
    if not when or not when.strip().isdigit():
        return 0
    until = int(when.strip()) + FIXES_AFTER_DAYS * 24 * 3600
    out = _try(
        repo,
        "log",
        f"--grep=(^|[^0-9])#{number}([^0-9]|$)",
        "--extended-regexp",
        f"--until={until}",
        "--format=%H",
        f"{tip}..{REMOTE}/{TRUNK}",
    )
    return len(out.split()) if out else 0


CORPUS_FOLDERS = ("docs/plans", "docs/slice-suggestions")
_RENAME_LINE = re.compile(r"^R\d*\t(.+?)\t(.+)$")
_STAGED_RENAME = re.compile(r"^R.\s+(.+?) -> (.+)$")


def corpus_renames(checkout: str | Path) -> dict[str, str]:
    """Every rename of a corpus document git knows, old path → new path
    (plan 08, item 1): the whole history with git's own rename detection,
    newest first so a path renamed twice maps to its latest name, plus a
    rename staged and not yet committed. The whole history and not a depth:
    `-n` bounds the commits shown, not the commits walked, so a depth bought
    nothing (measured 2026-09-07 on Hello Revenue's 4268 commits: 0.2 s at
    any depth, 615 renames). A file deleted and another created without git
    seeing a rename is not here — that is the body match's case, in
    `board/reconcile.py::same_body`."""
    moves: dict[str, str] = {}
    log = _try(
        checkout,
        "log",
        "-M",
        "--diff-filter=R",
        "--name-status",
        "--format=",
        "--",
        *CORPUS_FOLDERS,
    )
    for line in (log or "").splitlines():
        match = _RENAME_LINE.match(line)
        if match and match.group(1) not in moves:
            moves[match.group(1)] = match.group(2)
    porcelain = _try(checkout, "status", "--porcelain", "--untracked-files=no")
    for line in (porcelain or "").splitlines():
        match = _STAGED_RENAME.match(line)
        if match:
            moves[match.group(1)] = match.group(2)
    return moves


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
            level=False,
            behind=behind,
            note=f"could not fast-forward: {error}",
            fetched=True,
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


def release(
    checkout: str | Path, *, ahead: str | None = None, fetch_first: bool = False
) -> Release:
    """What promoting the stable branch from this checkout would carry: the
    files and the commit count of the range between `origin/main` and
    `ahead` — `origin/develop` by default, and the lane's own `HEAD` when a
    fold asks what its promotion would carry (card #139, item 1).

    It decides nothing; it answers. A range it could not read is `read`
    False with the reason, never an empty answer: "nothing to carry" and
    "nothing could be seen" are the two sides the refusal in the fold verb
    must tell apart, and a checkout with no stable branch is the second.
    The three-dot form is the merge base's, so the answer is what `ahead`
    adds and not what the stable branch has moved on without — the same
    shape `changed_files` reads a lane's own work with."""
    if fetch_first:
        why = fetch(checkout)
        if why is not None:
            return Release(files=[], commits=0, read=False, note=f"could not fetch: {why}")
    inside = _try(checkout, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.strip() != "true":
        # Said apart from the next answer on purpose: "this checkout cannot
        # be read at all" and "this project has no stable branch" are two
        # different facts, and a refusal that showed one wording for both
        # would send a reader looking for a branch in a directory that is
        # not there (the four-state run for item 1, 2026-09-13).
        return Release(
            files=[],
            commits=0,
            read=False,
            note=f"{checkout} is not a checkout this machine can read",
        )
    stable = f"{REMOTE}/{STABLE}"
    if head_of(checkout, stable) is None:
        return Release(
            files=[],
            commits=0,
            read=False,
            note=f"there is no {stable} here, so what a promotion would carry cannot be read",
        )
    tip = ahead or f"{REMOTE}/{TRUNK}"
    if head_of(checkout, tip) is None:
        return Release(files=[], commits=0, read=False, note=f"there is no {tip} here")
    diff = _try(checkout, "diff", "--name-only", f"{stable}...{tip}")
    if diff is None:
        return Release(files=[], commits=0, read=False, note=f"git could not read {stable}...{tip}")
    counted = _try(checkout, "rev-list", "--count", f"{stable}..{tip}")
    return Release(
        files=[line.strip() for line in diff.splitlines() if line.strip()],
        commits=int(counted.strip()) if counted and counted.strip().isdigit() else 0,
        read=True,
        note=None,
    )


class Folded(BaseModel):
    pushed: bool
    words: str
    tip: str | None
    main_pushed: bool | None
    """None when main was not asked for."""
    held: str | None = None
    """The standing hold file this fold wrote into the lane before pushing,
    so the closes queued behind a held release do not meet their own
    archive refusal (card #139, item 3); None when none was asked for or
    one already stood, and git's own words when it could not be written."""


HOLD_HEAD = "# The release is held"


def _inside(worktree: str | Path, hold: str) -> Path | None:
    """Where the hold file sits in the lane, or None when the path leaves it.

    The declaration is the owner's own words, but a path that climbs out of
    the project would have a fold write outside the repository it is
    folding — the one thing a fold must never do. Refused rather than
    trusted, because a boundary that matters is not a convention."""
    root = Path(worktree).resolve()
    place = (root / hold).resolve()
    return place if place != root and place.is_relative_to(root) else None


def _write_hold(worktree: str | Path, hold: str, why: str) -> tuple[str | None, str | None]:
    """Write the project's standing hold file into the lane and commit it,
    so the fold carries it to the shared branch and every close behind it
    reads it there. Answers (what was written, what went wrong).

    A file that already stands is left exactly as it is: the first held
    release wrote it, the owner's deletion is what lifts it, and a second
    lane rewriting it would erase the reason he is about to read.

    The commit skips the repository's own hooks. The hold is the machine's
    act at the moment a release is refused, not a session's change, and a
    project hook that asks every commit to name a card would stop the one
    commit that keeps every close behind this one finishing."""
    place = _inside(worktree, hold)
    if place is None:
        return None, f"{hold} is not a place inside this project"
    if place.exists():
        return None, None
    try:
        place.parent.mkdir(parents=True, exist_ok=True)
        place.write_text(f"{HOLD_HEAD}\n\n{why}\n", encoding="utf-8")
    except OSError as error:
        return None, str(error)
    try:
        _git(worktree, "add", "--", hold)
        _git(
            worktree,
            "commit",
            "--no-verify",
            "-m",
            f"chore(release): hold the release — {hold}",
            "-m",
            why,
        )
    except GitFailed as error:
        return None, str(error)
    return hold, None


def fold(
    worktree: str | Path, *, promote_main: bool, hold: str | None = None, why: str | None = None
) -> Folded:
    """Push the lane's HEAD to origin/develop by fast-forward, proved by
    origin/develop equalling HEAD after a fetch; with `promote_main`, push
    the same commit to origin/main afterwards.

    With `hold`, the project's standing hold file is written and committed
    into the lane first, so one push carries both the work and the hold
    that keeps the closes behind it archiving (card #139, item 3). The
    write is never combined with `promote_main`: a held release is one that
    is not promoting.

    The hold is written after the tree is proved clean and taken back if the
    push then fails, so a fold that did not land never leaves a hold commit
    sitting in the lane. That commit would otherwise ride the *next* fold —
    and if the owner promoted in between, the shared branch would carry a
    standing hold no release asked for, which makes a project's archive gate
    stand aside silently and for good."""
    written: str | None = None
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
            held=written,
        )
    was = head(worktree)
    if was is None:
        return Folded(
            pushed=False,
            words="no HEAD to push",
            tip=None,
            main_pushed=None,
            held=written,
        )
    if hold and why and not promote_main:
        written, refused = _write_hold(worktree, hold, why)
        if refused is not None:
            written = refused
    tip = head(worktree)
    try:
        _git(worktree, "push", REMOTE, f"HEAD:{TRUNK}", timeout=FETCH_SECONDS)
    except GitFailed as error:
        if written == hold and tip != was:
            # The tree was proved clean a moment ago and this commit is ours.
            _try(worktree, "reset", "--hard", was)
            written, tip = None, was
        return Folded(
            pushed=False,
            words=str(error),
            tip=tip,
            main_pushed=None,
            held=written,
        )
    unfetched = fetch(worktree)
    if unfetched is not None:
        return Folded(
            pushed=False,
            words=f"pushed, but could not fetch to prove it: {unfetched}",
            tip=tip,
            main_pushed=None,
            held=written,
        )
    landed = head_of(worktree, f"{REMOTE}/{TRUNK}")
    if landed != tip:
        return Folded(
            pushed=False,
            words=f"pushed, but {REMOTE}/{TRUNK} reads {landed} and HEAD is {tip}",
            tip=tip,
            main_pushed=None,
            held=written,
        )
    if not promote_main:
        return Folded(
            pushed=True,
            words=f"{REMOTE}/{TRUNK} is {tip[:10]}",
            tip=tip,
            main_pushed=None,
            held=written,
        )
    try:
        _git(worktree, "push", REMOTE, f"HEAD:{STABLE}", timeout=FETCH_SECONDS)
    except GitFailed as error:
        return Folded(
            pushed=True,
            words=f"{REMOTE}/{TRUNK} is {tip[:10]}; main not promoted: {error}",
            tip=tip,
            main_pushed=False,
            held=written,
        )
    return Folded(
        pushed=True,
        words=f"{REMOTE}/{TRUNK} and {REMOTE}/{STABLE} are {tip[:10]}",
        tip=tip,
        main_pushed=True,
        held=written,
    )
