"""The session hook: queues on disk, drains to the board, never blocks and
never raises (plan 03, item 3); and on PostToolUse carries the board's word
into the session, or nothing (plan 10, item 2). Run as the real script,
against a small HTTP server standing in for the board."""

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from tests.ratchets.paths import REPO

HOOK = REPO / "hooks" / "needle_hook.py"
LANE = "/srv/p/.claude/worktrees/card-7-x"
WORD = {
    "project": "p",
    "card_number": 7,
    "sentences": [
        "#9's lane is also editing README.md. Say in the watercooler what you are doing there.",
        "#9 said on the watercooler: README.md is mine until the fold",
    ],
    "read_at": "2026-09-04T12:00:00+00:00",
}


class Board(HTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.posts: list[list[dict]] = []
        self.up = True
        self.slow = False
        self.words: dict[str, dict] = {LANE: WORD}
        self.reads: list[str] = []
        self.wrote: list[str | None] = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 — http.server's own name
        server: Board = self.server  # type: ignore[assignment]
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"[]")
        if not server.up:
            self.send_response(503)
            self.end_headers()
            return
        server.posts.append(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"received": %d}' % len(body))

    def do_GET(self):  # noqa: N802
        server: Board = self.server  # type: ignore[assignment]
        parts = urlsplit(self.path)
        cwd = parse_qs(parts.query).get("cwd", [""])[0]
        server.reads.append(cwd)
        server.wrote.append(parse_qs(parts.query).get("wrote", [None])[0])
        if server.slow:
            time.sleep(1.5)
        if not server.up:
            self.send_response(503)
            self.end_headers()
            return
        word = server.words.get(cwd)
        if parts.path != "/api/word" or word is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(word).encode("utf-8"))

    def log_message(self, *args):  # quiet
        return


def run_hook(payload: dict, data_dir: Path, url: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"NEEDLE_DATA_DIR": str(data_dir), "NEEDLE_URL": url, "PATH": "/usr/bin:/bin"},
        timeout=20,
    )


def serving():
    board = Board()
    thread = threading.Thread(target=board.serve_forever, daemon=True)
    thread.start()
    return board, f"http://127.0.0.1:{board.server_address[1]}"


def test_the_hook_queues_while_the_board_is_down_and_drains_when_it_is_up(tmp_path: Path):
    board, url = serving()
    queue = tmp_path / "hook-queue.jsonl"
    try:
        board.up = False
        first = run_hook(
            {
                "hook_event_name": "Stop",
                "session_id": "aaaa0001-0000-4000-8000-000000000000",
                "cwd": LANE,
                "last_assistant_message": "Which one?",
                "transcript_path": "/t.jsonl",
                "tool_output": "never kept",
            },
            tmp_path,
            url,
        )
        assert first.returncode == 0 and first.stdout == ""
        assert len(queue.read_text().splitlines()) == 1, "queued while the board refused"
        assert board.posts == []

        board.up = True
        second = run_hook(
            {
                "hook_event_name": "SessionEnd",
                "session_id": "aaaa0001-0000-4000-8000-000000000000",
                "cwd": LANE,
                "reason": "prompt_input_exit",
            },
            tmp_path,
            url,
        )
        assert second.returncode == 0
        assert len(board.posts) == 1 and [e["kind"] for e in board.posts[0]] == [
            "Stop",
            "SessionEnd",
        ]
        assert (
            board.posts[0][0]["message"] == "Which one?" and "tool_output" not in board.posts[0][0]
        )
        assert board.posts[0][1]["reason"] == "prompt_input_exit"
        assert queue.read_text() == "", "drained"

        ignored = run_hook(
            {"hook_event_name": "Stop", "session_id": "x", "cwd": "/x", "agent_id": "sub-1"},
            tmp_path,
            url,
        )
        assert ignored.returncode == 0 and len(board.posts) == 1, (
            "a subagent's stop is not the session's"
        )
    finally:
        board.shutdown()
        board.server_close()


