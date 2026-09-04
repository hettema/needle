"""Every path the runtime reads on this machine and every command it runs.

One module, so the fixture floor can stand in for the machine whole: each
path answers to an environment variable, each command is found on PATH, and
a ratchet under `tests/ratchets/` holds that nothing else under `runtime/`
reaches the machine. The facts here were verified on this machine on
2026-09-04 (plan 02, rulings).
"""

import contextlib
import os
import re
import shutil
import subprocess
from pathlib import Path

PROC = Path("/proc")
SPAWN_REAP_SECONDS = 5.0
"""How long to wait for a fire-and-forget launcher to exit (it exits at once);
past it the launcher is left unreaped rather than blocking the caller."""


class CommandMissing(Exception):
    """A command the runtime needs is not on PATH. Named, never silent."""


Timeout = subprocess.TimeoutExpired
"""What `run` raises past its deadline, named here so no other module needs subprocess."""


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
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout, check=False
    )


def spawn(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    """Start a process the runtime never waits on, pipes to or signals.

    A window is the owner's room: 0.1 held a pipe to the launcher, whose
    process chain ends in the terminal itself, and killed the window when its
    wait expired. Its own session and no pipes at all is what makes a door a
    room he can stay in.
    """
    child = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    # The launcher itself exits at once — `omarchy-launch-tui` ends in
    # `exec setsid …`, which forks the terminal into its own session and
    # returns — so this reaps the launcher without holding the window it
    # started. A launcher that somehow lingers is left alone rather than
    # waited on; the window's own proof, not this, is what the caller trusts.
    with contextlib.suppress(subprocess.TimeoutExpired):
        child.wait(timeout=SPAWN_REAP_SECONDS)


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
    return None if fields is None or len(fields) < 20 else fields[19]


def process_alive(pid: int, start: str | None) -> bool:
    """A process exists and is the one the registry meant: pid reuse cannot
    turn a dead record into a live session."""
    actual = process_start(pid)
    return actual is not None and (start is None or actual == start)


def parent_of(pid: int) -> int | None:
    fields = _stat_fields(pid)
    return None if fields is None or len(fields) < 2 else int(fields[1])


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


def cgroup_of(pid: int) -> str | None:
    """The unit holding the process: the last segment of its cgroup path."""
    try:
        line = (PROC / str(pid) / "cgroup").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return line.rsplit("/", 1)[-1] or None


def adopt(unit: str, pids: list[int]) -> tuple[bool, str]:
    """Put running processes of ours into a transient scope of the user manager.

    `StartTransientUnit` with a `PIDs` property is what `systemd-run --scope`
    does for its own pid. Verified 2026-09-04 that the user manager takes any
    pid of ours, that the process keeps running where it was, and that
    stopping the scope ends it. Returns whether the call succeeded and the
    command's own words.
    """
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
        "1",
        "PIDs",
        "au",
        str(len(pids)),
        *[str(p) for p in pids],
        "0",
    ]
    done = run(argv, timeout=10)
    return done.returncode == 0, (done.stderr or done.stdout).strip()


def unit_name(prefix: str, label: str, suffix: str = "scope") -> str:
    """A transient unit's name, with everything systemd would refuse written as `-`."""
    safe = re.sub(r"[^A-Za-z0-9:_.\\-]", "-", label).strip("-") or "unnamed"
    return f"{prefix}{safe}.{suffix}"
