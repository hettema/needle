#!/usr/bin/env python3
"""Needle's session hook: the one way a session's start, stop and end reach the board.

Registered in each project's `.claude/settings.json` for SessionStart, Stop,
SessionEnd and StopFailure (`needle hook install <repo>` writes the entry).
Reads the hook payload from stdin, keeps the fields the board reads, queues
the event on disk, and posts the whole queue to the running board. The
board being down loses nothing: the queue stays and drains on the next
event. It never raises, never writes to stdout, never blocks a session for
more than a moment — a broken bridge degrades to a stale board, never a
broken session. Standard library only, so it runs under any Python 3 with
no environment of its own.
"""

import contextlib
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

POST_TIMEOUT_SECONDS = 2.0
KEEP_SECONDS = 7 * 86400
"""Queued events older than this are dropped at the next drain: a board that
was down for a week does not need the stops of a week ago."""
KEPT = (
    "hook_event_name",
    "session_id",
    "cwd",
    "source",
    "last_assistant_message",
    "reason",
    "error",
    "transcript_path",
)


def data_dir() -> Path:
    override = os.environ.get("NEEDLE_DATA_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "needle"


def board_url() -> str:
    return os.environ.get("NEEDLE_URL", "http://127.0.0.1:8480").rstrip("/")


def event_of(payload: dict) -> dict | None:
    if payload.get("agent_id"):
        return None  # a subagent's turn; the session's own stop is what the board reads
    kind = payload.get("hook_event_name")
    if kind not in ("SessionStart", "Stop", "SessionEnd", "StopFailure"):
        return None
    event = {k: payload.get(k) for k in KEPT if payload.get(k) is not None}
    event["hook_event_name"] = kind
    event["at"] = time.time()
    return event


def to_posted(event: dict) -> dict:
    return {
        "kind": event["hook_event_name"],
        "session_id": str(event.get("session_id") or ""),
        "cwd": str(event.get("cwd") or ""),
        "at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(float(event.get("at", 0)))),
        "source": event.get("source"),
        "message": event.get("last_assistant_message"),
        "reason": event.get("reason"),
        "error": event.get("error"),
        "transcript_path": event.get("transcript_path"),
    }


def drain(queue: Path, lock) -> None:
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        lines = queue.read_text(encoding="utf-8").splitlines() if queue.is_file() else []
        horizon = time.time() - KEEP_SECONDS
        events = []
        for line in lines:
            try:
                blob = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if (
                isinstance(blob, dict)
                and float(blob.get("at", 0)) >= horizon
                and blob.get("session_id")
            ):
                events.append(blob)
        if not events:
            queue.write_text("", encoding="utf-8")
            return
        body = json.dumps([to_posted(e) for e in events]).encode("utf-8")
        request = urllib.request.Request(
            board_url() + "/api/hooks", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=POST_TIMEOUT_SECONDS) as response:
            if 200 <= response.status < 300:
                queue.write_text("", encoding="utf-8")
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        event = event_of(payload) if isinstance(payload, dict) else None
        folder = data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        queue = folder / "hook-queue.jsonl"
        with (folder / "hook-queue.lock").open("a+") as lock:
            if event is not None:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    with queue.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(event, ensure_ascii=False) + "\n")
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
            # The board being down is not an error: the queue drains on the next event.
            with contextlib.suppress(urllib.error.URLError, OSError, ValueError):
                drain(queue, lock)
    except Exception:  # noqa: BLE001 — a hook failure must never break a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
