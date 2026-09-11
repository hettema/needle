"""Every path the runtime reads on this machine and every command it runs.

One module, so the fixture floor can stand in for the machine whole: each
path answers to an environment variable, each command is found on PATH, and
a ratchet under `tests/ratchets/` holds that nothing else under `runtime/`
reaches the machine. The facts here were verified on this machine on
2026-09-04 (plan 02, rulings).
"""

import contextlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from domain.dial import Meminfo
from domain.machine import BoardMachine
from infrastructure.paths import board_path, data_dir

PROC = Path("/proc")
SPAWN_REAP_SECONDS = 5.0
"""How long to wait for a fire-and-forget launcher to exit (it exits at once);
past it the launcher is left unreaped rather than blocking the caller."""


class CommandMissing(Exception):
    """A command the runtime needs is not on PATH. Named, never silent."""


class Unreachable(Exception):
    """The other machine did not answer: `ssh` exited 255, or the machine
    has no host the board can reach. The words say which (card #83)."""


MACHINE_ID_FILE = Path("/etc/machine-id")
REPO_ROOT = Path(__file__).resolve().parents[1]
"""Needle's own checkout, the one `needle` here was installed from: what
the default command for running `needle` on another machine names, since
the plan lays every project at the same path on every machine."""


def machine_id() -> str:
    """The kernel's identity for this machine: the 32 hex characters of
    `/etc/machine-id`, stable across boots and unique per install (read
    2026-09-09 on this laptop: it begins `704ef8de`). What the board
    compares to its rows to know which machine it runs on (card #83); the
    floor lays one of its own. Empty when it cannot be read, which no
    registered row matches."""
    override = os.environ.get("NEEDLE_MACHINE_ID")
    if override:
        return override.strip()
    try:
        return MACHINE_ID_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def hostname() -> str:
    """What the kernel calls this machine: the word the board uses for a
    machine nobody registered."""
    return socket.gethostname() or "this machine"


def needle_command() -> str:
    """How `needle` runs on a machine laid out like this one, as a shell
    line: the same words `board/brief.py::needle_command` gives a lane —
    `--project`, never `--directory`, for the reason recorded there."""
    return f"uv --project {shlex.quote(str(REPO_ROOT))} run needle"


SSH_OPTIONS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=5")
"""No prompt ever: a key the agent does not hold is a refusal, not a hang;
and five seconds to connect, so an unreachable machine costs the beat five
seconds and not the kernel's minutes."""
SSH_UNREACHABLE = 255
"""What `ssh` exits with when it never reached a shell on the other side."""


