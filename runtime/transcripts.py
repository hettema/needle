"""What a lane handed out, read from its transcripts (plan 12, item 3).

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

from domain.handout import Dispatch
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
