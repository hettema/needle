#!/usr/bin/env python3
"""Needle's session hook: the one way a session's start, stop and end reach
the board, and the one way the board's word reaches a running session.

Registered in each project's `.claude/settings.json` for SessionStart, Stop,
SessionEnd, StopFailure and PostToolUse (`needle hook install <repo>` writes
the entries). For the four session events it reads the payload from stdin,
keeps the fields the board reads, queues the event on disk, and posts the
whole queue to the running board; the board being down loses nothing, the
queue stays and drains on the next event. For PostToolUse it asks the board
for the word of the lane at its working directory — what the board learned
about the lane since it last listened (plan 10) — with half a second to
spare, and prints it as the event's context for the model; nothing is
queued, nothing is posted, and a board that is down, slow or has nothing
to say prints nothing. It never raises, never blocks a session for more
than a moment, and writes to stdout in exactly one place, from the board's
own answer — anything else on stdout would be a hook failure landing in
the session. Standard library only, so it runs under any Python 3 with no
environment of its own.
"""

import contextlib
import fcntl
import json
import os
import sys
import time
from pathlib import Path

# `urllib.request` is imported where the four session events post (`drain`)
# and `http.client` where the word is read (`answer`), not here: PostToolUse
# runs on every tool call, and the import of urllib.request alone was a
# third of the hook's cost when measured (plan 10 close-out).

POST_TIMEOUT_SECONDS = 2.0
WORD_TIMEOUT_SECONDS = 0.5
"""The ceiling on a PostToolUse: this fires on every tool call of every
session on the machine, and Claude Code's own default for a command hook
is 600 s, which would let a hung board hold every tool call."""
WORD_EVENT = "PostToolUse"
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
    import urllib.request

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


def word_target(payload: dict) -> tuple[str, int, str] | None:
    """Host, port and path for the word's read, or None when this payload
    asks for none: not a PostToolUse, a subagent's, or no working directory
    to name a lane by."""
    from urllib.parse import urlencode, urlsplit

    if payload.get("hook_event_name") != WORD_EVENT or payload.get("agent_id"):
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return None
    url = urlsplit(board_url())
    if not url.hostname:
        return None
    return url.hostname, url.port or 80, "/api/word?" + urlencode({"cwd": cwd})


def answer(payload: dict) -> None:
    """The one place this script writes to stdout: the board's word for the
    lane, as PostToolUse's context for the model. Every path is inside the
    one catch-all, so a board that is down, slow, answers with anything but
    the word, or names no lane prints nothing at all."""
    try:
        import http.client

        target = word_target(payload)
        if target is None:
            return
        host, port, path = target
        connection = http.client.HTTPConnection(host, port, timeout=WORD_TIMEOUT_SECONDS)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            if response.status != 200:
                return
            word = json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()
        sentences = word.get("sentences") if isinstance(word, dict) else None
        if not isinstance(sentences, list) or not sentences:
            return
        said = "\n".join(str(s) for s in sentences if s)
        if not said:
            return
        print(
            json.dumps(
                {"hookSpecificOutput": {"hookEventName": WORD_EVENT, "additionalContext": said}}
            )
        )
    except Exception:  # noqa: BLE001 — a word that cannot be read is no word
        return


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict) and payload.get("hook_event_name") == WORD_EVENT:
            # A read, never an event: the queue stays the session events' path.
            answer(payload)
            return 0
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
            # The board being down is not an error: the queue drains on the
            # next event. URLError is an OSError, so one name covers it.
            with contextlib.suppress(OSError, ValueError):
                drain(queue, lock)
    except Exception:  # noqa: BLE001 — a hook failure must never break a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
