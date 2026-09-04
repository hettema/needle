"""The session hook: queues on disk, drains to the board, never blocks and
never raises (plan 03, item 3). Run as the real script, against a small
HTTP server standing in for the board."""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tests.ratchets.paths import REPO

HOOK = REPO / "hooks" / "needle_hook.py"


class Board(HTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.posts: list[list[dict]] = []
        self.up = True


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


def test_the_hook_queues_while_the_board_is_down_and_drains_when_it_is_up(tmp_path: Path):
    board = Board()
    thread = threading.Thread(target=board.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{board.server_address[1]}"
    queue = tmp_path / "hook-queue.jsonl"
    try:
        board.up = False
        first = run_hook(
            {
                "hook_event_name": "Stop",
                "session_id": "aaaa0001-0000-4000-8000-000000000000",
                "cwd": "/srv/p/.claude/worktrees/card-7-x",
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
                "cwd": "/srv/p/.claude/worktrees/card-7-x",
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
