"""The fixture floor: a machine the runtime can stand on without touching this one.

Every path the runtime reads is redirected to a temporary directory through
the variables `runtime.machine` answers to, and every command it runs is a
stand-in under `tests/fakes/bin/`, first on PATH. The fakes register
sessions the way the real CLI does and follow the fate a test scripts, so a
launch, a wall, a move and a window can each be played without a real
subscription, a real daemon or a real window (plan 02, criterion 6). A
ratchet holds that the floor is under every test.
"""

import fcntl
import json
import os
import signal
import subprocess
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
    codex_home: Path
    acct_cache: Path
    state_file: Path
    cgroup_root: Path
    applications: Path
    machine_id: str = "floor-machine-0001"
    """What the floor's `/etc/machine-id` says (card #83): a second floor
    laid beside this one answers with its own."""
    ssh_control: Path | None = None
    """Where the runtime's `ssh` would keep its shared connection: under
    the floor, so a test never writes into the laptop's runtime directory."""
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

    def _locked(self, work):
        """Under the same lock every fake binary takes before it touches the
        state file. Without it a read can land mid-write and see half a file:
        `test_a_reading_is_stricter_at_once_and_a_looser_one_authorises_nothing`
        died on a `JSONDecodeError` at setup on 2026-09-08 while the board's
        own loops ran a fake in another thread. A suite that fails at random
        is a trunk that goes red at random, so the reader takes the lock the
        writers already take."""
        with (self.state_file.parent / (self.state_file.name + ".lock")).open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return work()
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def state(self) -> dict:
        return self._locked(lambda: json.loads(self.state_file.read_text(encoding="utf-8")))

    def update(self, **changes: object) -> None:
        def write() -> None:
            blob = json.loads(self.state_file.read_text(encoding="utf-8"))
            blob.update(changes)
            self.state_file.write_text(json.dumps(blob, indent=1), encoding="utf-8")

        self._locked(write)

    def answer_best(
        self,
        slot: str,
        model: str | None = None,
        why: str = "",
        *,
        make: str | None = None,
        tier: int | None = None,
        tier_ruled_on: str | None = None,
        tier_why: str = "",
    ) -> None:
        """What the one rule answers next. `make`, `tier` and `tier_ruled_on`
        are left out unless a test asks for them, because `claude-acct` today
        answers without them and the runtime must read that answer (card
        #63): a test that names none of the three plays the rule as it is."""
        answer: dict[str, object] = {
            "slot": slot,
            "model": model,
            "why": why or f"headroom on {slot}",
        }
        if make is not None:
            answer["make"] = make
        if tier is not None:
            answer["tier"] = tier
        if tier_ruled_on is not None:
            answer["tier_ruled_on"] = tier_ruled_on
        if tier_why:
            answer["tier_why"] = tier_why
        self.update(best=answer)

    def refuse_best(self, error: str) -> None:
        self.update(best={"error": error})

    def write_scope(self, unit: str, pids: list[int], *, active: bool = True) -> None:
        """A unit the fake manager holds, and what its control group holds
        (card #99): `list-units` lists it while active, `show -p
        ControlGroup` names its group, and `cgroup.procs` there lists the
        pids. The fake's `stop` marks it inactive and records the unit in
        `scope_stops`; it ends no process, so a test kills what it planted."""
        group = f"/app.slice/{unit}"
        procs = self.cgroup_root / group.lstrip("/") / "cgroup.procs"
        procs.parent.mkdir(parents=True, exist_ok=True)
        procs.write_text("".join(f"{pid}\n" for pid in pids), encoding="utf-8")

        def write() -> None:
            blob = json.loads(self.state_file.read_text(encoding="utf-8"))
            blob.setdefault("scopes", {})[unit] = {
                "ActiveState": "active" if active else "inactive",
                "LoadState": "loaded",
                "ControlGroup": group,
            }
            self.state_file.write_text(json.dumps(blob, indent=1), encoding="utf-8")

        self._locked(write)

    def write_board_entry(self, slug: str, base: str = "http://127.0.0.1:8480") -> Path:
        """The board's desktop entry for a project, as the machine writes it
        (card #41): its Exec runs the floor's `board-window` stand-in on
        the `--app=` URL, which adds a client under Chromium's app-id."""
        path = self.applications / f"Needle {slug}.desktop"
        path.write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name=Needle {slug}\n"
            f"Exec={FAKE_BIN / 'board-window'} --app={base}/p/{slug}\n"
            "Terminal=false\n",
            encoding="utf-8",
        )
        return path

    def script_launches(self, *fates: dict) -> None:
        self.update(launches=list(fates))

    def lay_host(self, name: str, *, available_gb: float = 24.0) -> "Floor":
        """A second machine (card #83): its own floor under this one's root,
        reached by the fake `ssh` under `name`, sharing this floor's fake
        state (the scripted fates and the compositor are one machine's
        worth of stand-ins) and its own everything else — slots, registries,
        memory, store, machine id. `needle` there is the venv's own script,
        run by the fake `ssh` with the host's environment."""
        other = lay(self.root / "hosts" / name)
        other.machine_id = f"floor-machine-{name}"
        other.state_file = self.state_file
        other.ssh_control = self.ssh_control
        write_meminfo(other.meminfo, available_gb=available_gb, swap_free_gb=8.0, swap_total_gb=8.0)
        env = {
            variable: str(getattr(other, attribute)) for variable, attribute in ENVIRONMENT.items()
        }
        env["NEEDLE_DB"] = str(other.root / "needle.db")
        hosts = self.state().get("hosts") or {}
        hosts[name] = {"env": env}
        self.update(hosts=hosts)
        return other

    def host_down(self, name: str, down: bool = True) -> None:
        """The other machine stops answering: the fake `ssh` exits 255."""
        hosts = self.state().get("hosts") or {}
        hosts[name]["down"] = down
        self.update(hosts=hosts)

    def write_limits(
        self, slot: str, *, spent: dict[str, float], resets: dict[str, str], fetched_at: float
    ) -> Path:
        """One subscription's last limits reading as `claude-acct cache`
        writes it (`<cache>/<slot>.json`, read 2026-09-09): the share spent
        per allowance label and when each comes back."""
        self.acct_cache.mkdir(parents=True, exist_ok=True)
        path = self.acct_cache / f"{slot}.json"
        path.write_text(
            json.dumps(
                {
                    "account": slot,
                    "email": IDENTITIES.get(slot),
                    "tier": "Max 20x",
                    "fetchedAt": fetched_at,
                    "limits": spent,
                    "resets": resets,
                    "auth": "",
                }
            ),
            encoding="utf-8",
        )
        return path

    def write_boots(self, *boots: tuple[int, str, str, str]) -> None:
        """The machine's boots as `journalctl --list-boots -o json` lists
        them: (index, boot id, first entry, last entry), the times in ISO."""
        listed = []
        for index, boot_id, first, last in boots:
            listed.append(
                {
                    "index": index,
                    "boot_id": boot_id,
                    "first_entry": int(_epoch(first) * 1_000_000),
                    "last_entry": int(_epoch(last) * 1_000_000),
                }
            )
        self.update(boots=listed)

    def write_journal(self, unit: str, *lines: str) -> None:
        """What `journalctl --user -u <unit> -o short-iso` prints: each line
        given with its stamp in front, as the real journal prints it."""
        journal = self.state().get("journal") or {}
        journal[unit] = list(lines)
        self.update(journal=journal)

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

    def write_rollout(
        self,
        session_id: str,
        *,
        cwd: str = "/tmp/somewhere",
        source: str = "exec",
        model: str | None = None,
        started_at: str = "2026-09-05T09:00:00.000Z",
        mid_turn: bool = False,
        tool: str | None = None,
        tool_input: str = "",
        malformed: bool = False,
    ) -> Path:
        """A Codex rollout as Codex writes one (verified 2026-09-05): the
        `session_meta` head naming the session, its directory and its
        source (`cli` for a terminal, `exec` for a worker), then a turn —
        open when `mid_turn`, else closed by `task_complete` — with one
        tool call in it when `tool` is named."""
        stamp = started_at.replace(":", "-").split(".")[0]
        folder = self.codex_home / "sessions" / "2026" / "09" / "05"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"rollout-{stamp}-{session_id}.jsonl"
        if malformed:
            path.write_text("{not json\n", encoding="utf-8")
            return path
        meta = {
            "timestamp": started_at,
            "ordinal": 0,
            "type": "session_meta",
            "payload": {
                "session_id": session_id,
                "id": session_id,
                "timestamp": started_at,
                "cwd": cwd,
                "originator": "codex-tui" if source == "cli" else "codex_exec",
                "cli_version": "0.152.1",
                "source": source,
            },
        }
        if model is not None:
            # Where Codex records the model that answered: the provenance of
            # the base instructions it was given (0.153.4, read 2026-09-08).
            meta["payload"]["base_instructions"] = {
                "text": "You are Codex.",
                "provenance": {"type": "model", "model": model},
            }
        records = [
            meta,
            {
                "timestamp": started_at,
                "ordinal": 1,
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "t1"},
            },
        ]
        if tool is not None:
            records.append(
                {
                    "timestamp": "2026-09-05T09:00:05.000Z",
                    "ordinal": 2,
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "status": "completed",
                        "call_id": "call_1",
                        "name": tool,
                        "input": tool_input,
                    },
                }
            )
        if not mid_turn:
            records.append(
                {
                    "timestamp": "2026-09-05T09:00:09.000Z",
                    "ordinal": 3,
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "t1", "last_agent_message": ""},
                }
            )
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    def script_codex(self, *fates: dict) -> None:
        """What the fake `codex exec` does next, one fate per call. For a
        `resume`: `answer` (writes `text` to the answer file after `after`
        seconds), `silent` (an empty last message), `fail` (exits 1 at once
        with `stderr`), `linger` (stays at work until stopped). For a lane
        (an `exec` with no subcommand): `linger` writes a rollout of its own
        and stays at work, which is a lane that took; `fail` and `silent`
        end at once, which is a lane that did not."""
        self.update(codex=list(fates))

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


