"""What a session's transcript says: what a lane handed out (plan 12, item
3), what a session is doing right now (plan 17, item 3), and where a session
no registry holds any more ran (plan 17, item 1).

Claude Code writes one `<session id>.jsonl` per session under the working
directory's slug, and a subagent's own transcript under
`<session id>/subagents/`, so the files directly in the slug's directory are
the main threads of every session that ran in the lane: its first life, a
resume that forked the id, a rescue to another slot (every slot's
`projects/` is one directory, `runtime.machine`). A dispatch is an `Agent`
tool use on a main thread and its role is the `subagent_type` it named —
the same reading `machine burn` makes, so the card and the machine count
alike.
"""

import json
from datetime import datetime
from pathlib import Path

from domain.handout import Dispatch
from domain.session import Doing
from runtime import machine


def dispatches(cwd: str) -> list[Dispatch] | None:
    """Every dispatch from every main thread that ran in `cwd`, oldest
    first; None when no transcript of the lane exists there."""
    directory = machine.transcript_dir(cwd)
    if not directory.is_dir():
        return None
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".jsonl")
    if not files:
        return None
    found: list[Dispatch] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # One file the board cannot read never hides the others; what
            # is counted is what could be read (review pass 2).
            continue
        found.extend(_dispatches_in(text))
    return sorted(found, key=lambda d: (d.at is None, d.at.timestamp() if d.at else 0.0))


def _dispatches_in(text: str) -> list[Dispatch]:
    found: list[Dispatch] = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("type") != "assistant":
            continue
        if record.get("isSidechain"):
            continue
        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Agent":
                continue
            given = block.get("input")
            role = given.get("subagent_type") if isinstance(given, dict) else None
            found.append(
                Dispatch(
                    role=str(role).lower() if role else "claude",
                    session_id=str(record.get("sessionId") or ""),
                    at=_when(record.get("timestamp")),
                )
            )
    return found


def _when(stamp: object) -> datetime | None:
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


TAIL_BYTES = 64 * 1024
"""How much of a transcript's end is read for the last step: a tool call's
record is a few hundred bytes, a tool result can be tens of kilobytes, and
the last tool use is what is wanted."""

_TELLING = ("file_path", "command", "pattern", "path", "url", "description", "prompt", "skill")
"""The input field that says what a tool acted on, in the order tried."""
STEP_LENGTH = 80


def last_step(cwd: str, session_id: str) -> Doing | None:
    """The last tool the session ran and on what, with its time, from the
    tail of its transcript (plan 17, item 3); None with no transcript or no
    tool use in the tail. A subagent's steps are on its own sidechain and
    never counted as the session's."""
    path = machine.transcript_path(cwd, session_id)
    try:
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    found: Doing | None = None
    for line in tail.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("type") != "assistant":
            continue
        if record.get("isSidechain"):
            continue
        at = _when(record.get("timestamp"))
        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if at is None or not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                found = Doing(step=_step(block), at=at)
    return found


def _step(block: dict) -> str:
    name = str(block.get("name") or "a tool")
    given = block.get("input")
    target = ""
    if isinstance(given, dict):
        for key in _TELLING:
            value = given.get(key)
            if isinstance(value, str) and value.strip():
                target = value.strip().splitlines()[0]
                break
    step = f"{name} {target}".strip()
    return step if len(step) <= STEP_LENGTH else step[: STEP_LENGTH - 1] + "…"


def find(session_id: str) -> tuple[str, Path] | None:
    """The working directory and transcript of a session no registry holds
    any more, by its id: a colleague whose process has ended has no row,
    and a call's first act is the resume from its transcript (plan 17,
    item 1). The directory is read from the transcript's own records, not
    from the slug, which is lossy."""
    root = machine.transcripts_root()
    try:
        matches = sorted(root.glob(f"*/{session_id}.jsonl"))
    except OSError:
        return None
    for path in matches:
        cwd = _cwd_in(path)
        if cwd:
            return cwd, path
    return None


def _cwd_in(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for _ in range(200):
                line = f.readline()
                if not line:
                    break
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                cwd = record.get("cwd") if isinstance(record, dict) else None
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        return None
    return None


def last_activity(cwd: str, session_id: str) -> datetime | None:
    """When the session's transcript last grew, from the newest dated record
    in its tail (plan 68, item 1): the last thing the process is known to
    have done, which is what a death that nothing names is dated by. None
    with no transcript or no dated record in the tail."""
    path = machine.transcript_path(cwd, session_id)
    try:
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    found: datetime | None = None
    for line in tail.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        at = _when(record.get("timestamp"))
        if at is not None and (found is None or at > found):
            found = at
    return found


def tokens(cwd: str) -> int | None:
    """What every session that ran in `cwd` cost, in tokens: context (input,
    cache read and cache creation) plus output of every request, counted
    once — assistant records sharing a `requestId` are one request and the
    last block's usage wins, and a record already counted from another file
    is a copy a fork or a resume left behind (the definitions `machine
    burn` fixed on 2026-09-04, so the card and the machine count alike).
    None when no transcript of the lane exists; a file that cannot be read
    never hides the others. Subagents' own transcripts are counted with the
    main threads, since the lane paid for them (card #58)."""
    directory = machine.transcript_dir(cwd)
    if not directory.is_dir():
        return None
    files = sorted(p for p in directory.rglob("*.jsonl") if p.is_file())
    if not files:
        return None
    usage_by_request: dict[str, int] = {}
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("type") != "assistant":
                continue
            message = record.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if not isinstance(usage, dict):
                continue
            request = str(record.get("requestId") or record.get("uuid") or "")
            if not request:
                continue
            counted = 0
            for key in (
                "input_tokens",
                "cache_read_input_tokens",
                "cache_creation_input_tokens",
                "output_tokens",
            ):
                value = usage.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    counted += value
            usage_by_request[request] = counted
    return sum(usage_by_request.values())