def control_path() -> Path:
    """Where `ssh` keeps its shared connections: one live connection per
    machine, reused by every verb for a minute, so a pass that asks the
    other machine four questions pays one handshake."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) if runtime else Path.home() / ".ssh"
    return _path("NEEDLE_SSH_CONTROL", base / "needle-ssh-%C")


def remote_argv(host: str, line: str) -> list[str]:
    """`ssh <host> -- 'bash -lc <line>'`, the command as ONE argument. `ssh`
    joins its command words with spaces and hands the string to the other
    side's shell, so `bash`, `-lc` and the line as three words would reach
    that shell as `bash -lc needle sessions --json`, which runs `needle`
    alone (Codex's reading of card #83's second pass, and shlex's); the
    line is quoted once for that shell here. A login shell, because the
    tools the other machine runs `needle` with — `uv` and the rest of
    mise's shims — are on the PATH its profile sets, and sshd's own PATH
    has none of them (exit 127, the reading of 2026-09-05 on the signal
    reader's login shell)."""
    return [
        which("ssh"),
        *SSH_OPTIONS,
        "-o",
        "ControlMaster=auto",
        "-o",
        "ControlPersist=60",
        "-o",
        f"ControlPath={control_path()}",
        host,
        "--",
        shlex.join(["bash", "-lc", line]),
    ]


class BoardUnreadable(Exception):
    """The file that says where the board is cannot be read as saying so."""


def board_elsewhere() -> BoardMachine | None:
    """The machine the board serves from, when it is not this one: the file
    `needle board NAME` wrote, read by every verb that would open the
    board's store before it does (card #83, item 3). None when there is no
    file — the board is here, or this is a one-machine board. A file that
    cannot be read as one is a refusal and never silence: the verb would
    otherwise write a store the board never reads."""
    path = board_path()
    if not path.exists():
        return None
    try:
        return BoardMachine.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as wrong:
        raise BoardUnreadable(f"{path} does not say where the board is: {wrong}") from wrong


def set_board(board: BoardMachine | None) -> Path:
    """Write which machine the board serves from, or forget it (None)."""
    path = board_path()
    if board is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(board.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def forward(board: BoardMachine, argv: list[str]) -> int:
    """Run one `needle` verb on the board's machine with its output flowing
    here as if it had run here, and answer its exit code. Nothing is read
    from stdin on either side: no verb reads it, and an open one would hold
    the other side's shell. `ssh`'s 255 is said in the board's name and as
    what it is — the line was lost, before or after the verb ran there, so
    a write is repeated only after the board is read (Codex's eighth pass
    on card #83). A signal that ended `ssh` here is answered as a shell
    answers it, 128 plus the signal; what the verb on the other side did
    after the line dropped is not known here either — a fold is a push
    and several rows — so the board is read before anything is repeated
    (the ninth pass)."""
    done = subprocess.run(
        remote_argv(board.host, f"{board.command} {shlex.join(argv)}"),
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if done.returncode == SSH_UNREACHABLE:
        print(
            f"the board serves from {board.name} ({board.host}) and the line to it was lost: "
            f"whether `needle {argv[0]}` ran there is not known here; read the board before "
            "repeating a write",
            file=sys.stderr,
        )
    if done.returncode < 0:
        return 128 - done.returncode
    return done.returncode


def run_line(
    host: str, line: str, *, timeout: float = 30.0, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one shell line on another machine and answer what it printed.
    `stdin`, when given, is what the line reads on its standard input: a
    value too large to be one argument travels there (card #123 — the one
    question names every lane on the machine, and a single argument stops
    at 128 KB, which card #83's first live move hit). Raises `Unreachable`
    when `ssh` never got a shell there."""
    done = subprocess.run(
        remote_argv(host, line),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        input=stdin,
    )
    if done.returncode == SSH_UNREACHABLE:
        raise Unreachable(f"{host} did not answer: {(done.stderr or done.stdout).strip()[:200]}")
    return done


Timeout = subprocess.TimeoutExpired
"""What `run` raises past its deadline, named here so no other module needs subprocess."""
Completed = subprocess.CompletedProcess[str]
"""What `run` and `run_line` answer, named here for the same reason."""


def _path(variable: str, default: Path) -> Path:
    override = os.environ.get(variable)
    return Path(override) if override else default


def slot_root() -> Path:
    """Where the declared slots live: `<root>/accounts.json` and `<root>/<slot>/`."""
    return _path("NEEDLE_SLOT_ROOT", Path.home() / ".claude-accounts")


def roles_path() -> Path:
    """The machine's roles file: which roles exist and the model each runs on
    today (`~/.claude-accounts/roles.json`, the machine's card 12)."""
    return slot_root() / "roles.json"


def package_cache() -> Path:
    """`uv`'s package cache, the one directory outside its worktree a lane
    must write to run the suite (card #63). Named here rather than in the
    launcher so the floor can stand it somewhere throwaway."""
    override = os.environ.get("UV_CACHE_DIR")
    if override:
        return Path(override)
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return _path("NEEDLE_PACKAGE_CACHE", base / "uv")


def claude_home() -> Path:
    """Claude Code's default config directory, which is a registry of its own:
    a session started with no `CLAUDE_CONFIG_DIR` registers here."""
    return _path("NEEDLE_CLAUDE_HOME", Path.home() / ".claude")


def handoff_dir() -> Path:
    """Where the wall detector (`claude-acct handoff`) files a background
    session's handoff: one JSON file per session id."""
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return _path("NEEDLE_HANDOFF_DIR", base / "omarchy" / "claude-acct" / "handoff" / "bg")


def acct_cache_dir() -> Path:
    """`claude-acct`'s own cache: one `<slot>.json` per subscription with
    its last limits reading — what is spent and when each allowance comes
    back (`resets`, written since 2026-09-04) — beside the handoff and
    discussion directories. Read for a park's end (plan 68, item 3), never
    written."""
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return _path("NEEDLE_ACCT_CACHE", base / "omarchy" / "claude-acct")


def discussion_dir() -> Path:
    """The machine's watercooler: where sessions of any make on this laptop
    talk through files (`~/.cache/omarchy/claude-acct/discussion/`, the
    machine's CLAUDE.md). Read by the board, never written."""
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return _path("NEEDLE_DISCUSSION_DIR", base / "omarchy" / "claude-acct" / "discussion")


def transcripts_root() -> Path:
    """Where transcripts live. Every slot's `projects/` is a symlink to the
    default directory's (verified on all four slots), so one root serves all."""
    return _path("NEEDLE_TRANSCRIPTS", claude_home() / "projects")


def transcript_dir(cwd: str) -> Path:
    """`<projects>/<cwd slug>/`: every session that ran in `cwd`, one
    `.jsonl` each; the slug is the path with every character outside
    [A-Za-z0-9] written as `-`."""
    return transcripts_root() / re.sub(r"[^A-Za-z0-9]", "-", cwd)


def transcript_path(cwd: str, session_id: str) -> Path:
    return transcript_dir(cwd) / f"{session_id}.jsonl"


def transcript_size(cwd: str, session_id: str) -> int | None:
    try:
        return transcript_path(cwd, session_id).stat().st_size
    except OSError:
        return None


def codex_home() -> Path:
    """Codex's own configuration directory, which is a registry of its
    own: every session of the other make writes a rollout under its
    `sessions/` (plan 57, `runtime.codex`)."""
    return _path("NEEDLE_CODEX_HOME", Path.home() / ".codex")


def codex_sessions_root() -> Path:
    """`<codex home>/sessions/<yyyy>/<mm>/<dd>/rollout-<stamp>-<id>.jsonl`,
    one file per Codex session, verified on this machine 2026-09-05."""
    return codex_home() / "sessions"


def cgroup_root() -> Path:
    """The control-group tree the user manager keeps its units in: a unit's
    `ControlGroup` is a path under it, and `cgroup.procs` there lists every
    process the unit holds (card #99)."""
    return _path("NEEDLE_CGROUP_ROOT", Path("/sys/fs/cgroup"))


def applications_dir() -> Path:
    """Where the desktop entries live (`~/.local/share/applications`): the
    board's own entry is the machine's, read here to open the board on a
    project when no window shows it (card #41, item 1)."""
    data = os.environ.get("XDG_DATA_HOME")
    base = Path(data) if data else Path.home() / ".local" / "share"
    return _path("NEEDLE_APPLICATIONS", base / "applications")


def meminfo_path() -> Path:
    """The kernel's memory summary; the floor lays one of its own."""
    return _path("NEEDLE_MEMINFO", PROC / "meminfo")


def hook_queue_path() -> Path:
    """Where the sessions' hook queues its events: `hook-queue.jsonl` in the
    data folder, which `hooks/needle_hook.py::data_dir` names by the same
    rule (`NEEDLE_DATA_DIR`, else the XDG data home) — never beside the
    store, which `NEEDLE_DB` moves on its own (Codex's pass 2 on card #124,
    finding 1). The floor lays its own data folder."""
    return data_dir() / "hook-queue.jsonl"


def hook_queue_moments() -> list[float] | None:
    """When each event still queued by the sessions' hook fired, in seconds
    since the epoch, one JSON object a line as `hooks/needle_hook.py`
    appends and drains it (card #124). Empty when there is no queue or
    nothing readable in it; None when the file is there and could not be
    read, which is no count at all and never a zero. The hook writes its
    lines unescaped (`ensure_ascii=False`), so a write cut short can leave
    half a character at the end: the bytes are decoded leniently, the torn
    line fails to parse and is skipped as the hook's own drain skips it, and
    every whole line still counts (Codex's cold read of card #124, call 95,
    2.2)."""
    queue = hook_queue_path()
    try:
        raw = queue.read_bytes()
    except FileNotFoundError:
        return []
    except OSError:
        return None
    # Split on the line feed alone: `splitlines` also splits U+0085, U+2028
    # and U+2029, which the hook leaves raw inside a JSON string, and would cut
    # a whole event in two (Codex's cold read of card #124, call 97, 2.3).
    lines = raw.decode("utf-8", errors="replace").split("\n")
    moments: list[float] = []
    for line in lines:
        try:
            blob = json.loads(line)
            moments.append(float(blob["at"]))
        except (ValueError, TypeError, KeyError):
            continue
    return moments


_MEMINFO_LINE = re.compile(r"^(\w+):\s+(\d+)(?:\s+kB)?", re.M)


def meminfo() -> Meminfo:
    """`MemAvailable`, `SwapTotal` and `SwapFree` in bytes, as the kernel
    counts them (kB is kibibytes there). Raises OSError when the file cannot
    be read and ValueError when a field is missing, so the caller can say
    the machine could not be read rather than guess a number."""
    text = meminfo_path().read_text(encoding="utf-8")
    fields = {key: int(value) * 1024 for key, value in _MEMINFO_LINE.findall(text)}
    try:
        return Meminfo(
            total=fields.get("MemTotal", 0),
            available=fields["MemAvailable"],
            swap_total=fields["SwapTotal"],
            swap_free=fields["SwapFree"],
        )
    except KeyError as missing:
        raise ValueError(f"{meminfo_path()} has no {missing.args[0]} line") from missing


# ── commands ───────────────────────────────────────────────────────────


def which(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise CommandMissing(f"`{name}` is not on PATH")
    return found


def run(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float = 30.0,
    host: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command here, or on `host` when one is named (card #83): the
    same words, quoted for the other machine's shell, run in `cwd` there
    when one is given. An environment never crosses the wire — what a
    session on another machine runs with is that machine's runtime's to
    set — so `env` with `host` is refused rather than silently dropped."""
    if host is not None:
        if env is not None:
            raise ValueError("an environment cannot be sent to another machine")
        line = shlex.join(argv)
        if cwd is not None:
            line = f"cd {shlex.quote(str(cwd))} && {line}"
        return run_line(host, line, timeout=timeout)
    return subprocess.run(
        argv, capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout, check=False
    )


_forgotten: list[subprocess.Popen[bytes]] = []
"""Children started with `spawn(…, wait=False)` and still to be reaped: a
notification stays on his screen until he dismisses it, so its process
lives for hours, and a handle dropped on the floor warns at collection."""


def spawn(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    wait: bool = True,
    host: str | None = None,
) -> None:
    """Start a process the runtime never waits on, pipes to or signals —
    here, or on `host` through `ssh` when the desktop is another machine
    (card #83); the launcher there ends in `setsid` as here, so the `ssh`
    returns when it does and the window outlives it.

    A window is the owner's room: 0.1 held a pipe to the launcher, whose
    process chain ends in the terminal itself, and killed the window when its
    wait expired. Its own session and no pipes at all is what makes a door a
    room he can stay in. With `wait=False` the caller does not even wait for
    the child to exit: a notification with a button blocks until he answers
    or dismisses it (card #41), and the loop that raised it beats on; the
    handle is kept and reaped on a later spawn.
    """
    if host is not None:
        if env is not None:
            raise ValueError("an environment cannot be sent to another machine")
        argv = remote_argv(host, shlex.join(argv))
    child = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    if not wait:
        _forgotten[:] = [c for c in _forgotten if c.poll() is None]
        _forgotten.append(child)
        return
    # The launcher itself exits at once — `omarchy-launch-tui` ends in
    # `exec setsid …`, which forks the terminal into its own session and
    # returns — so this reaps the launcher without holding the window it
    # started. A launcher that somehow lingers is left alone rather than
    # waited on; the window's own proof, not this, is what the caller trusts.
    with contextlib.suppress(subprocess.TimeoutExpired):
        child.wait(timeout=SPAWN_REAP_SECONDS)


def detach(argv: list[str], *, cwd: str | Path, log: Path) -> int:
    """Start a process the runtime watches by pid and never pipes to or
    waits on: a called Codex worker (plan 57, item 2), or a cold reading
    in a fresh thread (card #87). Its own process group, so nothing that
    reaches the caller's group ends it and a caller that exits leaves it
    running; what it prints goes to `log`, so a death has its words and a
    live worker never blocks on a full pipe. Answers the pid; a command
    that cannot be executed is an OSError here.

    Once a double fork that reparented the worker to init, which only a
    single-threaded caller may do: the board's server is a threaded
    process and, since card #87, asks a colleague from the reading loop's
    beat, so the child is spawned without a fork of our own. A finished
    child is a zombie until reaped; the pids are kept and reaped on the
    next detach, so a long-running board holds no more of them than the
    readings it opened since its last. The shell shim is only a `cd`: the
    spawn cannot change directory itself, and `exec` keeps the pid the
    caller watches. A group and not a session because this platform's
    spawn refuses `setsid` as unavailable (read 2026-09-09), and the
    caller has no controlling terminal to lose."""
    _reap()
    sink = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        pid = os.posix_spawn(
            "/bin/sh",
            ["sh", "-c", 'cd -- "$0" && exec "$@"', str(cwd), *argv],
            os.environ.copy(),
            file_actions=[
                (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
                (os.POSIX_SPAWN_DUP2, sink, 1),
                (os.POSIX_SPAWN_DUP2, sink, 2),
            ],
            setpgroup=0,
        )
    finally:
        os.close(sink)
    _detached.append(pid)
    return pid


_detached: list[int] = []
"""The processes `detach` started and has not yet seen end."""


def _reap() -> None:
    """Collect every detached child that has exited, and forget it."""
    still: list[int] = []
    for pid in _detached:
        try:
            done, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            continue
        if done == 0:
            still.append(pid)
    _detached[:] = still


def terminate(pid: int) -> None:
    """Ask a process of ours to end; a pid already gone is no error."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(pid, 15)


def session_env(config_dir: str | Path, slot: str) -> dict[str, str]:
    """The environment a session on a slot runs with. `CLAUDE_ACCOUNT` mirrors
    what `claude-acct use` sets, so the statusline and the browser router
    read the same slot from a runtime-born session as from a hand-started one."""
    return {**os.environ, "CLAUDE_CONFIG_DIR": str(config_dir), "CLAUDE_ACCOUNT": slot}


# ── processes ──────────────────────────────────────────────────────────


def _stat_fields(pid: int) -> list[str] | None:
    """The fields of /proc/<pid>/stat after the command name, so a space in
    the name cannot shift them."""
    try:
        stat = (PROC / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    return stat.rsplit(")", 1)[1].split()


def process_start(pid: int) -> str | None:
    """Field 22 of /proc/<pid>/stat, the start time the registry stamps as
    `procStart` (verified equal on every live row, 2026-09-04)."""
    fields = _stat_fields(pid)
    if fields is None or len(fields) < 20 or fields[0] == "Z":
        # A zombie has a stat line and no process: it is gone.
        return None
    return fields[19]


def process_alive(pid: int, start: str | None) -> bool:
    """A process exists and is the one the registry meant: pid reuse cannot
    turn a dead record into a live session."""
    actual = process_start(pid)
    return actual is not None and (start is None or actual == start)


def parent_of(pid: int) -> int | None:
    fields = _stat_fields(pid)
    return None if fields is None or len(fields) < 2 else int(fields[1])


def ancestors_of(pid: int) -> list[int]:
    """The process's parents up to init, nearest first; empty once it is
    gone or already init's child (card #99)."""
    found: list[int] = []
    seen = {pid}
    parent = parent_of(pid)
    while parent is not None and parent > 1 and parent not in seen:
        found.append(parent)
        seen.add(parent)
        parent = parent_of(parent)
    return found


def children_of(pid: int) -> list[int]:
    found: list[int] = []
    for entry in PROC.iterdir():
        if not entry.name.isdigit():
            continue
        fields = _stat_fields(int(entry.name))
        if fields is not None and len(fields) >= 2 and int(fields[1]) == pid:
            found.append(int(entry.name))
    return found


def descendants_of(pid: int) -> list[int]:
    out: list[int] = []
    queue = [pid]
    while queue:
        for child in children_of(queue.pop()):
            out.append(child)
            queue.append(child)
    return out


def pids() -> list[int]:
    """Every process in /proc right now."""
    return [int(entry.name) for entry in PROC.iterdir() if entry.name.isdigit()]


def cmdline_of(pid: int) -> str | None:
    """The process's argv as one space-joined line; None once it is gone."""
    try:
        raw = (PROC / str(pid) / "cmdline").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def open_files_of(pid: int) -> list[str]:
    """The paths the process holds open, as its fd links name them; empty
    when it is gone or not ours to read. A Codex terminal holds its rollout
    open and names it nowhere in argv (verified 2026-09-05)."""
    folder = PROC / str(pid) / "fd"
    try:
        entries = list(folder.iterdir())
    except OSError:
        return []
    found: list[str] = []
    for entry in entries:
        with contextlib.suppress(OSError):
            found.append(os.readlink(entry))
    return found


def cgroup_of(pid: int) -> str | None:
    """The unit holding the process: the last segment of its cgroup path."""
    try:
        line = (PROC / str(pid) / "cgroup").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return line.rsplit("/", 1)[-1] or None


_SHOW_LINE = re.compile(r"^(\w+)=(.*)$", re.M)
UNSET = "[not set]"
"""What `systemctl show` prints for a property the unit does not carry —
`MemoryCurrent` of a scope the manager no longer holds (verified
2026-09-07 on this machine, exit 0 even for a unit that never existed)."""


def show_units(units: list[str], properties: list[str]) -> dict[str, dict[str, str]]:
    """`systemctl --user show -p …` for several units in one call: per unit,
    the properties it printed, verbatim. One blank-line-separated block per
    unit, each carrying its `Id` (verified 2026-09-07); a unit the manager
    does not hold still gets a block, with `[not set]` where it has no
    value. Raises `CommandMissing` when there is no `systemctl`."""
    if not units:
        return {}
    argv = [which("systemctl"), "--user", "show", "-p", "Id"]
    for name in properties:
        argv += ["-p", name]
    done = run(argv + units, timeout=20)
    if done.returncode != 0:
        raise OSError(f"systemctl show failed: {(done.stderr or done.stdout).strip()}")
    found: dict[str, dict[str, str]] = {}
    for block in done.stdout.split("\n\n"):
        fields = dict(_SHOW_LINE.findall(block))
        if fields.get("Id"):
            found[fields["Id"]] = fields
    return found


def scope_memory(units: list[str]) -> dict[str, int]:
    """What each scope holds right now, in bytes (`MemoryCurrent`, as the
    user manager counts it); a scope with no value — gone, or never made —
    is left out. Raises `CommandMissing` or `OSError` when the reading
    could not be made, so the caller can say so rather than read zero."""
    held: dict[str, int] = {}
    for unit, fields in show_units(units, ["MemoryCurrent"]).items():
        value = fields.get("MemoryCurrent", UNSET)
        if value.isdigit():
            held[unit] = int(value)
    return held


def hold_scopes_at(units: list[str], memory_high: int) -> list[str]:
    """Set `MemoryHigh` on every scope among `units` whose mark is not
    `memory_high`, with `set-property --runtime` (verified 2026-09-09 on a
    throwaway scope of this machine's user manager: the property lands on
    a running scope and reads back). A scope the manager made before the
    runtime adopted the process, or one that outlived its session and took
    the next in, keeps the mark it was born with — Hello Revenue #483's
    read infinity beside #409's 5 GB a minute after card #107's fold — so
    the mark is read on every pass and set where it is missing. Returns
    the units set. Raises what `show_units` raises; one scope whose set
    fails or times out is skipped and the rest are still set, so a unit
    set before it is still answered and one after it is still tried
    (Codex's reading of the fix, 2026-09-09)."""
    fields = show_units(units, ["MemoryHigh"])
    held: list[str] = []
    for unit in units:
        if fields.get(unit, {}).get("MemoryHigh") == str(memory_high):
            continue
        argv = [
            which("systemctl"),
            "--user",
            "set-property",
            "--runtime",
            unit,
            f"MemoryHigh={memory_high}",
        ]
        try:
            done = run(argv, timeout=10)
        except (OSError, Timeout):
            continue
        if done.returncode == 0:
            held.append(unit)
    return held


def unit_state(unit: str) -> str | None:
    """The unit's `ActiveState` — `active`, `failed`, `inactive` — or None
    when the manager does not hold it or cannot be asked."""
    try:
        fields = show_units([unit], ["ActiveState", "LoadState"]).get(unit)
    except (OSError, Timeout, CommandMissing):
        return None
    if fields is None or fields.get("LoadState") == "not-found":
        return None
    return fields.get("ActiveState") or None


def reset_failed(unit: str) -> bool:
    """Clear a unit the manager still holds as failed. A scope oomd killed
    stays loaded as `failed` (nine of them stood on this machine on
    2026-09-07), and `StartTransientUnit` under that name is refused with
    "was already loaded" until it is reset — so a lane that came back could
    never be put in its own scope again (plan 53, item 2)."""
    try:
        done = run([which("systemctl"), "--user", "reset-failed", unit], timeout=10)
    except (OSError, Timeout, CommandMissing):
        return False
    return done.returncode == 0


def adopt(unit: str, pids: list[int], *, memory_high: int | None = None) -> tuple[bool, str]:
    """Put running processes of ours into a transient scope of the user manager.

    `StartTransientUnit` with a `PIDs` property is what `systemd-run --scope`
    does for its own pid. Verified 2026-09-04 that the user manager takes any
    pid of ours, that the process keeps running where it was, and that
    stopping the scope ends it. A unit of that name the manager still holds
    as failed is reset first (verified 2026-09-07: the call is refused
    otherwise, and lands after the reset). `memory_high` is the scope's
    high mark in bytes (`MemoryHigh`): past it the kernel throttles and
    reclaims inside the scope — a throttle it may let the scope exceed under
    pressure, never a kill — so a lane that grows presses on itself first,
    not on the windows the owner is using (card #107; verified
    2026-09-09 on a throwaway scope of this machine's user manager, systemd
    261: the property lands and `systemctl show -p MemoryHigh` reads it).
    Returns whether the call succeeded and the command's own words.
    """
    if unit_state(unit) == "failed":
        reset_failed(unit)
    properties: list[str] = ["PIDs", "au", str(len(pids)), *[str(p) for p in pids]]
    count = 1
    if memory_high is not None:
        properties += ["MemoryHigh", "t", str(memory_high)]
        count += 1
    argv = [
        which("busctl"),
        "--user",
        "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StartTransientUnit",
        "ssa(sv)a(sa(sv))",
        unit,
        "fail",
        str(count),
        *properties,
        "0",
    ]
    done = run(argv, timeout=10)
    return done.returncode == 0, (done.stderr or done.stdout).strip()


def units_named(prefix: str, kind: str = "scope") -> list[str]:
    """Every active unit of the kind whose name starts with `prefix`, as the
    user manager lists them (card #99). Verified 2026-09-09 on this
    machine: the pattern is a glob the manager matches itself, one that
    matches nothing prints nothing and exits 0, and the unit's name is the
    first word of each line. Raises `CommandMissing` or `OSError` when the
    manager cannot be asked, so the caller says so rather than read none."""
    argv = [
        which("systemctl"),
        "--user",
        "list-units",
        f"--type={kind}",
        "--state=active",
        "--plain",
        "--no-legend",
        f"{prefix}*",
    ]
    done = run(argv, timeout=20)
    if done.returncode != 0:
        raise OSError(f"systemctl list-units failed: {(done.stderr or done.stdout).strip()}")
    return [line.split()[0] for line in done.stdout.splitlines() if line.strip()]


def unit_pids(unit: str) -> list[int]:
    """Every process the unit holds right now, from its control group's
    `cgroup.procs` (card #99); none when the manager no longer holds the
    unit or the group cannot be read. Raises as `show_units` does."""
    fields = show_units([unit], ["ControlGroup"]).get(unit) or {}
    path = fields.get("ControlGroup", UNSET)
    if not path.startswith("/"):
        return []
    try:
        text = (cgroup_root() / path.lstrip("/") / "cgroup.procs").read_text(encoding="utf-8")
    except OSError:
        return []
    return [int(word) for word in text.split() if word.isdigit()]


def stop_unit(unit: str) -> tuple[bool, str]:
    """Ask the manager to stop a unit of ours, which ends every process it
    holds: what `systemctl --user stop` does to a scope (verified
    2026-09-04 for `adopt`, and by hand on three finished sessions' groups
    on 2026-09-09 — two gone in 15 ms, one whose `uvicorn` ignored the
    signal and was killed at the manager's stop timeout, the unit left
    `failed`, which `adopt` resets before reusing the name). Asked with
    `--no-block`, so a stubborn process never holds the caller for that
    timeout: the answer is whether the manager took the job, and its words;
    `unit_pids` says when the group is empty."""
    done = run([which("systemctl"), "--user", "stop", "--no-block", unit], timeout=20)
    return done.returncode == 0, (done.stderr or done.stdout).strip()


def unit_name(prefix: str, label: str, suffix: str = "scope") -> str:
    """A transient unit's name, with everything systemd would refuse written as `-`."""
    safe = re.sub(r"[^A-Za-z0-9:_.\\-]", "-", label).strip("-") or "unnamed"
    return f"{prefix}{safe}.{suffix}"


def boots() -> list[dict[str, object]]:
    """The machine's boots as the journal lists them (`journalctl
    --list-boots -o json`, verified 2026-09-09): one object per boot with
    `index` (0 is this boot, negative the previous ones), `boot_id`, and
    `first_entry` and `last_entry` in microseconds since the epoch. Empty
    when there is no journal to ask, which is only a boot unknown."""
    try:
        done = run([which("journalctl"), "--list-boots", "-o", "json", "--no-pager"], timeout=20)
    except (OSError, Timeout, CommandMissing):
        return []
    if done.returncode != 0:
        return []
    try:
        listed = json.loads(done.stdout)
    except ValueError:
        return []
    return [b for b in listed if isinstance(b, dict)] if isinstance(listed, list) else []


def journal(unit: str, lines: int, *, since: str | None = None) -> list[str]:
    """The last `lines` of a user unit's journal, each opening with its
    time (`-o short-iso`: `2026-09-05T21:32:51+0200 host systemd[1]: …`),
    so a reader can place a line inside or outside a session's life; from
    `since` (an ISO time) on when given, so a life's window is read whole
    and not only the tail — the daemon space's journal on this laptop runs
    to hundreds of lines a day and a kill four days back is past any tail.
    Empty when the journal cannot be asked, which is only a reason unknown."""
    argv = [which("journalctl"), "--user", "-u", unit, "--no-pager"]
    if since is not None:
        argv += ["--since", since]  # the interval whole, never a tail of it
    else:
        argv += ["-n", str(lines)]
    try:
        done = run([*argv, "-o", "short-iso"], timeout=20)
    except (OSError, Timeout, CommandMissing):
        return []
    if done.returncode != 0:
        return []
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]
