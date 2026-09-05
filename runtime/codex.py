"""Codex's sessions as rows of the one list, and the argv that calls one
warm (plan 57).

Codex keeps no registry: each session is one rollout file,
`<codex home>/sessions/<y>/<m>/<d>/rollout-<stamp>-<id>.jsonl`, whose first
record (`session_meta`) says the session's id, the directory it ran in and
its source — `cli` for a terminal of the owner's, `exec` for a
non-interactive worker — and whose tail says what it did last (a
`custom_tool_call` or `function_call` record) and whether its turn is open
(`task_started` with no `task_complete` or `turn_aborted` after it). No
process id is written anywhere, so a row is live only when a `codex`
process in /proc names the rollout: an `exec resume` carries the id in its
argv, a terminal holds the file open (both verified on this machine,
2026-09-05).

This reader stays a file-format reader beside `runtime.transcripts`; the
two share the `Session` and `Doing` shapes and nothing else, because the
two formats repeat no boundary yet (the plan's item 3). What a Codex row
never claims: a subscription slot (`slot` is the make's name), a model the
`Model` rungs could hold, a wall, a fork. What it never surfaces: the brief
it was given or the input of a tool call — a code-mode `exec` carries a
whole script, so `doing` is the tool's name and its time, nothing more.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from domain.session import Doing, Session, SessionKind, SessionState
from runtime import machine

SLOT = "codex"
"""The make's name, where a Claude row carries its subscription slot: the
one list sorts by it, the caller names a colleague by it, and every verb
that acts on a slot's registry reads it to refuse."""

RECENT_SECONDS = 24 * 3600
"""A rollout changed within this is a row of the one list; an older one is
reached by id (`find`) but not listed, since Codex never removes a rollout
and a list of every session ever run is not the one list."""

TAIL_BYTES = 64 * 1024
"""As `runtime.transcripts.TAIL_BYTES`: a tool-call record is a few hundred
bytes and a turn's last events sit at the end."""

WORKER_SOURCES = {"exec"}
"""`session_meta.source` for a non-interactive worker, the only kind a call
resumes. `cli` is a terminal of the owner's; a source this version has not
seen is neither, and is surfaced by its own word and never resumed as a
worker (Sol's correction in the first warm exchange, 2026-09-05: a positive
allowlist, not a default to worker)."""
TERMINAL_SOURCE = "cli"

TURN_ENDED = {"task_complete", "turn_aborted"}
TOOL_CALLS = {"custom_tool_call", "function_call", "local_shell_call", "web_search_call"}

_UUID = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
_ROLLOUT = re.compile(r"rollout-.*-" + _UUID + r"\.jsonl$")
_RESUMED = re.compile(r"\bresume\b.*?" + _UUID)
"""The id after `resume` in a worker's argv, past any flag between them;
the first id after the word, since a brief may name others."""
SHORT_LENGTH = 8


@dataclass
class Rollout:
    path: Path
    session_id: str
    cwd: str
    source: str
    """The rollout's own word for what kind of session it was: `cli`, `exec`."""
    started_at: datetime | None
    updated_at: datetime
    """The file's last change: the last thing the session wrote."""


def is_worker(rollout: Rollout) -> bool:
    return rollout.source in WORKER_SOURCES


@dataclass
class Tail:
    mid_turn: bool
    doing: Doing | None


def rollouts() -> list[Rollout]:
    """Every rollout whose head can be read, oldest change first. A file
    that is malformed, or gone between the listing and the read, is
    skipped: one bad rollout never hides the others."""
    root = machine.codex_sessions_root()
    try:
        paths = sorted(root.rglob("rollout-*.jsonl"))
    except OSError:
        return []
    found: list[Rollout] = []
    for path in paths:
        rollout = _rollout_of(path)
        if rollout is not None:
            found.append(rollout)
    return sorted(found, key=lambda r: r.updated_at)


def _rollout_of(path: Path) -> Rollout | None:
    try:
        stamp = path.stat().st_mtime
        with path.open(encoding="utf-8", errors="replace") as f:
            first = f.readline()
        meta = json.loads(first)
    except (OSError, ValueError):
        return None
    payload = meta.get("payload") if isinstance(meta, dict) else None
    if not isinstance(payload, dict) or meta.get("type") != "session_meta":
        return None
    session_id = payload.get("session_id") or payload.get("id")
    if not isinstance(session_id, str) or not session_id:
        return None
    cwd = payload.get("cwd")
    return Rollout(
        path=path,
        session_id=session_id,
        cwd=cwd if isinstance(cwd, str) else "",
        source=str(payload.get("source") or ""),
        started_at=_when(payload.get("timestamp")) or _when(meta.get("timestamp")),
        updated_at=datetime.fromtimestamp(stamp, UTC),
    )