def test_the_hook_never_raises_on_garbage(tmp_path: Path):
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        env={
            "NEEDLE_DATA_DIR": str(tmp_path),
            "NEEDLE_URL": "http://127.0.0.1:1",
            "PATH": "/usr/bin:/bin",
        },
        timeout=20,
    )
    assert done.returncode == 0 and done.stdout == "" and done.stderr == ""


def tool_use(cwd: str = LANE, **fields) -> dict:
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "aaaa0001-0000-4000-8000-000000000000",
        "cwd": cwd,
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": {"stdout": "x"},
    }
    payload.update(fields)
    return payload


def test_on_a_tool_use_the_hook_prints_the_boards_word_as_context_and_nothing_else(
    tmp_path: Path,
):
    """Plan 10, item 2: the word reaches the session as the event's context;
    the event is never queued or posted; and every way the board can fail
    to answer prints nothing, with exit 0 each time."""
    board, url = serving()
    queue = tmp_path / "hook-queue.jsonl"
    try:
        said = run_hook(tool_use(), tmp_path, url)
        assert said.returncode == 0 and said.stderr == ""
        assert json.loads(said.stdout) == {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(WORD["sentences"]),
            }
        }
        assert board.reads == [LANE]
        assert board.posts == [] and not queue.exists(), "a read, never an event"

        board.words[LANE] = {**WORD, "sentences": []}
        empty = run_hook(tool_use(), tmp_path, url)
        assert empty.returncode == 0 and empty.stdout == "" and empty.stderr == ""

        board.words[LANE] = WORD
        unknown = run_hook(tool_use(cwd="/srv/p"), tmp_path, url)
        assert unknown.returncode == 0 and unknown.stdout == "", "no lane, nothing to say"

        sub = run_hook(tool_use(agent_id="sub-1"), tmp_path, url)
        assert sub.returncode == 0 and sub.stdout == ""
        assert board.reads == [LANE, LANE, "/srv/p"], "a subagent's tool use asks nothing"

        board.up = False
        down = run_hook(tool_use(), tmp_path, url)
        assert down.returncode == 0 and down.stdout == "" and down.stderr == ""
        board.up = True

        board.slow = True
        started = time.monotonic()
        late = run_hook(tool_use(), tmp_path, url)
        took = time.monotonic() - started
        assert late.returncode == 0 and late.stdout == "" and late.stderr == ""
        assert took < 1.4, f"a slow board holds the hook for {took:.2f} s; the ceiling is 0.5"
        board.slow = False

        gone = run_hook(tool_use(), tmp_path, "http://127.0.0.1:1")
        assert gone.returncode == 0 and gone.stdout == "" and gone.stderr == ""
    finally:
        board.shutdown()
        board.server_close()


DOCTRINE_FIXTURE = """# How we work

words at the head.

## 3. A session's economics are inverted

A session does the whole thing right. NONCE-TORTOISE-7731

Keep every judgment.

## 4. Only what is written survives

Not read back.

## 8. Verify, don't assume — and the answer is usually there

Every claim a session makes stands on something it did.
*Shaped by:* a date.

## 9. Raise the standard, not just the output

Not read back either.
"""


def prompt(text: str, **extra) -> dict:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "aaaa0002-0000-4000-8000-000000000000",
        "cwd": LANE,
        "prompt": text,
    }
    payload.update(extra)
    return payload


def run_anchor(payload: dict, data_dir: Path, doctrine: Path | None) -> subprocess.CompletedProcess[str]:
    env = {"NEEDLE_DATA_DIR": str(data_dir), "NEEDLE_URL": "http://127.0.0.1:1", "PATH": "/usr/bin:/bin"}
    if doctrine is not None:
        env["NEEDLE_DOCTRINE"] = str(doctrine)
    return subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=20
    )


