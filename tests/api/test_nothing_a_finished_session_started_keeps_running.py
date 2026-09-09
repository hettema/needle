"""Nothing a finished session started keeps running (Needle #99).

Every lane's and reading's session runs in a process group of its own, and
on 2026-09-09 three groups stood a day after their sessions had ended,
holding forty abandoned wait loops that spawned a `sleep` every few
seconds while the laptop paged, and a fourth held a `uvicorn` a reading
had left. The beat now reads every group of ours and ends the ones nobody
is home in; `needle scopes` is the same reading from the terminal, and the
loop's reader.
"""

import json
import os
import signal
import subprocess
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from infrastructure import clock
from runtime import launch
from tests.api import test_doors as doors
from tests.api.test_doors import LANE, detail, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


@pytest.fixture
def travel(monkeypatch: pytest.MonkeyPatch):
    """The board's clock, moved by hand: the sweep waits a window of real
    seconds nobody wants a test to spend."""
    held = {"now": clock.now()}
    monkeypatch.setattr(clock, "now", lambda: held["now"])

    def forward(seconds: float) -> None:
        held["now"] += timedelta(seconds=seconds)

    return forward


def _gone(pid: int) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"{pid} did not die")


def _count(capsys) -> str:
    assert main(["scopes", "--stray", "--count"]) == 0
    return capsys.readouterr().out.strip()


def _stopped_rows(client: TestClient) -> list[str]:
    return [h["detail"] for h in detail(client)["history"] if h["kind"] == "stopped"]


def _lane(client: TestClient, machine_floor: Floor):
    doors.start(client)
    short = machine_floor.state()["launch_log"][0]["short"]
    runtime = client.app.state.loops.runtime
    session = next(s for s in runtime.sessions() if s.short_id == short)
    assert session.pid is not None
    return short, session


def test_a_group_nobody_is_home_in_is_ended_after_a_window_and_the_card_says_so_once_it_is_empty(
    client: TestClient, machine_floor: Floor, repo, capsys, travel
):
    """Item 1: a lane's session ends by a kill — no door, no hook — and its
    group still holds a process the session started. Reads inside the
    window leave it; the first read past the window asks the manager to
    end it; the read that finds the group empty writes the row with the
    count; nothing is asked twice. In the same machine the live lane's
    group, an empty group, the daemon's group, and the group of a session
    whose turn is done but whose process stands are never touched. Item
    2: `needle scopes` lists the group as nobody home before the sweep
    and counts none after."""
    short, session = _lane(client, machine_floor)
    unit = launch.lane_unit(LANE)
    stray = subprocess.Popen(["sleep", "300"])
    other = subprocess.Popen(["sleep", "300"])
    machine_floor.pids += [stray.pid, other.pid]
    try:
        machine_floor.write_scope(unit, [session.pid, stray.pid])
        machine_floor.write_scope(launch.lane_unit("card-9-just-started"), [])
        machine_floor.write_scope("claude-daemon-alpha.scope", [other.pid])
        reconcile(client)
        travel(31)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == []
        assert _count(capsys) == "0"
        assert main(["scopes"]) == 0
        listed = capsys.readouterr().out
        assert f"{unit}  {short}  2 processes (sleep 300)" in listed
        assert "card-9-just-started" in listed and "claude-daemon" not in listed

        # Its turn is done and its process stands: resumable, so its own.
        state_file = machine_floor.config_dir("alpha") / "jobs" / short / "state.json"
        state = json.loads(state_file.read_text())
        state["state"] = "done"
        state_file.write_text(json.dumps(state))
        reconcile(client)
        travel(31)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == []
        assert detail(client)["summary"]["lane_state"] == "stopped"

        # The process is killed: nothing told the board, and the group
        # keeps what the session left behind.
        os.kill(session.pid, signal.SIGKILL)
        _gone(session.pid)
        machine_floor.write_scope(unit, [stray.pid])
        assert _count(capsys) == "1"
        assert main(["scopes", "--stray"]) == 0
        assert capsys.readouterr().out.strip() == f"{unit}  nobody home  1 process (sleep 300)"

        reconcile(client)
        travel(10)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [], "reads inside the window are doubts"
        travel(21)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [unit]
        assert _stopped_rows(client) == [], (
            "the card is told when the group is empty, not when asked"
        )
        reconcile(client)
        assert _stopped_rows(client) == [
            f"Stopped what a finished session left in {unit}: 1 process nobody owned "
            "(sleep 300); nothing a finished session started keeps running."
        ]
        assert detail(client)["summary"]["lane_state"] == "ended"
        travel(31)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [unit], "nothing is asked twice"
        assert len(_stopped_rows(client)) == 1
        assert _count(capsys) == "0"
        assert main(["scopes", "--stray"]) == 0
        assert capsys.readouterr().out.strip() == "no group nobody is home in"
    finally:
        for left in (stray, other):
            left.kill()
            left.wait()


def test_a_refused_stop_is_said_once_in_words_that_claim_nothing_and_asked_again(
    client: TestClient, machine_floor: Floor, repo, travel
):
    """The manager refuses: the card hears it once, in words that claim no
    stop, and the beat asks again after another window — and says so when
    the group is finally empty."""
    _, session = _lane(client, machine_floor)
    unit = launch.lane_unit(LANE)
    stray = subprocess.Popen(["sleep", "300"])
    machine_floor.pids.append(stray.pid)
    try:
        os.kill(session.pid, signal.SIGKILL)
        _gone(session.pid)
        machine_floor.write_scope(unit, [stray.pid])
        machine_floor.update(stop_refuses=[unit])
        reconcile(client)
        travel(31)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == []
        refused = (
            f"Asked the machine to end what a finished session left in {unit}: 1 process "
            f"nobody owned (sleep 300); it refused: Failed to stop {unit}: Access denied. "
            "The beat asks again."
        )
        assert _stopped_rows(client) == [refused]
        reconcile(client)
        travel(31)
        reconcile(client)
        assert _stopped_rows(client) == [refused], "a refusal is said once"
        asked = [c for c in machine_floor.state()["systemctl_calls"] if "stop" in c]
        assert len(asked) == 2, "and asked again after another window"

        machine_floor.update(stop_refuses=[])
        travel(31)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [unit]
        reconcile(client)
        rows = _stopped_rows(client)
        assert len(rows) == 2 and any(
            r.startswith(f"Stopped what a finished session left in {unit}: 1 process nobody owned")
            for r in rows
        )
    finally:
        stray.kill()
        stray.wait()


def test_a_group_whose_card_still_has_a_live_session_is_left_alone(
    client: TestClient, machine_floor: Floor, repo, travel
):
    """The second guard: the registry knows a live session for the card,
    and its pid is not in the group this instant — a session being put
    back into its group after a move. A whole window with nobody home,
    and still no stop, because the card's session lives."""
    _, session = _lane(client, machine_floor)
    unit = launch.lane_unit(LANE)
    stray = subprocess.Popen(["sleep", "300"])
    machine_floor.pids.append(stray.pid)
    try:
        machine_floor.write_scope(unit, [stray.pid])
        for _ in range(3):
            reconcile(client)
            travel(31)
        assert machine_floor.state()["scope_stops"] == []
        assert session.pid is not None and detail(client)["summary"]["lane_state"] == "working"
    finally:
        stray.kill()
        stray.wait()