def _when(stamp: object) -> datetime | None:
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def tail_of(path: Path) -> Tail:
    """What the rollout's end says: whether a turn is open, and the last
    tool call by name and time."""
    try:
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - TAIL_BYTES))
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return Tail(mid_turn=False, doing=None)
    mid_turn = False
    doing: Doing | None = None
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        kind = payload.get("type") if isinstance(payload, dict) else None
        if not isinstance(kind, str):
            continue
        if record.get("type") == "event_msg":
            if kind == "task_started":
                mid_turn = True
            elif kind in TURN_ENDED:
                mid_turn = False
        elif record.get("type") == "response_item" and kind in TOOL_CALLS:
            at = _when(record.get("timestamp"))
            name = payload.get("name") if isinstance(payload, dict) else None
            if at is not None:
                doing = Doing(step=str(name or kind), at=at)
    return Tail(mid_turn=mid_turn, doing=doing)


# ── processes ──────────────────────────────────────────────────────────


def processes() -> dict[str, int]:
    """Session id → the pid of the `codex` process that names its rollout:
    the id after `resume` in an `exec resume` worker's argv, or the
    rollout a terminal holds open."""
    live: dict[str, int] = {}
    for pid in machine.pids():
        line = machine.cmdline_of(pid)
        if not line or "codex" not in line:
            continue
        resumed = _RESUMED.search(line)
        if resumed:
            live.setdefault(resumed.group(1), pid)
            continue
        for path in machine.open_files_of(pid):
            named = _ROLLOUT.search(path)
            if named:
                live.setdefault(named.group(1), pid)
    return live


# ── the rows ───────────────────────────────────────────────────────────


def row_of(rollout: Rollout, pid: int | None) -> Session:
    """One rollout as a row of the one list. A worker with a process is
    working (an `exec` process lives only for its turn); a terminal with a
    process is working while its turn is open and idle otherwise; no
    process is ended, whatever the file says. `recorded` carries the
    rollout's own source word, so a session of a source this reader does
    not know is shown as what it is."""
    tail = tail_of(rollout.path) if pid is not None else None
    worker = is_worker(rollout)
    if pid is None:
        state = SessionState.ENDED
    elif worker or (tail is not None and tail.mid_turn):
        state = SessionState.WORKING
    else:
        state = SessionState.IDLE
    short = rollout.session_id[:SHORT_LENGTH]
    return Session(
        slot=SLOT,
        config_dir=str(machine.codex_home()),
        short_id=short,
        session_id=rollout.session_id,
        kind=SessionKind.BACKGROUND if worker else SessionKind.INTERACTIVE,
        name=f"{SLOT}-{short}",
        cwd=rollout.cwd,
        worktree=None,
        state=state,
        recorded=rollout.source,
        detail="",
        pid=pid,
        scope=machine.cgroup_of(pid) if pid is not None else None,
        model=None,
        effort=None,
        stale=False,
        wall=None,
        intent="",
        created_at=rollout.started_at,
        updated_at=rollout.updated_at,
        resumed_from=None,
        doing=tail.doing if tail is not None else None,
    )


def sessions(now: datetime) -> list[Session]:
    """Every recent rollout, and every older one with a process, as rows."""
    live = processes()
    rows: list[Session] = []
    for rollout in rollouts():
        pid = live.get(rollout.session_id)
        if pid is None and (now - rollout.updated_at).total_seconds() > RECENT_SECONDS:
            continue
        rows.append(row_of(rollout, pid))
    return rows


def find(ref: str) -> list[Session]:
    """Every rollout the ref names, by full id or a prefix of at least the
    short id's length; more than one is the caller's to refuse."""
    if len(ref) < SHORT_LENGTH:
        return []
    matches = [r for r in rollouts() if r.session_id == ref or r.session_id.startswith(ref)]
    if not matches:
        return []
    live = processes()
    return [row_of(r, live.get(r.session_id)) for r in matches]


def warm() -> Session | None:
    """The worker the bare name names: the most recently changed rollout of
    a non-interactive session, or None when Codex has run none here."""
    workers = [r for r in rollouts() if is_worker(r)]
    if not workers:
        return None
    newest = workers[-1]
    return row_of(newest, processes().get(newest.session_id))


# ── the call ───────────────────────────────────────────────────────────


def resume_argv(session_id: str, *, brief: str, answer: str) -> list[str]:
    """`codex exec -o <answer> resume <id> <brief>`: the worker's last
    message is written to `answer` by Codex itself, outside the sandbox
    its shell commands run in, so the answer lands whatever the sandbox
    allows (the plan's evidence: a worker's own write to the shared record
    was refused on 2026-09-05, and `-o` before `resume` was verified the
    same day with a one-word reply). The sandbox is never widened here.
    `--skip-git-repo-check` lets a worker whose directory is no repository
    (a scratch probe) be resumed rather than refused for that alone."""
    return [
        machine.which("codex"),
        "exec",
        "-o",
        answer,
        "resume",
        "--skip-git-repo-check",
        session_id,
        brief,
    ]


def log_path(answer: str) -> Path:
    """Where a called worker's stdout and stderr go: beside the answer,
    named for it, so a death has its words and the board's note reader
    (which lists `.md` only) never mistakes it for a note."""
    given = Path(answer)
    return given.with_name(given.stem + ".log")
