"""Nothing a finished session started keeps running (Needle #99).

Every lane's and reading's session runs in a process group of its own, and
on 2026-09-09 three groups stood a day after their sessions had ended,
holding forty abandoned wait loops that spawned a `sleep` every few
seconds while the laptop paged. The beat now reads every group of ours
and stops the ones nobody is home in; `needle scopes` is the same reading
from the terminal, and the loop's reader.
"""

import os
import signal
import subprocess
import time

from fastapi.testclient import TestClient

from api.cli import main
from runtime import launch
from tests.api import test_doors as doors
from tests.api.test_doors import LANE, detail, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


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


def test_a_group_nobody_is_home_in_is_stopped_on_the_second_read_and_the_card_says_so(
    client: TestClient, machine_floor: Floor, repo, capsys
):
    """Item 1: a lane's session ends by a kill — no door, no hook — and its
    group still holds a process the session started. The first read notes
    it, the second stops the group through the runtime and the card says
    what was stopped and how many; a third finds the manager no longer
    holds it and stops nothing again. In the same machine, the live lane's
    group, an empty group and the daemon's group are never touched. Item
    2: `needle scopes` lists the group as nobody home before the sweep and
    counts none after."""
    doors.start(client)
    short = machine_floor.state()["launch_log"][0]["short"]
    runtime = client.app.state.loops.runtime
    session = next(s for s in runtime.sessions() if s.short_id == short)
    assert session.pid is not None
    unit = launch.lane_unit(LANE)

    stray = subprocess.Popen(["sleep", "300"])
    other = subprocess.Popen(["sleep", "300"])
    machine_floor.pids += [stray.pid, other.pid]
    try:
        # The lane's group with its session home, an empty group a Start
        # has just made, and the daemon's group, which is not ours.
        machine_floor.write_scope(unit, [session.pid, stray.pid])
        machine_floor.write_scope(launch.lane_unit("card-9-just-started"), [])
        machine_floor.write_scope("claude-daemon-alpha.scope", [other.pid])
        reconcile(client)
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == []
        assert _count(capsys) == "0"
        assert main(["scopes"]) == 0
        listed = capsys.readouterr().out
        assert f"{unit}  {short}  2 processes (sleep 300)" in listed
        assert "card-9-just-started" in listed and "claude-daemon" not in listed

        # The session is killed: nothing told the board, and the group
        # keeps what the session left behind.
        os.kill(session.pid, signal.SIGKILL)
        _gone(session.pid)
        machine_floor.write_scope(unit, [stray.pid])
        assert _count(capsys) == "1"
        assert main(["scopes", "--stray"]) == 0
        assert capsys.readouterr().out.strip() == f"{unit}  nobody home  1 process (sleep 300)"

        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [], "one read is a doubt, not a stop"
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [unit]
        opened = detail(client)
        assert opened["summary"]["lane_state"] == "ended"
        row = next(h for h in opened["history"] if h["kind"] == "stopped")
        assert row["actor"] == "machine"
        assert row["detail"] == (
            f"Stopped what a finished session left in {unit}: 1 process nobody owned "
            "(sleep 300); nothing a finished session started keeps running."
        )
        # The manager no longer holds the unit: nothing is stopped twice,
        # and the reader counts none.
        reconcile(client)
        assert machine_floor.state()["scope_stops"] == [unit]
        assert _count(capsys) == "0"
        assert main(["scopes", "--stray"]) == 0
        assert capsys.readouterr().out.strip() == "no group nobody is home in"
    finally:
        for left in (stray, other):
            left.kill()
            left.wait()


def test_a_group_whose_card_still_has_a_live_session_is_left_alone(
    client: TestClient, machine_floor: Floor, repo
):
    """The second guard: the registry knows a live session for the card,
    and its pid is not in the group this instant — a session being put
    back into its group after a move. Two reads with nobody home, and
    still no stop, because the card's session lives."""
    doors.start(client)
    short = machine_floor.state()["launch_log"][0]["short"]
    runtime = client.app.state.loops.runtime
    session = next(s for s in runtime.sessions() if s.short_id == short)
    unit = launch.lane_unit(LANE)
    stray = subprocess.Popen(["sleep", "300"])
    machine_floor.pids.append(stray.pid)
    try:
        machine_floor.write_scope(unit, [stray.pid])
        for _ in range(3):
            reconcile(client)
        assert machine_floor.state()["scope_stops"] == []
        assert session.pid is not None and detail(client)["summary"]["lane_state"] == "working"
    finally:
        stray.kill()
        stray.wait()
