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
never claims: a subscription slot (`slot` is the make's name), a wall, a
fork. What it never surfaces: the brief it was given or the input of a tool
call — a code-mode `exec` carries a whole script, so `doing` is the tool's
name and its time, nothing more.

Since card #63 this module also builds the argv that gives a Codex worker a
card's lane, beside the one that calls a worker warm.
"""

import json
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from domain.gate import Gate
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
    model: str | None
    """The model the rollout says answered it, from the session's own head;
    None when this version writes it somewhere else. The board shows it or
    shows the make alone, and never a guess (card #63, item 3)."""
    started_at: datetime | None
    updated_at: datetime
    """The file's last change: the last thing the session wrote."""
    effort: str | None = None
    """The reasoning effort the session's latest turn ran at, from the last
    `turn_context` record in the rollout (`effort`, read from a 0.153.4
    rollout on 2026-09-10); None when no turn carries a context, or the
    latest one names no effort whatever earlier turns named — which the
    caller is told rather than guessed (card #110, item 5)."""
    sandbox: str | None = None
    """The sandbox the same turn ran in (`sandbox_policy.type`: `read-only`,
    `workspace-write`, …); None on the same terms."""


CONTEXT_SCAN_BYTES = 4 * 1024 * 1024
"""How far back from a rollout's end its latest `turn_context` is looked
for. A turn's context opens the turn and the turn's records follow it, so
the last one sits within the last turn — near the end for a short turn,
megabytes back for a long one (the farthest first context measured on
2026-09-10 sat 3.1 MB into a forked thread); a rollout whose first turn
has not begun has none. Every read scans afresh: a cache was tried twice
and broken twice by the cold readers of rounds one and two of card #110
(a line still being written stepped past for good; a rollout rewritten in
place answering from before; a resumed scan skipping a context written
before its offset; identical bytes at one place not proving the record's
place), so the representation changed — the scan is the answer, and its
cost over every rollout of the last day is measured in that card's review
record."""


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
    effort, sandbox = _context_of(path)
    return Rollout(
        path=path,
        session_id=session_id,
        cwd=cwd if isinstance(cwd, str) else "",
        source=str(payload.get("source") or ""),
        model=_model_of(payload),
        started_at=_when(payload.get("timestamp")) or _when(meta.get("timestamp")),
        updated_at=datetime.fromtimestamp(stamp, UTC),
        effort=effort,
        sandbox=sandbox,
    )


def _context_of(path: Path) -> tuple[str | None, str | None]:
    """The effort and the sandbox of the rollout's latest turn, from the
    last complete `turn_context` record in the file; (None, None) when
    there is none or the file cannot be read. The last, not the first: a
    worker's first turn may carry no context and a fork inherits its
    parent's before its own turn begins (the cold read of round three,
    call 71, on two real rollouts), and what a caller is told is what the
    session's latest turn ran at — history, never a prediction of the
    next turn, which Codex resolves when the resume runs (the cold read of
    round five). Read backwards in growing blocks from the end, so
    a session whose last turn is short costs one small read and one whose
    last turn is long costs the turn; a line without a newline at the end
    is a line in flight and is not read."""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            end = size
            block = 64 * 1024
            carry = b""
            tail = True
            while end > 0 and size - end < CONTEXT_SCAN_BYTES:
                # Never past the cap: the budget bounds every block, so a
                # record larger than it is never read at all (round four).
                start = max(0, end - min(block, CONTEXT_SCAN_BYTES - (size - end)))
                f.seek(start)
                data = f.read(end - start) + carry
                lines = data.split(b"\n")
                if tail:
                    # The bytes after the file's last newline: nothing, or a
                    # line in flight — which may span several blocks (round
                    # four), so the tail is dropped until a newline is met.
                    lines.pop()
                    tail = not lines
                whole = lines if start == 0 else lines[1:]
                for raw in reversed(whole):
                    if b'"turn_context"' not in raw:
                        continue
                    found = _turn_context(raw)
                    if found is not None:
                        return found
                carry = b"" if start == 0 or not lines else lines[0]
                end = start
                block *= 2
    except OSError:
        return None, None
    return None, None


def _turn_context(raw: bytes) -> tuple[str | None, str | None] | None:
    """The two words of one `turn_context` line; None when the line is
    not one."""
    try:
        record = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    if not isinstance(record, dict) or record.get("type") != "turn_context":
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None, None
    named = payload.get("effort")
    policy = payload.get("sandbox_policy")
    kind = policy.get("type") if isinstance(policy, dict) else None
    return (
        named if isinstance(named, str) and named else None,
        kind if isinstance(kind, str) and kind else None,
    )


def last_error(log: Path) -> str | None:
    """The last tool error a worker's log holds — `ERROR codex_core::…:
    error=<words>`, the line Codex writes when a tool call fails inside a
    turn — so a turn that ended on one is reported as that error and not
    as a colleague that finished without its note (card #110, item 5; the
    carried defect's evidence: `collab spawn failed: no thread with id …`
    as a call's last line, 2026-09-07). None when the log has none or
    cannot be read."""
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    found: str | None = None
    for line in text.splitlines():
        match = _TOOL_ERROR.search(line)
        if match:
            found = match.group(1).strip()
    return found


_TOOL_ERROR = re.compile(r"\bERROR\b.*?\berror=(.+)$")


def _model_of(payload: dict) -> str | None:
    """The model named in a rollout's head. Codex records it as the
    provenance of the base instructions it was given
    (`base_instructions.provenance.model`, read from a 0.153.4 rollout on
    2026-09-08); a version that records it elsewhere answers None here and
    the board says the make alone, which is the truth and not a guess."""
    instructions = payload.get("base_instructions")
    provenance = instructions.get("provenance") if isinstance(instructions, dict) else None
    named = provenance.get("model") if isinstance(provenance, dict) else None
    return named if isinstance(named, str) and named else None


def _gate_of(effort: str | None) -> Gate | None:
    """Codex's effort word as the board's gate when it is one of the four;
    a word outside them (`none`, `minimal`) is no gate, and the row says
    so by carrying none."""
    try:
        return Gate(effort) if effort else None
    except ValueError:
        return None


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
        model=rollout.model,
        effort=_gate_of(rollout.effort),
        sandbox=rollout.sandbox,
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


def resume_argv(session_id: str, *, brief: str, answer: str, schema: str) -> list[str]:
    """`codex exec -o <answer> --output-schema <schema> resume <id> <brief>`:
    the worker's last message is written to `answer` by Codex itself,
    outside the sandbox its shell commands run in, so the answer lands
    whatever the sandbox allows (the plan's evidence: a worker's own write
    to the shared record was refused on 2026-09-05, and `-o` before
    `resume` was verified the same day with a one-word reply). The sandbox
    is never widened here. `--output-schema` holds the last message to the
    one answer shape (`domain.call.Answer`, card #73), so the board reads
    the words from a field and not from a first line guessed out of prose;
    `codex exec resume` takes the flag (its help, read 2026-09-07).
    `--skip-git-repo-check` lets a worker whose directory is no repository
    (a scratch probe) be resumed rather than refused for that alone."""
    return [
        machine.which("codex"),
        "exec",
        "-o",
        answer,
        "--output-schema",
        schema,
        "resume",
        "--skip-git-repo-check",
        session_id,
        brief,
    ]


def ask_argv(cwd: str, *, brief: str, answer: str, schema: str, effort: Gate) -> list[str]:
    """`codex exec -s read-only -C <cwd> -c model_reasoning_effort=<effort>
    --skip-git-repo-check -o <answer> --output-schema <schema> <brief>`: a
    fresh thread for a cold reading (card #87), never `resume`. Read-only
    because a reading judges and writes nothing but its last message,
    which Codex writes outside the sandbox; the project's checkout as the
    working directory so the reading can open the files the documents
    cite."""
    return [
        machine.which("codex"),
        "exec",
        "-s",
        "read-only",
        "-C",
        cwd,
        "-c",
        f"model_reasoning_effort={REASONING[effort]}",
        "--skip-git-repo-check",
        "-o",
        answer,
        "--output-schema",
        schema,
        brief,
    ]


def fresh_since(cwd: str, since: float) -> Session | None:
    """The worker rollout a fresh `codex exec` in `cwd` wrote after
    `since`, newest first, as a row: how an ask that answered before the
    observation window closed is still followed to its session."""
    stamp = datetime.fromtimestamp(since, UTC)
    candidates = [
        r
        for r in rollouts()
        if is_worker(r)
        and (r.started_at or r.updated_at) >= stamp - timedelta(seconds=2)
        and Path(r.cwd).resolve() == Path(cwd).resolve()
    ]
    if not candidates:
        return None
    newest = candidates[-1]
    return row_of(newest, processes().get(newest.session_id))


def schema_path(answer: str) -> Path:
    """Where the answer's schema is written before the call: beside the
    answer, named for it, so a reader of the record can see what the worker
    was held to, and never `.md`, so the board's note reader skips it."""
    given = Path(answer)
    return given.with_name(given.stem + ".schema.json")


# ── the lane ───────────────────────────────────────────────────────────

REASONING = {Gate.LOW: "low", Gate.MEDIUM: "medium", Gate.HIGH: "high", Gate.XHIGH: "xhigh"}
"""A plan's effort gate as Codex's own word for it. The four levels carry
the same names on both makes (`codex exec --help`, `model_reasoning_effort`,
read on 0.153.4 2026-09-08), so this map is an identity today and exists so
that the day one make renames a level the other is not renamed with it."""

GIT_ROOTS = ("objects", "refs", "logs")
"""The shared directories under a repository's `.git` that a commit on a
linked worktree's branch writes: the object store, the branch's ref and the
reflog. With the worktree's own `worktrees/<lane>` record they are the four
git paths a lane needs open, and no more. Codex's workspace sandbox denies
every write under `.git` by rule — proved on 2026-09-08 in a plain
repository, where a commit failed on `.git/index.lock` with the whole
repository as the workspace root — so naming these is what lets a lane
commit at all. What they leave closed is the main checkout's own index and
working tree, both verified refused in the same probe: the boundary a Claude
lane holds by its harness's guard, a Codex lane holds in the kernel."""


def lane_roots(repo: Path, lane: str, cache: Path) -> list[str]:
    """Everything outside its own worktree a Codex lane may write: the four
    git paths a commit on its branch needs (`GIT_ROOTS`), and the package
    cache its suite needs — five in all, and nothing else. Directories only:
    a file named here makes the sandbox exit 101 with a panic before the
    session starts (`.git/config`, 2026-09-08)."""
    git = repo / ".git"
    return [str(git / "worktrees" / lane), *[str(git / part) for part in GIT_ROOTS], str(cache)]


def lane_argv(
    worktree: Path,
    *,
    model: str | None,
    effort: Gate | None,
    prompt: str,
    roots: list[str],
) -> list[str]:
    """`codex exec` as a card's lane: working in the worktree, sandboxed to
    it, allowed the roots a commit and a suite need, and told the brief a
    Claude lane is told.

    Why `workspace-write` and not the launcher's bypass: Omarchy runs the
    owner's own Codex sessions with no sandbox at all, which is his call for
    a session he is watching; a lane nobody watches gets the sandbox,
    because the boundary "a lane never touches the main checkout" is then
    held by the kernel rather than by a rule the session could reason its
    way past (§5). Network access is on because the lane folds through the
    same door a Claude lane does — it runs the suite and `needle fold`
    itself — and a fold reaches origin and the board (all four verified
    inside the sandbox, 2026-09-08). No `-o` and no `--output-schema`: a
    lane's word is its commits and the card, not a last message.
    """
    # `-c` values are parsed as TOML, and JSON's array-of-strings escaping is
    # TOML's, so a path carrying a quote or a backslash cannot end the array
    # early and be read as something else.
    roots_toml = json.dumps(roots)
    argv = [machine.which("codex"), "exec", "-s", "workspace-write", "-C", str(worktree)]
    if model:
        argv += ["-m", model]
    if effort is not None:
        argv += ["-c", f"model_reasoning_effort={REASONING[effort]}"]
    argv += [
        "-c",
        f"sandbox_workspace_write.writable_roots={roots_toml}",
        "-c",
        "sandbox_workspace_write.network_access=true",
        prompt,
    ]
    return argv


def log_path(answer: str) -> Path:
    """Where a called worker's stdout and stderr go: beside the answer,
    named for it, so a death has its words and the board's note reader
    (which lists `.md` only) never mistakes it for a note."""
    given = Path(answer)
    return given.with_name(given.stem + ".log")


def configured_model() -> str | None:
    """The model Codex's own configuration names for a new session (the
    top-level `model` of `config.toml`), which is what a fresh worker
    called from a lane runs: what the team's stale test compares a
    challenger's model with (card #58). None when the file names none —
    the binary's default then, which this runtime does not guess — or
    cannot be read."""
    path = machine.codex_home() / "config.toml"
    try:
        loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    named = loaded.get("model")
    return named if isinstance(named, str) and named else None
