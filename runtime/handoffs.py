"""The wall detector's files for background sessions, read verbatim.

`claude-acct handoff` (the `StopFailure` hook, matcher `rate_limit`) writes
`<handoff dir>/<session_id>.json` the moment a background session's turn dies
on a limit, naming the slot and model the one rule chose. The runtime acts
on the file and never reads the limit message for meaning (plan 02, ruling
1). A file it cannot read is named, never skipped in silence.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from domain.slot import Handoff, Model
from runtime import machine


class Handoffs(BaseModel):
    by_session: dict[str, Handoff]
    unreadable: list[str]
    """Paths in the handoff directory that are not a handoff the runtime can read."""


def _when(value: object) -> datetime:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), UTC)
    if isinstance(value, str):
        return datetime.fromisoformat(value).astimezone(UTC)
    raise ValueError(f"no time in {value!r}")


def _model(value: object) -> Model | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"model {value!r}")
    return Model(value)


def read_handoff(path: Path) -> Handoff:
    blob = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(blob, dict):
        raise ValueError("not an object")
    pid = blob.get("pid")
    stopped = blob.get("stopped")
    short = blob.get("short_id") or blob.get("daemon_short")
    return Handoff(
        session_id=str(blob["session_id"]),
        short_id=str(short) if short else None,
        from_slot=str(blob["from"]),
        account=str(blob["account"]),
        model=_model(blob.get("model")),
        prompt=str(blob.get("prompt") or ""),
        reason=str(blob.get("reason") or ""),
        at=_when(blob.get("at")),
        cwd=str(blob["cwd"]) if blob.get("cwd") else None,
        worktree=str(blob["worktree"]) if blob.get("worktree") else None,
        pid=int(pid) if isinstance(pid, int | float | str) and str(pid).isdigit() else None,
        stopped=bool(stopped) if isinstance(stopped, bool) else None,
        path=str(path),
    )


def read_handoffs() -> Handoffs:
    folder = machine.handoff_dir()
    by_session: dict[str, Handoff] = {}
    unreadable: list[str] = []
    if not folder.is_dir():
        return Handoffs(by_session={}, unreadable=[])
    for path in sorted(folder.glob("*.json")):
        try:
            handoff = read_handoff(path)
        except (OSError, ValueError, KeyError, TypeError):
            unreadable.append(str(path))
            continue
        by_session[handoff.session_id] = handoff
    return Handoffs(by_session=by_session, unreadable=unreadable)


def remove(handoff: Handoff) -> None:
    """The move it asked for is done and verified; the file has served."""
    Path(handoff.path).unlink(missing_ok=True)