def test_on_the_word_the_hook_reads_the_named_sections_back_verbatim_and_nothing_else(tmp_path: Path):
    """Card #60, item 4: on "backbrief" the doctrine's named sections reach
    the session as the prompt's context, verbatim from the file, with no
    words of the hook's own beyond the preface; a prompt without the word,
    a subagent's prompt, and a doctrine file that is missing or lacks a
    named section print nothing; nothing is queued or posted."""
    doctrine = tmp_path / "HOW-WE-WORK.md"
    doctrine.write_text(DOCTRINE_FIXTURE, encoding="utf-8")
    queue = tmp_path / "hook-queue.jsonl"

    said = run_anchor(prompt("please backbrief the plan"), tmp_path, doctrine)
    assert said.returncode == 0 and said.stderr == ""
    out = json.loads(said.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "UserPromptSubmit"
    context = out["additionalContext"]
    assert context.startswith(f"BACKBRIEF — two sections of the one text, read back verbatim from {doctrine}:")
    assert "## 3. A session's economics are inverted\nA session does the whole thing right. NONCE-TORTOISE-7731\n\nKeep every judgment." in context
    assert "## 8. Verify, don't assume — and the answer is usually there\nEvery claim a session makes stands on something it did.\n*Shaped by:* a date." in context
    assert "Not read back" not in context and "words at the head" not in context
    assert not queue.exists(), "a read, never an event"

    for word in ("Back brief it", "bb", "please BB now", "backbriefed"):
        assert json.loads(run_anchor(prompt(word), tmp_path, doctrine).stdout)["hookSpecificOutput"]

    for silent in ("fix the bug", "the hobby and the rabbit", "brief back"):
        quiet = run_anchor(prompt(silent), tmp_path, doctrine)
        assert quiet.returncode == 0 and quiet.stdout == "" and quiet.stderr == "", silent

    sub = run_anchor(prompt("backbrief", agent_id="sub-1"), tmp_path, doctrine)
    assert sub.returncode == 0 and sub.stdout == ""

    gone = run_anchor(prompt("backbrief"), tmp_path, tmp_path / "missing.md")
    assert gone.returncode == 0 and gone.stdout == "" and gone.stderr == ""

    partial = tmp_path / "partial.md"
    partial.write_text(DOCTRINE_FIXTURE.replace("## 8. Verify", "## 8. Check"), encoding="utf-8")
    renamed = run_anchor(prompt("backbrief"), tmp_path, partial)
    assert renamed.returncode == 0 and renamed.stdout == "", "half an anchor is no anchor"


def test_the_real_doctrine_reads_back_under_the_context_cap(tmp_path: Path):
    """Claude Code caps a hook's additionalContext at 10,000 characters; the
    two sections of the real one text stay under it, or the cap would cut
    §8 silently."""
    said = run_anchor(prompt("backbrief"), tmp_path, None)
    context = json.loads(said.stdout)["hookSpecificOutput"]["additionalContext"]
    assert len(context) < 10_000, len(context)
    assert "## 3. A session's economics are inverted" in context
    assert "## 8. Verify, don't assume — and the answer is usually there" in context


def test_the_hook_names_the_file_a_writing_tool_wrote_and_nothing_for_the_rest(tmp_path: Path):
    """Plan 17, item 2: a note the lane puts on the machine's watercooler
    must never be read back to it, and only the hook knows what the tool
    call wrote — so a Write or Edit names its file in the read, and a Read
    or a Bash names nothing."""
    board, url = serving()
    try:
        wrote = tool_use()
        wrote.update({"tool_name": "Write", "tool_input": {"file_path": "/srv/d/from-x.md"}})
        assert run_hook(wrote, tmp_path, url).returncode == 0
        read = tool_use()
        read.update({"tool_name": "Read", "tool_input": {"file_path": "/srv/d/from-x.md"}})
        assert run_hook(read, tmp_path, url).returncode == 0
        relative = tool_use()
        relative.update({"tool_name": "Edit", "tool_input": {"file_path": "notes/from-x.md"}})
        assert run_hook(relative, tmp_path, url).returncode == 0
        assert board.wrote == ["/srv/d/from-x.md", None, None]
    finally:
        board.shutdown()
        board.server_close()
