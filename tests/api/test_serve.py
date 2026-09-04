"""`needle serve` is a process a supervisor can stop (plan 01b, item 2).

The server is started for real, as a subprocess, with a stream held open the
way the page holds one; SIGTERM must end it within two seconds, exit 0, with
the stream closed. Before the fix it never ended: uvicorn drained connections
without a deadline and the stream waited on a board change that never came.
"""

import http.client
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from domain.project import Project
from infrastructure.store import Store
from tests.conftest import NOW
from tests.ratchets.paths import REPO

DEADLINE_SECONDS = 2.0


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(port: int, process: subprocess.Popen[bytes]) -> None:
    for _ in range(200):
        if process.poll() is not None:
            raise AssertionError(f"the server exited early with {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("the server never listened")


def test_serve_stops_within_two_seconds_of_sigterm_with_a_stream_open(tmp_path: Path, corpus: Path):
    database = tmp_path / "needle.db"
    store = Store(database)
    store.add_project(
        Project(slug="proj", name="Harbourmaster", path=str(corpus), registered_at=NOW)
    )
    store.close()

    port = free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "api.cli", "serve", "--port", str(port)],
        cwd=REPO,
        env={**os.environ, "NEEDLE_DB": str(database)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_port(port, process)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/api/projects/proj/stream")
        stream = connection.getresponse()
        assert stream.status == 200
        assert stream.readline().startswith(b"event: board")

        sent_at = time.monotonic()
        process.send_signal(signal.SIGTERM)
        try:
            code = process.wait(timeout=DEADLINE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            raise AssertionError(
                f"still running {DEADLINE_SECONDS}s after SIGTERM with a stream open"
            ) from None
        took = time.monotonic() - sent_at
        assert code == 0, f"exited {code} after {took:.2f}s"
        # The stream was closed by the server, not left for the client to time out on.
        stream.read()
        assert stream.closed or stream.isclosed()
        connection.close()
    finally:
        if process.poll() is None:
            process.kill()
        output = process.communicate()[0].decode(errors="replace")
        assert "Traceback" not in output, output
