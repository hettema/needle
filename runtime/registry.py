"""One list of sessions, read from every registry and checked against /proc.

Each config directory keeps two records: `jobs/<short>/state.json` for a
background session (its state, its cwd, the prompt it was born with) and
`sessions/<pid>.json` for every process of the CLI running under that
directory, background or interactive, with the pid and its start time. The
second is what makes the first true: a row is live only when its process is
in /proc with the start time the record stamped. The same session id in
several registries is one session; the copy with the process wins.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from domain.gate import Gate
from domain.session import Session, SessionKind, SessionState
from domain.slot import Handoff, Model, Slot
from runtime import machine

_BACKGROUND_STATES = {
    "working": SessionState.WORKING,
    "blocked": SessionState.BLOCKED,
    "done": SessionState.DONE,
    "stopped": SessionState.IDLE,
}
_INTERACTIVE_STATES = {"busy": SessionState.WORKING}


def _when(value: object) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value) / 1000, UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None
    return None


def _flag(flags: object, name: str) -> str | None:
    if not isinstance(flags, list):
        return None
    for i, flag in enumerate(flags[:-1]):
        if flag == name:
            return str(flags[i + 1])
    return None


def _model(flags: object) -> Model | None:
    value = (_flag(flags, "--model") or "").lower()
    for model in Model:
        if model.value in value:
            return model
    return None


def _effort(flags: object) -> Gate | None:
    value = _flag(flags, "--effort")
    return Gate(value) if value in {g.value for g in Gate} else None


def read_json(path: Path) -> dict[str, object] | None:
    """One of the CLI's own JSON records, or None when it is not there or not an object."""
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return blob if isinstance(blob, dict) else None


_json = read_json


def processes(config_dir: Path) -> dict[str, dict[str, object]]:
    """Session id → the `sessions/<pid>.json` record whose process is live in /proc."""
    live: dict[str, dict[str, object]] = {}
    folder = config_dir / "sessions"
    if not folder.is_dir():
        return live
    for path in sorted(folder.glob("*.json")):
        record = _json(path)
        if record is None:
            continue
        pid, start, session_id = record.get("pid"), record.get("procStart"), record.get("sessionId")
        if not isinstance(pid, int) or not isinstance(session_id, str):
            continue
        if machine.process_alive(pid, str(start) if start is not None else None):
            live[session_id] = record
    return live


def read_state(config_dir: Path, short_id: str) -> dict[str, object] | None:
    return _json(config_dir / "jobs" / short_id / "state.json")


def live_pid(config_dir: Path, session_id: str) -> int | None:
    record = processes(config_dir).get(session_id)
    pid = record.get("pid") if record else None
    return pid if isinstance(pid, int) else None


def _background_row(
    slot: Slot,
    short_id: str,
    state: dict[str, object],
    process: dict[str, object] | None,
    wall: Handoff | None,
) -> Session:
    recorded = str(state.get("state") or "")
    pid = process.get("pid") if process else None
    pid = pid if isinstance(pid, int) else None
    verdict = _BACKGROUND_STATES.get(recorded, SessionState.IDLE) if pid else SessionState.ENDED
    cwd = str(state.get("cwd") or "")
    worktree = state.get("worktreePath")
    return Session(
        slot=slot.name,
        config_dir=slot.config_dir,
        short_id=short_id,
        session_id=str(state.get("sessionId") or short_id),
        kind=SessionKind.BACKGROUND,
        name=str(state.get("name") or short_id),
        cwd=cwd,
        worktree=str(worktree) if isinstance(worktree, str) and worktree else None,
        state=verdict,
        recorded=recorded,
        detail=str(state.get("detail") or ""),
        pid=pid,
        scope=machine.cgroup_of(pid) if pid else None,
        model=_model(state.get("respawnFlags")),
        effort=_effort(state.get("respawnFlags")),
        stale=False,
        wall=wall,
        intent=str(state.get("intent") or ""),
        created_at=_when(state.get("createdAt")),
        updated_at=_when(state.get("updatedAt")),
    )


def _interactive_row(slot: Slot, session_id: str, process: dict[str, object]) -> Session:
    recorded = str(process.get("status") or "")
    pid = process["pid"]
    assert isinstance(pid, int)
    return Session(
        slot=slot.name,
        config_dir=slot.config_dir,
        short_id=session_id.split("-")[0],
        session_id=session_id,
        kind=SessionKind.INTERACTIVE,
        name=str(process.get("name") or session_id.split("-")[0]),
        cwd=str(process.get("cwd") or ""),
        worktree=None,
        state=_INTERACTIVE_STATES.get(recorded, SessionState.IDLE),
        recorded=recorded,
        detail="",
        pid=pid,
        scope=machine.cgroup_of(pid),
        model=None,
        effort=None,
        stale=False,
        wall=None,
        intent="",
        created_at=_when(process.get("startedAt")),
        updated_at=_when(process.get("updatedAt")),
    )


def read_registry(slot: Slot, walls: dict[str, Handoff]) -> list[Session]:
    """Every row one config directory holds, each checked against /proc."""
    config_dir = Path(slot.config_dir)
    live = processes(config_dir)
    rows: list[Session] = []
    seen: set[str] = set()
    jobs = config_dir / "jobs"
    if jobs.is_dir():
        for folder in sorted(jobs.iterdir()):
            state = read_state(config_dir, folder.name) if folder.is_dir() else None
            if state is None:
                continue
            session_id = str(state.get("sessionId") or folder.name)
            seen.add(session_id)
            rows.append(
                _background_row(
                    slot, folder.name, state, live.get(session_id), walls.get(session_id)
                )
            )
    for session_id, process in live.items():
        if session_id in seen or str(process.get("kind") or "") == "bg":
            continue
        rows.append(_interactive_row(slot, session_id, process))
    return rows


def merge(rows: list[Session]) -> list[Session]:
    """One row per session id. The copy with a live process wins; every other
    copy is kept and marked stale, so a registry that lies is visible as such.
    With no live copy anywhere, the most recently updated record stands."""
    by_id: dict[str, list[Session]] = {}
    for row in rows:
        by_id.setdefault(row.session_id, []).append(row)
    out: list[Session] = []
    for copies in by_id.values():
        if len(copies) == 1:
            out.extend(copies)
            continue
        live = [c for c in copies if c.pid is not None]
        winner = (
            live[0]
            if live
            else max(copies, key=lambda c: c.updated_at or datetime.min.replace(tzinfo=UTC))
        )
        for copy in copies:
            out.append(copy if copy is winner else copy.model_copy(update={"stale": True}))
    out.sort(
        key=lambda s: (
            s.stale,
            s.slot,
            -(s.updated_at or datetime.min.replace(tzinfo=UTC)).timestamp(),
        )
    )
    return out


def sessions(slots: list[Slot], walls: dict[str, Handoff]) -> list[Session]:
    rows: list[Session] = []
    for slot in slots:
        rows.extend(read_registry(slot, walls))
    return merge(rows)
