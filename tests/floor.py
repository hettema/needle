"""The fixture floor: a machine the runtime can stand on without touching this one.

Every path the runtime reads is redirected to a temporary directory through
the variables `runtime.machine` answers to, and every command it runs is a
stand-in under `tests/fakes/bin/`, first on PATH. The fakes register
sessions the way the real CLI does and follow the fate a test scripts, so a
launch, a wall, a move and a window can each be played without a real
subscription, a real daemon or a real window (plan 02, criterion 6). A
ratchet holds that the floor is under every test.
"""

import json
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path

FAKE_BIN = Path(__file__).parent / "fakes" / "bin"
SLOTS = ("alpha", "beta")
IDENTITIES = {"alpha": "alpha@example.test", "beta": "beta@example.test"}


@dataclass
class Floor:
    root: Path
    slot_root: Path
    claude_home: Path
    handoff_dir: Path
    transcripts: Path
    discussion: Path
    meminfo: Path
    state_file: Path
    pids: list[int] = field(default_factory=list)

    def config_dir(self, slot: str) -> Path:
        return self.slot_root / slot

    def set_memory(
        self, *, available_gb: float, swap_free_gb: float, swap_total_gb: float = 8.0
    ) -> None:
        """What the machine reports of its memory: the floor's `/proc/meminfo`."""
        write_meminfo(
            self.meminfo,
            available_gb=available_gb,
            swap_free_gb=swap_free_gb,
            swap_total_gb=swap_total_gb,
        )

    # ── the fakes' state ───────────────────────────────────────────────

    def state(self) -> dict:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def update(self, **changes: object) -> None:
        blob = self.state()
        blob.update(changes)
        self.state_file.write_text(json.dumps(blob, indent=1), encoding="utf-8")

    def answer_best(self, slot: str, model: str | None = None, why: str = "") -> None:
        self.update(best={"slot": slot, "model": model, "why": why or f"headroom on {slot}"})

    def refuse_best(self, error: str) -> None:
        self.update(best={"error": error})

    def script_launches(self, *fates: dict) -> None:
        self.update(launches=list(fates))

    # ── the registries, as the machine would have written them ────────

    def write_job(
        self,
        slot: str,
        short: str,
        *,
        state: str = "working",
        detail: str = "",
        cwd: str = "/tmp/somewhere",
        name: str | None = None,
        session_id: str | None = None,
        updated_at: str = "2026-09-04T09:00:00Z",
        model: str = "fable",
        effort: str = "xhigh",
        worktree: str | None = None,
        intent: str = "the brief",
        resumed_from: str | None = None,
    ) -> str:
        session_id = session_id or f"{short}-0000-4000-8000-000000000000"
        blob = {
            "state": state,
            "detail": detail,
            "sessionId": session_id,
            "resumeSessionId": resumed_from or session_id,
            "cwd": cwd,
            "name": name or short,
            "respawnFlags": ["--effort", effort, "--model", model],
            "intent": intent,
            "createdAt": "2026-09-04T08:00:00Z",
            "updatedAt": updated_at,
        }
        if worktree:
            blob["worktreePath"] = worktree
        path = self.config_dir(slot) / "jobs" / short / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(blob), encoding="utf-8")
        return session_id

    def write_process(
        self,
        slot: str,
        session_id: str,
        pid: int,
        *,
        start: str | None = None,
        kind: str = "bg",
        status: str = "busy",
        cwd: str = "/tmp/somewhere",
        name: str = "a session",
    ) -> None:
        path = self.config_dir(slot) / "sessions" / f"{pid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": pid,
                    "sessionId": session_id,
                    "cwd": cwd,
                    "procStart": start if start is not None else proc_start(pid),
                    "kind": kind,
                    "status": status,
                    "name": name,
                    "startedAt": 1788505419526,
                }
            ),
            encoding="utf-8",
        )

    def write_handoff(self, session_id: str, **fields: object) -> Path:
        blob = {
            "session_id": session_id,
            "short_id": session_id.split("-")[0],
            "daemon_short": session_id.split("-")[0],
            "pid": None,
            "from": "alpha",
            "cwd": "/tmp/somewhere",
            "worktree": "/tmp/somewhere",
            "account": "beta",
            "model": None,
            "prompt": "[claude-acct] Carry on.",
            "reason": "You've reached your Fable limit.",
            "why": "Fable headroom on beta",
            "at": 1788505419.5,
            "stopped": False,
        }
        blob.update(fields)
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        path = self.handoff_dir / f"{session_id}.json"
        path.write_text(json.dumps(blob), encoding="utf-8")
        return path

    def write_transcript(self, cwd: str, session_id: str, size: int) -> Path:
        from runtime import machine

        path = machine.transcript_path(cwd, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{"type":"user"}\n' * (size // 16 + 1))
        return path

    # ── cleanup ────────────────────────────────────────────────────────

    def kill_everything(self) -> None:
        """Kill the `sleep` processes the fake CLI left standing, and nothing else.

        Killing by bare pid is the caller-matching hazard CLAUDE.md names: a
        pid the fake recorded may since have been reused by an unrelated
        process — pytest itself, a `uv` helper — and a blind SIGKILL took the
        whole run down (exit 137). So a pid is killed only when it is still a
        `sleep` (the fake's session process) with the start time recorded for
        it; a reused pid is a different command, or a different start, and is
        left alone."""
        recorded = self.state().get("pids", [])
        for entry in [*({(p, None) for p in self.pids}), *recorded]:
            pid, start = entry if isinstance(entry, list | tuple) else (entry, None)
            if pid == os.getpid() or not is_sleep(int(pid), start):
                continue
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue


def is_sleep(pid: int, start: str | None) -> bool:
    """The pid names a live `sleep` whose start time is the recorded one."""
    proc = Path("/proc") / str(pid)
    try:
        if (proc / "comm").read_text(encoding="utf-8").strip() != "sleep":
            return False
        return start is None or proc_start(pid) == start
    except OSError:
        return False


def proc_start(pid: int) -> str:
    return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[19]


def lay(root: Path) -> Floor:
    slot_root = root / "slots"
    for name in SLOTS:
        (slot_root / name).mkdir(parents=True)
        (slot_root / name / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"emailAddress": IDENTITIES[name]}}), encoding="utf-8"
        )
        (slot_root / name / ".credentials.json").write_text("{}", encoding="utf-8")
    (slot_root / "accounts.json").write_text(
        json.dumps(
            {
                "_comment": "the test floor's slots",
                "alpha": {"profile": "Profile 1", "email": IDENTITIES["alpha"]},
                "beta": {"profile": "Profile 2", "email": IDENTITIES["beta"]},
            }
        ),
        encoding="utf-8",
    )
    (slot_root / "roles.json").write_text(
        json.dumps(
            {
                "_comment": "the test floor's roles: the machine's shape, both roles unearned",
                "top": "claude-fable-5-1[1m]",
                "downgrade": "opus",
                "execution": None,
                "search": None,
                "_history": [],
            }
        ),
        encoding="utf-8",
    )
    home = root / "claude-home"
    home.mkdir()
    (home / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"emailAddress": IDENTITIES["alpha"]}}), encoding="utf-8"
    )
    handoffs = root / "handoff" / "bg"
    handoffs.mkdir(parents=True)
    transcripts = root / "projects"
    transcripts.mkdir()
    discussion = root / "discussion"
    discussion.mkdir()
    # A machine with room: the dial's memory floor is 5 GB (board/dial.py).
    meminfo = root / "meminfo"
    write_meminfo(meminfo, available_gb=16.0, swap_free_gb=8.0, swap_total_gb=8.0)
    state = root / "fake-state.json"
    state.write_text(
        json.dumps(
            {
                "best": {"slot": "alpha", "model": None, "why": "Fable headroom on alpha"},
                "best_calls": [],
                "launches": [],
                "launch_log": [],
                "stops": [],
                "clients": [],
                "spawned": [],
                "busctl_calls": [],
                "windows_open": True,
                "window_delay": 0.0,
                "pids": [],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return Floor(
        root=root,
        slot_root=slot_root,
        claude_home=home,
        handoff_dir=handoffs,
        transcripts=transcripts,
        discussion=discussion,
        meminfo=meminfo,
        state_file=state,
    )


def write_meminfo(
    path: Path, *, available_gb: float, swap_free_gb: float, swap_total_gb: float
) -> None:
    """In the kernel's shape: `Key:   <n> kB`, kB meaning kibibytes."""
    kb = 1024

    def line(key: str, gb: float) -> str:
        return f"{key}:{int(gb * kb * kb):>16} kB\n"

    path.write_text(
        line("MemTotal", 32.0)
        + line("MemFree", available_gb / 2)
        + line("MemAvailable", available_gb)
        + line("SwapTotal", swap_total_gb)
        + line("SwapFree", swap_free_gb),
        encoding="utf-8",
    )


ENVIRONMENT = {
    "NEEDLE_SLOT_ROOT": "slot_root",
    "NEEDLE_CLAUDE_HOME": "claude_home",
    "NEEDLE_HANDOFF_DIR": "handoff_dir",
    "NEEDLE_TRANSCRIPTS": "transcripts",
    "NEEDLE_DISCUSSION_DIR": "discussion",
    "NEEDLE_MEMINFO": "meminfo",
    "NEEDLE_FAKE_STATE": "state_file",
}
"""Variable → the floor attribute it points at. `runtime.machine` reads all
but the last; the fakes read the last."""
