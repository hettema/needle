#!/usr/bin/env python3
"""Needle's session hook: the one way a session's start, stop and end reach
the board, the one way the board's word reaches a running session, and the
one way the doctrine is read back into a session that has drifted from it.

Registered in each project's `.claude/settings.json` for SessionStart, Stop,
SessionEnd, StopFailure, PostToolUse and UserPromptSubmit (`needle hook
install <repo>` writes the entries), and in the machine's Codex hooks for
the events Codex fires. For the four session events it reads the payload
from stdin, keeps the fields the board reads, queues the event on disk, and
posts the whole queue to the running board; the board being down loses
nothing, the queue stays and drains on the next event. For PostToolUse it
asks the board for the word of the lane at its working directory — what the
board learned about the lane since it last listened (plan 10), naming the
file the tool call wrote when it wrote one, so a note the lane put on the
machine's watercooler is never read back to it (plan 17) — with half a
second to spare, and prints it as the event's context for the model. For
UserPromptSubmit it reads the person's prompt and, when it carries the word
"backbrief", prints two sections of `docs/HOW-WE-WORK.md` verbatim as the
turn's context (card #60): the one text is passive context that fades in
salience as a session grows, and the sections that fade first are the ones
a backbrief rests on. The hook holds no doctrine words of its own — it
names the sections and reads them from the file at fire time, so there is
nothing here to drift from the text, and a ratchet holds that every
section it names exists. Nothing is queued or posted for either read, and a
board that is down, a prompt without the word, or a doctrine file that
cannot be read prints nothing. It never raises, never blocks a session for
more than a moment, and writes to stdout in exactly one place — anything
else on stdout would be a hook failure landing in the session. Standard
library only, so it runs under any Python 3 with no environment of its own.
"""

import contextlib
import fcntl
import json
import os
import re
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
ANCHOR_EVENT = "UserPromptSubmit"
ANCHOR_WORD = re.compile(r"back[ \t]?brief|\bbb\b", re.IGNORECASE)
"""The word that asks for the re-anchor, as Hello Revenue's hook read it
since 2026-04-20: "backbrief", "back brief", or "bb" on its own."""
ANCHOR_SECTIONS = (
    "3. A session's economics are inverted",
    "8. Verify, don't assume — and the answer is usually there",
)
"""The `## ` headings of the one text read back on the word, verbatim. Why
these two: they are the rules Hello Revenue's re-anchor carried for five
months — the inverted economics, and verification against ground truth
with the search before a new primitive — and the ones whose failure is
silent: a session that has stopped checking reads exactly like one that
has not. The shape-first rule stays out; it is the owner's steering and is
delivered by the text alone."""
ANCHOR_PREFACE = "BACKBRIEF — two sections of the one text, read back verbatim from"
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


def doctrine_path() -> Path:
    """The one text, beside this script in Needle's own checkout; the floor
    and a throwaway session point elsewhere through NEEDLE_DOCTRINE."""
    override = os.environ.get("NEEDLE_DOCTRINE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "docs" / "HOW-WE-WORK.md"


def sections_of(text: str, titles: tuple[str, ...]) -> list[str]:
    """Each named `## ` section of the doctrine, heading included, up to the
    next `## ` heading — verbatim, so the anchor can never say what the text
    does not."""
    found: list[str] = []
    for title in titles:
        match = re.search(
            r"^## " + re.escape(title) + r"\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
        )
        if match:
            found.append(f"## {title}\n{match.group(1).strip()}")
    return found


def anchor(payload: dict) -> str | None:
    """The re-anchor for this prompt, or None when the payload asks for
    none: not a UserPromptSubmit, a subagent's, a prompt without the word,
    or a doctrine file that cannot be read whole."""
    if payload.get("hook_event_name") != ANCHOR_EVENT or payload.get("agent_id"):
        return None
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not ANCHOR_WORD.search(prompt):
        return None
    path = doctrine_path()
    sections = sections_of(path.read_text(encoding="utf-8"), ANCHOR_SECTIONS)
    if len(sections) != len(ANCHOR_SECTIONS):
        return None
    return f"{ANCHOR_PREFACE} {path}:\n\n" + "\n\n".join(sections)


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
        # Lines are written unescaped, so a write cut short can end in half a
        # character; decoded strictly, that one tail would fail every drain
        # after it and the queue would never empty (card #124). Decoded
        # leniently, the torn line fails to parse and is skipped below.
        raw = queue.read_bytes() if queue.is_file() else b""
        lines = raw.decode("utf-8", errors="replace").splitlines()
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
    query = {"cwd": cwd}
    wrote = written(payload)
    if wrote:
        query["wrote"] = wrote
    return url.hostname, url.port or 80, "/api/word?" + urlencode(query)


WRITING_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def written(payload: dict) -> str | None:
    """The file this tool call wrote, when the tool was one that writes a
    file it names: what the board needs so a note the session put on the
    machine's watercooler is never read back to it (plan 17, item 2)."""
    if payload.get("tool_name") not in WRITING_TOOLS:
        return None
    given = payload.get("tool_input")
    path = given.get("file_path") if isinstance(given, dict) else None
    return path if isinstance(path, str) and path.startswith("/") else None


def word(payload: dict) -> str | None:
    """The board's word for the lane, or None when the board is down, slow,
    answers with anything but the word, or names no lane."""
    import http.client

    target = word_target(payload)
    if target is None:
        return None
    host, port, path = target
    connection = http.client.HTTPConnection(host, port, timeout=WORD_TIMEOUT_SECONDS)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        if response.status != 200:
            return None
        blob = json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()
    sentences = blob.get("sentences") if isinstance(blob, dict) else None
    if not isinstance(sentences, list) or not sentences:
        return None
    return "\n".join(str(s) for s in sentences if s) or None


def answer(payload: dict) -> None:
    """The one place this script writes to stdout: the board's word for the
    lane as PostToolUse's context, or the doctrine's two sections as
    UserPromptSubmit's. Every path is inside the one catch-all, so whatever
    cannot be read prints nothing at all."""
    try:
        event = payload.get("hook_event_name")
        said = word(payload) if event == WORD_EVENT else anchor(payload)
        if not said:
            return
        print(
            json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": said}})
        )
    except Exception:  # noqa: BLE001 — a word that cannot be read is no word
        return


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict) and payload.get("hook_event_name") in (WORD_EVENT, ANCHOR_EVENT):
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
                    # A write cut short leaves a line with no end; appended
                    # onto it, this event would join the torn line and be
                    # dropped with it at the drain (card #124).
                    with queue.open("a+b") as f:
                        if f.seek(0, os.SEEK_END):
                            f.seek(-1, os.SEEK_END)
                            if f.read(1) != b"\n":
                                f.write(b"\n")
                        f.write((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
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
