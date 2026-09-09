"""A card that finishes or needs you rings, once, and the record says what
you were told (Needle #41, items 2 and 3).

On the floor: a lane that folds and closes rings as the card enters
Executed; one that dies rings with the machine's reason; the owner's own
Stop rings nothing, though the machine writes the exit down; the same exit
reconciled twice rings once, and a ring owed by the record and never made
is made at the next reconcile; a Stop hook whose last message ends on a
question rings with that line once the grace has passed, and a stop that
becomes an exit inside the grace is one ring, the exit's.
"""

import json
import os
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from api import loops as loops_mod
from api.cli import main
from domain.notice import Told
from infrastructure import clock
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, LANE, archive_plan, column_of, detail, lane_path, post_hook, reconcile, start
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


@pytest.fixture
def travel(monkeypatch: pytest.MonkeyPatch):
    """The board's clock, moved by hand: the grace is a minute nobody wants
    a test to spend."""
    held = {"now": clock.now()}
    monkeypatch.setattr(clock, "now", lambda: held["now"])

    def forward(seconds: float) -> None:
        held["now"] = held["now"] + timedelta(seconds=seconds)

    return forward


def rings(floor: Floor, count: int, seconds: float = 5.0) -> list[list[str]]:
    """The notifier's argv, once the shells the loop never waits on have run."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        found = floor.state().get("notified", [])
        if len(found) >= count:
            return found
        time.sleep(0.05)
    return floor.state().get("notified", [])


def told_rows(client: TestClient) -> list[str]:
    return [h["detail"] for h in detail(client)["history"] if h["kind"] == "told"]


def kill_lane(floor: Floor, launched: dict) -> None:
    os.kill(launched["pid"], 9)
    (floor.config_dir("alpha") / "sessions" / f"{launched['pid']}.json").unlink()


def test_a_lane_that_folds_and_closes_rings_once_as_the_card_enters_executed(
    client: TestClient, machine_floor: Floor, repo
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    assert main(["row", "proj", str(CARD), "DELIVERED", "the meter bills"]) == 0
    done = archive_plan(repo)
    watch = f"the plan is archived — file {done.relative_to(repo)} by 2026-12-31"
    assert main(["row", "proj", str(CARD), "WATCH", watch]) == 0
    kill_lane(machine_floor, launched)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert column_of(client, CARD) == "Executed"

    (argv,) = rings(machine_floor, 1)
    assert argv[:8] == [
        "-u", "critical", "-t", "0", "-a", "notify-send", "-A", "default=Open the board"
    ]
    assert argv[8] == "Needle · Harbourmaster #253: Every metered kilowatt is billed"
    assert argv[9] == (
        "Moved Executing → Executed — the close landed: the plan is archived and DELIVERED is written"
    )
    assert machine_floor.state()["played"] == [
        ["/usr/share/sounds/freedesktop/stereo/complete.oga"]
    ]
    assert told_rows(client) == [
        "Told you (moved on): Moved Executing → Executed — the close landed: the plan is archived and "
        "DELIVERED is written"
    ]
    # The button runs `needle show` for this card, from the server's own environment.
    shell = machine_floor.state()["notified"]
    assert len(shell) == 1
    assert loops_mod.show_command("proj", CARD)[-3:] == ["show", "proj", "253"]

    # The same exit, reconciled again: nothing more rings.
    reconcile(client)
    reconcile(client)
    time.sleep(0.3)
    assert len(machine_floor.state()["notified"]) == 1
    assert len(told_rows(client)) == 1


def test_a_ring_the_record_owes_is_made_at_the_next_reconcile_and_a_failed_one_is_one_row(
    client: TestClient, machine_floor: Floor, monkeypatch: pytest.MonkeyPatch
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    runtime = client.app.state.loops.runtime
    real_tell = runtime.tell

    # A crash between the move and the ring: the move landed, no `told` row
    # follows it, and the next reconcile rings.
    def crash(notice, opens):
        raise RuntimeError("the board died here")

    monkeypatch.setattr(runtime, "tell", crash)
    kill_lane(machine_floor, launched)
    reconcile(client)
    assert column_of(client, CARD) == "Up next"
    assert told_rows(client) == [] and machine_floor.state()["notified"] == []

    monkeypatch.setattr(runtime, "tell", real_tell)
    reconcile(client)
    (argv,) = rings(machine_floor, 1)
    assert argv[9].startswith("Moved Executing → Up next — the lane ended with nothing folded")
    assert len(told_rows(client)) == 1

    # A notifier that could not be reached: one row saying why, one warning,
    # and never a ring every thirty seconds for the same exit.
    monkeypatch.setattr(
        runtime, "tell", lambda notice, opens: Told(raised=False, words="could not tell you: no")
    )
    client.post(f"/api/projects/proj/cards/{CARD}/resume")
    assert column_of(client, CARD) == "Executing"
    resumed = machine_floor.state()["launch_log"][-1]
    kill_lane(machine_floor, resumed)
    reconcile(client)
    assert column_of(client, CARD) == "Up next"
    assert told_rows(client)[0] == "Could not tell you: no"
    monkeypatch.setattr(runtime, "tell", real_tell)
    reconcile(client)
    time.sleep(0.3)
    assert len(machine_floor.state()["notified"]) == 1
    assert len(told_rows(client)) == 2


def test_a_lane_killed_by_the_machine_rings_the_reason_once(
    client: TestClient, machine_floor: Floor
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    machine_floor.update(
        journal={
            f"needle-{LANE}.scope": [
                "claude[4242]: Killed process 4242 (claude) total-vm:9GB oom-kill",
            ]
        }
    )
    kill_lane(machine_floor, launched)
    reconcile(client)
    assert column_of(client, CARD) == "Up next"
    (argv,) = rings(machine_floor, 1)
    assert argv[9].startswith("Moved Executing → Up next — the lane ended with nothing folded (")
    assert "Killed process 4242 (claude)" in argv[9]
    reconcile(client)
    time.sleep(0.3)
    assert len(machine_floor.state()["notified"]) == 1


def test_the_owners_own_stop_rings_nothing_though_the_machine_writes_the_exit(
    client: TestClient, machine_floor: Floor
):
    start(client)
    stopped = client.post(f"/api/projects/proj/cards/{CARD}/stop")
    assert stopped.status_code == 200, stopped.text
    assert column_of(client, CARD) == "Up next"
    history = detail(client)["history"]
    assert any(
        h["actor"] == "machine" and h["kind"] == "moved" and "nothing folded" in h["detail"]
        for h in history
    )
    reconcile(client)
    time.sleep(0.3)
    assert machine_floor.state()["notified"] == []
    assert told_rows(client) == []


def test_a_question_rings_once_with_its_last_line_after_the_grace(
    client: TestClient, machine_floor: Floor, repo, travel
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    session_id, short = launched["session_id"], launched["short"]
    state_file = machine_floor.config_dir("alpha") / "jobs" / short / "state.json"
    state = json.loads(state_file.read_text())
    state["state"] = "done"
    state_file.write_text(json.dumps(state))
    post_hook(
        client,
        "Stop",
        session_id,
        lane_path(repo),
        message="The parser is in.\n\nShould the gate default to high or medium?",
    )
    assert detail(client)["summary"]["lane_state"] == "asking"
    time.sleep(0.3)
    assert machine_floor.state()["notified"] == [], "inside the grace: a stop may become an exit"

    travel(loops_mod.TELL_GRACE_SECONDS + 5)
    reconcile(client)
    (argv,) = rings(machine_floor, 1)
    assert argv[9] == "Asking you: Should the gate default to high or medium?"
    assert machine_floor.state()["played"] == [
        ["/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"]
    ]
    assert told_rows(client) == [
        "Told you (needs you): Asking you: Should the gate default to high or medium?"
    ]

    # The same question, seen again: nothing.
    travel(30)
    reconcile(client)
    time.sleep(0.3)
    assert len(machine_floor.state()["notified"]) == 1

    # A new question is a new ring.
    post_hook(
        client,
        "Stop",
        session_id,
        lane_path(repo),
        message="Parsed.\n\nAnd the effort: xhigh?",
    )
    travel(loops_mod.TELL_GRACE_SECONDS + 5)
    reconcile(client)
    found = rings(machine_floor, 2)
    assert found[1][9] == "Asking you: And the effort: xhigh?"


def test_a_stop_that_becomes_an_exit_inside_the_grace_is_one_ring_the_exits(
    client: TestClient, machine_floor: Floor, repo, travel
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    session_id, short = launched["session_id"], launched["short"]
    state_file = machine_floor.config_dir("alpha") / "jobs" / short / "state.json"
    state = json.loads(state_file.read_text())
    state["state"] = "done"
    state_file.write_text(json.dumps(state))
    post_hook(client, "Stop", session_id, lane_path(repo), message="Done here. Merge it?")
    assert detail(client)["summary"]["lane_state"] == "asking"
    travel(10)
    kill_lane(machine_floor, launched)
    post_hook(client, "SessionEnd", session_id, lane_path(repo), reason="prompt_input_exit")
    reconcile(client)
    assert column_of(client, CARD) == "Up next"
    (argv,) = rings(machine_floor, 1)
    assert argv[9].startswith("Moved Executing → Up next — the lane ended with nothing folded")

    travel(loops_mod.TELL_GRACE_SECONDS + 5)
    reconcile(client)
    time.sleep(0.3)
    assert len(machine_floor.state()["notified"]) == 1, "the question never rings: it ended"
    assert len(told_rows(client)) == 1