def _epoch(stamp: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


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


IN_MEMORY = {"tmpfs", "ramfs"}


def filesystem_of(path: Path) -> str:
    """The kind of filesystem the path stands on, as the kernel answers for
    that path (`statfs`, printed by `stat -f %T`): "tmpfs", "btrfs", ...
    Why the kernel and not the mount table: three review reads in a row
    found a way the table's order or spelling misled a reader — an escaped
    name, a mount hidden under a later one on its parent, a moved mount that
    keeps its earlier entry — and the kernel's own answer for the path has
    no order to misread (card #109). devtmpfs answers "tmpfs", being one.
    The floor check refuses a root whose answer is in IN_MEMORY, and every
    run writes its answer to the ledger the plan's loop reads."""
    done = subprocess.run(
        ["stat", "-f", "-c", "%T", str(path)], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


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
    codex_home = root / "codex-home"
    (codex_home / "sessions").mkdir(parents=True)
    acct_cache = root / "acct-cache"
    acct_cache.mkdir()
    # A machine with room: the dial's memory floor is 5 GB (board/dial.py).
    meminfo = root / "meminfo"
    write_meminfo(meminfo, available_gb=16.0, swap_free_gb=8.0, swap_total_gb=8.0)
    cgroups = root / "cgroup"
    cgroups.mkdir()
    applications = root / "applications"
    applications.mkdir()
    ssh_control = root / "ssh-control"
    ssh_control.mkdir()
    state = root / "fake-state.json"
    state.write_text(
        json.dumps(
            {
                # As `claude-acct best` answers today: a slot, and `model:
                # null` for that slot's own top rung. The floor says what the
                # machine says, so the suite reads what the owner reads; a
                # test that wants a rung named by its model scripts it
                # (`answer_best(slot, "fable")`), and both paths are live
                # (card #63).
                "best": {"slot": "alpha", "model": None, "why": "Fable headroom on alpha"},
                "best_calls": [],
                "launches": [],
                "launch_log": [],
                "stops": [],
                "clients": [],
                "spawned": [],
                "busctl_calls": [],
                "scopes": {},
                "scope_stops": [],
                "notified": [],
                "played": [],
                "press": None,
                "codex": [],
                "codex_log": [],
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
        codex_home=codex_home,
        acct_cache=acct_cache,
        state_file=state,
        cgroup_root=cgroups,
        applications=applications,
        ssh_control=ssh_control / "needle-ssh-%C",
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
    "NEEDLE_CODEX_HOME": "codex_home",
    "NEEDLE_ACCT_CACHE": "acct_cache",
    "NEEDLE_FAKE_STATE": "state_file",
    "NEEDLE_CGROUP_ROOT": "cgroup_root",
    "NEEDLE_APPLICATIONS": "applications",
    "NEEDLE_MACHINE_ID": "machine_id",
    "NEEDLE_SSH_CONTROL": "ssh_control",
}
"""Variable → the floor attribute it points at. `runtime.machine` reads all
but the fake state; the fakes read that one. The machine id is a value,
not a path: what the floor's kernel would say it is (card #83)."""
