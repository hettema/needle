"""Work the laptop interrupted comes back by itself, and the board says
truly how it ended (plan 68, item 6): one case per cause on the floor.

A lane the machine ended — its memory taken, the account's daemon space
killed under it, the laptop gone down, an allowance run out, the connection
back — is brought back by the lane loop through the gate Start passes, once
per cause within the horizon, and a second death of one cause parks it with
the end the board reads: the machine's memory held above the floor for a
beat, the allowance's reset, the rule finding room, the hour's count. A
lane that closed, asked the owner, or ended for a reason nothing names is
left where it fell, and the card says which. The board's memory of all of it
is the store, so a fresh loop over a parked board writes nothing new.
"""

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import loops as loops_mod
from api.cli import main
from domain.ending import Cause
from infrastructure import clock
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.attention import claim_count
from tests.api.test_doors import (
    CARD,
    LANE,
    archive_plan,
    column_of,
    detail,
    lane_path,
    post_hook,
    reconcile,
    start,
)
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

LANE_UNIT = f"needle-{LANE}.scope"
DAEMON_UNIT = "claude-daemon-alpha.scope"
ATTEMPT_1 = "Attempt 1 for this cause in the last hour; one is made per hour, then it waits."


def stamp(at: datetime | None = None) -> str:
    return (at or datetime.now(UTC)).isoformat()


def kill(machine_floor: Floor, launched: dict) -> None:
    """The process goes away and its /proc record with it: what the
    registry reads after an oom-kill or a boot."""
    os.kill(launched["pid"], 9)
    (Path(launched["config_dir"]) / "sessions" / f"{launched['pid']}.json").unlink()


def oom(machine_floor: Floor, unit: str = LANE_UNIT, at: datetime | None = None) -> None:
    machine_floor.write_journal(
        unit,
        f"{stamp(at)} DH systemd[919]: {unit}: systemd-oomd killed 12 process(es) in this unit.",
        f"{stamp(at)} DH systemd[919]: {unit}: Failed with result 'oom-kill'.",
    )


def rescued(client: TestClient) -> list[str]:
    return [h["detail"] for h in detail(client)["history"] if h["kind"] == "rescued"]


def launches(machine_floor: Floor) -> list[dict]:
    return machine_floor.state()["launch_log"]


def hold_clock(monkeypatch, at: datetime) -> None:
    monkeypatch.setattr(clock, "now", lambda: at)


def begun(client: TestClient, machine_floor: Floor) -> dict:
    """A lane with hands on, sighted once by the loop, and the pass its Start
    asked for already run (card #123): a test that stages a kill after this
    stages it after the board last saw the lane alive, as a real kill is."""
    start(client)
    reconcile(client)
    doors.settle(client)
    return launches(machine_floor)[0]


# ── the machine's hand: resumed through the gate ───────────────────────


def test_a_lane_whose_memory_was_taken_waits_on_the_floor_and_comes_back_once_it_holds(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    launched = begun(client, machine_floor)
    oom(machine_floor)
    kill(machine_floor, launched)
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=1.0)
    reconcile(client)

    parked = detail(client)
    assert parked["summary"]["lane_state"] == "ended"
    assert parked["lane"]["cause"] == Cause.LANE_KILLED.value
    assert parked["lane"]["park"] is not None, rescued(client)
    assert (
        "the machine is full: 2.0 GB available, 1.0 GB swap free, 5 GB needed"
        in (parked["lane"]["park"])
    )
    assert parked["lane"]["park"].endswith("then it comes back by itself")
    assert parked["summary"]["state"]["word"] == "coming back"
    assert parked["summary"]["state"]["meaning"] == "quiet"
    assert parked["lane"]["sentence"].startswith("Nothing for you: the session on it ended ")
    assert (
        " ago and the board brings it back by itself. The machine took back its memory at "
        in parked["lane"]["sentence"]
    )
    assert column_of(client, CARD) == "Up next"
    board = client.get("/api/projects/proj/board").json()
    assert claim_count(board, "lane ended") == 0, "a parked lane is the machine's, not a death"
    assert len(launches(machine_floor)) == 1
    assert [r for r in rescued(client) if r.startswith("Waiting to bring it back")]

    # Room comes back: the park waits one whole beat with the floor held.
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    reconcile(client)
    assert len(launches(machine_floor)) == 1, "the floor has to hold for a beat first"
    later = clock.now() + timedelta(seconds=loops_mod.FLOOR_SECONDS + 1)
    hold_clock(monkeypatch, later)
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    words = rescued(client)
    assert any(
        w.startswith("The wait ended: the machine's memory has held above the floor") for w in words
    )
    assert any(w.startswith("Brought back after the machine took back its memory") for w in words)
    assert column_of(client, CARD) == "Executing"
    assert detail(client)["lane"]["park"] is None


def test_a_session_killed_with_its_daemon_space_names_that_kill_and_not_the_lanes_older_one(
    client: TestClient, machine_floor: Floor
):
    """#435's second ending on 2026-09-05: the lane space's kill took its
    first life, the daemon space's kill its second, and the board cited
    the first."""
    launched = begun(client, machine_floor)
    oom(machine_floor, LANE_UNIT, at=datetime.now(UTC) - timedelta(hours=2))
    oom(machine_floor, DAEMON_UNIT)
    kill(machine_floor, launched)
    reconcile(client)

    words = rescued(client)
    assert len(words) == 1 and words[0].startswith(
        "Brought back after the machine took back its account's memory at "
    ), words
    assert DAEMON_UNIT in words[0] and LANE_UNIT not in words[0]
    assert column_of(client, CARD) == "Executing"


def test_a_life_from_a_previous_boot_is_the_boots_and_comes_back_with_the_boots_words(
    client: TestClient, machine_floor: Floor, store: Store
):
    """#85's four lanes: the lid closed at 18:51, the board said they had
    finished their turn, and the resume told them a subscription ran out."""
    now = datetime.now(UTC)
    machine_floor.write_boots(
        (0, "boot-a", stamp(now - timedelta(hours=3)), stamp(now + timedelta(hours=1)))
    )
    launched = begun(client, machine_floor)
    seen = store.sighting(launched["session_id"])
    assert seen is not None and seen.boot_id == "boot-a"
    kill(machine_floor, launched)
    machine_floor.write_boots(
        (
            -1,
            "boot-a",
            stamp(now - timedelta(hours=3)),
            stamp(seen.last_seen + timedelta(seconds=9)),
        ),
        (
            0,
            "boot-b",
            stamp(seen.last_seen + timedelta(minutes=4)),
            stamp(now + timedelta(hours=1)),
        ),
    )
    reconcile(client)

    words = rescued(client)
    assert len(words) == 1 and words[0].startswith("Brought back after the laptop went down: "), (
        words
    )
    assert "it came back at" in words[0] and "and the session was alive at" in words[0]
    told = launches(machine_floor)[1]["argv"][-1]
    assert told.startswith(
        "Continue where you stopped. Your last turn was cut: the laptop went down: "
    )
    assert "read your worktree and the card before trusting your memory" in told
    assert "subscription" not in told
    assert column_of(client, CARD) == "Executing"


def test_a_recovery_handoff_on_a_surviving_process_is_the_connection_never_a_wall(
    client: TestClient, machine_floor: Floor
):
    launched = begun(client, machine_floor)
    machine_floor.write_handoff(
        launched["session_id"],
        at=time.time(),
        **{"from": "alpha"},
        account="alpha",
        pid=launched["pid"],
        reason="server_error",
        why="connection back after a transient death",
        prompt="[claude-acct] Your last turn ended on: server_error. The connection is back.",
    )
    reconcile(client)

    words = rescued(client)
    assert len(words) == 1 and words[0].startswith(
        "Brought back after the connection came back on alpha (server_error): now "
    ), words
    assert "allowance" not in words[0] and "limit" not in words[0]
    told = launches(machine_floor)[1]["argv"][-1]
    assert told.startswith("[claude-acct] Your last turn ended on: server_error")
    assert column_of(client, CARD) == "Executing"


def test_the_moving_face_reads_the_cause_the_handoff_carries(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    launched = begun(client, machine_floor)
    # A handoff the loop is forbidden to act on this pass shows the face
    # mid-move; refusing the rule is the simplest hold.
    machine_floor.write_handoff(
        launched["session_id"],
        at=time.time(),
        **{"from": "alpha"},
        account="nowhere",
        pid=launched["pid"],
        reason="server_error",
        why="connection back after a transient death",
    )
    reconcile(client)
    moving = detail(client)["lane"]
    assert moving["state"] == "moving", rescued(client)
    assert moving["sentence"].startswith(
        "Happening now: the session on it stopped on a dropped connection and the connection is "
        "back; it is being put back to work on nowhere."
    )


def test_a_walled_lane_on_a_full_machine_gives_its_memory_back_and_comes_back_on_the_handoffs_rung(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    """Card #107: the walled process is stopped in the pass that parks it,
    the ending reads as the wall (the handoff stands), and the lane comes
    back on the account the wall chose once the room has held for a beat."""
    launched = begun(client, machine_floor)
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=1.0)
    wall = dict(
        **{"from": "alpha"},
        account="beta",
        pid=launched["pid"],
        reason="You've hit your session limit · resets 4:40pm",
    )
    machine_floor.write_handoff(launched["session_id"], at=time.time(), **wall)
    reconcile(client)

    assert len(launches(machine_floor)) == 1, "parked, not launched"
    assert _gone(launched["pid"]), "the walled process is gone in the same pass"
    words = rescued(client)  # newest first: the park is written, then the stop follows it
    assert words[0].startswith("Stopped "), words
    assert "to give its memory back while it waits for room" in words[0], words
    assert words[1].startswith("Waiting to bring it back after its allowance ran out on alpha"), (
        words
    )
    assert "the machine is full: 2.0 GB available, 1.0 GB swap free, 5 GB needed" in words[1]

    # The next pass names the ending from the standing handoff, and waits on.
    reconcile(client)
    parked = detail(client)
    assert parked["lane"]["state"] == "ended"
    assert parked["lane"]["cause"] == Cause.WALL.value, parked["lane"]
    assert parked["lane"]["park"] is not None
    assert parked["summary"]["state"]["word"] == "coming back"
    assert len(launches(machine_floor)) == 1
    assert len(rescued(client)) == len(words), "nothing said twice"

    # Room holds for a beat: relaunched on the rung the wall chose.
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    reconcile(client)
    assert len(launches(machine_floor)) == 1, "the floor has to hold for a beat first"
    # The floor's hold is an hour on the test floor (`quick`) and the rescue
    # horizon is an hour too, so the wall is re-stamped to stay young past
    # the hold; the file's other words are unchanged.
    held = clock.now() + timedelta(seconds=loops_mod.FLOOR_SECONDS + 1)
    machine_floor.write_handoff(
        launched["session_id"], at=(held - timedelta(minutes=5)).timestamp(), **wall
    )
    hold_clock(monkeypatch, held)
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    assert launches(machine_floor)[1]["config_dir"] == str(machine_floor.config_dir("beta"))
    lifted = rescued(client)
    held = "The wait ended: the machine's memory has held above the floor"
    assert any(w.startswith(held) for w in lifted)
    assert any(w.startswith("Brought back after its allowance ran out on alpha") for w in lifted)
    assert column_of(client, CARD) == "Executing"


def test_a_lane_parked_on_the_floor_before_this_rule_has_its_process_stopped_next_pass(
    client: TestClient, machine_floor: Floor, store: Store
):
    """The six real lanes of 2026-09-09 were parked with their processes
    standing; a park that already stands is where the stop has to happen."""
    launched = begun(client, machine_floor)
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=1.0)
    machine_floor.write_handoff(
        launched["session_id"],
        at=time.time(),
        **{"from": "alpha"},
        account="beta",
        pid=launched["pid"],
        reason="You've hit your session limit · resets 4:40pm",
    )
    store.open_park(
        "proj",
        CARD,
        session_id=launched["session_id"],
        cause=Cause.WALL,
        words="it waits: the machine is full; then it comes back by itself",
        waits_on="floor",
        until=None,
        held_since=None,
        at=clock.now(),
    )
    reconcile(client)
    assert _gone(launched["pid"]), "stopped on the first pass that finds the standing park"
    words = rescued(client)
    assert words[0].startswith("Stopped ") and "to give its memory back" in words[0], words
    reconcile(client)
    assert len(rescued(client)) == len(words), "said once"
    assert len(launches(machine_floor)) == 1


@pytest.mark.parametrize("reset_known", [True, False])
def test_a_walled_lane_that_waited_asks_the_rule_when_its_rung_has_since_run_out(
    client: TestClient, machine_floor: Floor, monkeypatch, reset_known: bool
):
    """Codex's reading of card #107's first pass: a handoff younger than the
    horizon named a rung the lane might wait past. The account's own latest
    reading decides, and an allowance spent with no time for its return is
    not read as back."""
    launched = begun(client, machine_floor)
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=1.0)
    wall = dict(**{"from": "alpha"}, account="beta", pid=launched["pid"], reason="a limit")
    machine_floor.write_handoff(launched["session_id"], at=time.time(), **wall)
    reconcile(client)
    reconcile(client)
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    reconcile(client)
    held = clock.now() + timedelta(seconds=loops_mod.FLOOR_SECONDS + 1)
    machine_floor.write_handoff(
        launched["session_id"], at=(held - timedelta(minutes=5)).timestamp(), **wall
    )
    machine_floor.write_limits(
        "beta",
        spent={"Session (5-hour)": 1.0},
        resets={"Session (5-hour)": (held + timedelta(hours=2)).isoformat()} if reset_known else {},
        fetched_at=held.timestamp(),
    )
    hold_clock(monkeypatch, held)
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    assert launches(machine_floor)[1]["config_dir"] == str(machine_floor.config_dir("alpha")), (
        "beta's own reading says its allowance is gone, so the rule placed it"
    )


def test_the_owners_stop_on_a_walled_session_removes_the_machines_request_to_move_it(
    client: TestClient, machine_floor: Floor
):
    """A standing handoff would name the ending a wall and bring the lane
    back; the owner's stop is his, so the request goes with it."""
    launched = begun(client, machine_floor)
    path = machine_floor.write_handoff(
        launched["session_id"],
        at=time.time(),
        **{"from": "alpha"},
        account="nowhere",
        pid=launched["pid"],
        reason="a limit",
    )
    reconcile(client)
    assert detail(client)["lane"]["state"] == "moving"
    assert main(["stop", launched["short"]]) == 0
    assert not path.exists(), "the owner's stop took the handoff with it"
    reconcile(client)
    assert detail(client)["lane"]["state"] == "ended"
    assert detail(client)["lane"]["park"] is None
    assert len(launches(machine_floor)) == 1


def test_the_owners_stop_after_the_boards_own_floor_stop_keeps_the_lane_down(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    """The board's stop on the floor names the ending a wall; the owner's stop
    afterwards is written over it, so room coming back brings nothing."""
    launched = begun(client, machine_floor)
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=1.0)
    machine_floor.write_handoff(
        launched["session_id"],
        at=time.time(),
        **{"from": "alpha"},
        account="beta",
        pid=launched["pid"],
        reason="a limit",
    )
    reconcile(client)
    reconcile(client)
    assert detail(client)["lane"]["cause"] == Cause.WALL.value
    assert main(["stop", launched["short"]]) == 0
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    reconcile(client)
    hold_clock(monkeypatch, clock.now() + timedelta(seconds=loops_mod.FLOOR_SECONDS + 1))
    reconcile(client)
    reconcile(client)
    assert len(launches(machine_floor)) == 1, "the owner's stop stands"
    lane = detail(client)["lane"]
    assert lane["cause"] == Cause.STOPPED.value and lane["park"] is None


def _gone(pid: int) -> bool:
    return not Path(f"/proc/{pid}/status").exists() or _zombie(pid)


def _zombie(pid: int) -> bool:
    try:
        return "Z" in Path(f"/proc/{pid}/status").read_text().split("State:")[1].split()[0]
    except (OSError, IndexError):
        return True


# ── the allowance: a park with an end ──────────────────────────────────


def test_a_second_wall_within_the_hour_parks_until_the_reset_and_the_park_lifts_at_it(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    launched = begun(client, machine_floor)
    machine_floor.write_handoff(
        launched["session_id"],
        **{"from": "alpha"},
        account="beta",
        pid=launched["pid"],
        at=time.time(),
    )
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    moved = launches(machine_floor)[1]
    reset = datetime.now(UTC) + timedelta(hours=2)
    machine_floor.write_limits(
        "beta",
        spent={"Session (5-hour)": 1.0, "Fable Weekly": 0.4},
        resets={"Session (5-hour)": reset.isoformat()},
        fetched_at=datetime.now(UTC).timestamp(),
    )
    machine_floor.write_handoff(
        moved["session_id"],
        at=time.time(),
        **{"from": "beta"},
        account="alpha",
        pid=moved["pid"],
        reason="You've hit your session limit · resets soon",
    )
    reconcile(client)

    assert len(launches(machine_floor)) == 2, "parked, not thrashed"
    parked = detail(client)
    words = rescued(client)
    assert words[0].startswith("Waiting to bring it back after its allowance ran out on beta"), (
        words
    )
    assert "tried once already in the last hour after its allowance ran out" in words[0]
    assert "or an account has room sooner" not in words[0], "the clock alone lifts a repeat"
    assert f"Session (5-hour) on beta comes back at {reset.strftime('%Y-%m-%d %H:%MZ')}" in words[0]
    assert parked["lane"]["state"] == "moving", "the process still stands while it waits"
    reconcile(client)
    assert len(rescued(client)) == len(words), "the park note lands once"

    hold_clock(monkeypatch, reset + timedelta(seconds=1))
    reconcile(client)
    assert len(launches(machine_floor)) == 3
    lifted = rescued(client)
    assert any(w.startswith("The wait ended: the wait ran to its end at ") for w in lifted)
    assert lifted[0].startswith("Brought back after its allowance ran out on beta")


def test_a_wall_with_no_destination_parks_from_the_walls_record_and_lifts_when_the_rule_finds_room(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """`claude-acct` writes no handoff when no account has room; the only
    trace is the session's own stop-failure event."""
    launched = begun(client, machine_floor)
    state_file = machine_floor.config_dir("alpha") / "jobs" / launched["short"] / "state.json"
    state = state_file.read_text()
    state_file.write_text(state.replace('"state": "working"', '"state": "blocked"'))
    reset = datetime.now(UTC) + timedelta(hours=3)
    machine_floor.write_limits(
        "alpha",
        spent={"Session (5-hour)": 1.0},
        resets={"Session (5-hour)": reset.isoformat()},
        fetched_at=datetime.now(UTC).timestamp(),
    )
    machine_floor.refuse_best("no account with headroom")
    post_hook(
        client,
        "StopFailure",
        launched["session_id"],
        lane_path(repo),
        error="rate_limit",
        message="You've hit your limit · resets 9:30pm (Europe/Stockholm)",
    )

    parked = detail(client)
    words = rescued(client)
    assert len(launches(machine_floor)) == 1
    assert words[0].startswith(
        "Waiting to bring it back after its allowance ran out on alpha (You've hit your limit · "
        "resets 9:30pm (Europe/Stockholm)): "
    ), words
    assert (
        f"Session (5-hour) on alpha comes back at {reset.strftime('%Y-%m-%d %H:%MZ')}" in words[0]
    )
    assert "no account has room to run it" in words[0]
    assert parked["lane"]["state"] == "blocked"

    machine_floor.answer_best("beta")
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    lifted = rescued(client)
    assert any(w.startswith("The wait ended: the rule found room on beta") for w in lifted)
    assert lifted[0].startswith("Brought back after its allowance ran out on alpha")
    assert detail(client)["lane"]["session"]["slot"] == "beta"


def test_twice_the_same_cause_within_the_hour_parks_on_the_clock_and_a_fresh_loop_writes_nothing(
    client: TestClient, machine_floor: Floor, monkeypatch
):
    launched = begun(client, machine_floor)
    oom(machine_floor)
    kill(machine_floor, launched)
    reconcile(client)
    assert len(launches(machine_floor)) == 2
    second = launches(machine_floor)[1]
    reconcile(client)  # the replacement is sighted
    oom(machine_floor)
    kill(machine_floor, second)
    reconcile(client)

    assert len(launches(machine_floor)) == 2, "a second death of one cause parks"
    words = rescued(client)
    assert words[0].startswith("Waiting to bring it back after the machine took back its memory")
    assert (
        "the board tried once already in the last hour" in words[0] and "it came back" in words[0]
    )
    assert "one attempt is made per hour, so it waits until" in words[0]
    park = detail(client)["lane"]["park"]
    assert park is not None and "so it waits until" in park

    # A fresh loop over the parked store — a `needle` command, a restarted
    # server — says nothing new (item 2).
    before = len(detail(client)["history"])
    loops_mod.Loops(client.app.state.loops.live, client.app.state.loops.runtime).reconcile_now()
    assert len(detail(client)["history"]) == before
    reconcile(client)
    assert len(detail(client)["history"]) == before

    hold_clock(monkeypatch, clock.now() + timedelta(seconds=loops_mod.RESCUE_HORIZON_SECONDS + 5))
    reconcile(client)
    assert len(launches(machine_floor)) == 3
    assert rescued(client)[0].startswith("Brought back after the machine took back its memory")


def test_a_server_that_died_between_the_launch_and_its_record_finds_the_replacement(
    client: TestClient, machine_floor: Floor, store: Store, repo: Path
):
    launched = begun(client, machine_floor)
    oom(machine_floor)
    kill(machine_floor, launched)
    # The row a launch is preceded by, left open: the server died after
    # `claude --bg` registered the replacement and before the record.
    store.open_recovery(
        "proj",
        CARD,
        session_id=launched["session_id"],
        cause=Cause.LANE_KILLED,
        words="the machine took back its memory",
        at=clock.now(),
    )
    replacement = machine_floor.write_job(
        "alpha",
        "beef0002",
        cwd=lane_path(repo),
        worktree=lane_path(repo),
        name=LANE,
        resumed_from=launched["session_id"],
    )
    machine_floor.write_process("alpha", replacement, os.getpid(), cwd=lane_path(repo))
    reconcile(client)

    assert len(launches(machine_floor)) == 1, "one interruption, one replacement"
    rows = store.recoveries("proj", CARD)
    assert len(rows) == 1 and rows[0].verdict == "found" and rows[0].replacement == replacement
    words = rescued(client)
    assert len(words) == 1 and words[0].startswith("Found beef0002 on alpha already brought back")
    assert detail(client)["summary"]["lane_state"] == "working"


# ── left where it fell ─────────────────────────────────────────────────


def test_a_closed_card_with_no_fold_record_is_finished_and_nothing_resumes(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """The eight Hello Revenue lanes the board called "finished its turn,
    open the card to start again" on 2026-09-08 had all closed their
    cards; their lanes were older than the lane records."""
    launched = begun(client, machine_floor)
    archive_plan(repo)
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "the meter bills",
                "--watch",
                "the plan is archived — file docs/plans/done by 2026-12-31 every 1h",
            ]
        )
        == 0
    )
    capsys.readouterr()
    client.app.state.loops.live.rescan("proj")
    # A session that stood down because another owned the close is read
    # against that card's close, not its own last words (#147, #219, #238).
    post_hook(
        client,
        "Stop",
        launched["session_id"],
        lane_path(repo),
        message="Standing down: the other lane owns this close. Shall I keep the worktree?",
    )
    oom(machine_floor)
    kill(machine_floor, launched)
    reconcile(client)

    assert len(launches(machine_floor)) == 1
    assert rescued(client) == []
    assert store.deaths("proj") == {}, "a finished lane gets no death sentence"
    ended = detail(client)["lane"]
    assert ended["state"] == "ended" and ended["died"] is None and ended["park"] is None
    assert ended["sentence"].startswith(
        "Nothing for you: its close landed and the session on it ended "
    )
    assert column_of(client, CARD) == "Executed"


def test_an_ending_nothing_names_is_shown_unresolved_and_never_resumed(
    client: TestClient, machine_floor: Floor
):
    launched = begun(client, machine_floor)
    kill(machine_floor, launched)
    reconcile(client)

    assert len(launches(machine_floor)) == 1
    dead = detail(client)
    assert dead["lane"]["cause"] == Cause.UNKNOWN.value
    assert dead["lane"]["died"].startswith("the process disappeared after its last activity at ")
    assert dead["lane"]["died"].endswith("; the cause is not established")
    assert dead["summary"]["state"]["word"] == "session died"
    assert dead["doors"]["resume"]["offered"], "the owner's Resume stays"
    assert column_of(client, CARD) == "Up next"
    assert rescued(client) == []


def test_a_lane_that_put_a_decision_to_the_owner_is_his_even_when_the_machine_killed_it(
    client: TestClient, machine_floor: Floor, repo: Path
):
    launched = begun(client, machine_floor)
    post_hook(
        client,
        "Stop",
        launched["session_id"],
        lane_path(repo),
        message="Two readings disagree on the tariff. Nothing can move until you rule.",
    )
    oom(machine_floor)
    kill(machine_floor, launched)
    reconcile(client)

    assert len(launches(machine_floor)) == 1
    dead = detail(client)["lane"]
    assert dead["cause"] == Cause.LANE_KILLED.value, "the death is still named truly"
    assert dead["park"] is None and rescued(client) == []
    assert dead["sentence"].startswith("Your move: decide what it asked and bring it back. ")
    assert "Nothing can move until you rule." in dead["sentence"]


def test_a_handoff_naming_a_finished_lane_expires(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    launched = begun(client, machine_floor)
    archive_plan(repo)
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "d",
                "--watch",
                "the plan is archived — file docs/plans/done by 2026-12-31 every 1h",
            ]
        )
        == 0
    )
    capsys.readouterr()
    client.app.state.loops.live.rescan("proj")
    path = machine_floor.write_handoff(
        launched["session_id"],
        **{"from": "alpha"},
        account="beta",
        pid=launched["pid"],
        at=time.time(),
    )
    reconcile(client)

    assert not path.exists(), "a handoff naming finished work is consumed unacted"
    assert len(launches(machine_floor)) == 1
    words = rescued(client)
    assert len(words) == 1 and words[0].startswith(
        f"A request to move {launched['short']} expired unacted: the work is closed"
    )


def test_a_parked_lanes_fresh_room_read_hands_the_wire_only_the_busy_cards_names(
    client: TestClient, machine_floor, repo: Path
):
    """The pass bounds the names it hands `room --owner` to the cards with
    hands on (E2BIG at 128 KB on the first live move); the park's own
    fresh read handed every card's names until 2026-09-10 evening, so
    Hello Revenue #503, parked on the rented machine with 30 GB free, read
    its room as unreadable for twenty-five minutes and never came back.
    Both reads hand the same bounded names."""
    loops = client.app.state.loops
    start(client)
    reconcile(client)
    handed: list[dict] = []
    real = loops.runtime.rooms

    def rooms(**kwargs):
        handed.append(kwargs)
        return real(**kwargs)

    # A card the board once had a lane for, with no hands on it now: the
    # name an unbounded read would hand the wire and a bounded one never.
    names = dict(loops._names())
    names["needle-card-999-long-gone.scope"] = ("proj", 999)
    loops.runtime.rooms = rooms
    all_names = loops._names
    loops._names = lambda: names
    try:
        loops.headroom_now()
        loops._room_of(loops.runtime.here().name)
    finally:
        loops.runtime.rooms = real
        loops._names = all_names
    assert len(handed) == 2
    busy = set(loops._owners().values())
    assert busy, "the started lane has hands on"
    for kwargs in handed:
        assert set(kwargs["owners"].values()) <= busy
        assert "needle-card-999-long-gone.scope" not in kwargs["owners"]
        assert kwargs["read"] == set(loops._owners())
    assert handed[0]["owners"] == handed[1]["owners"]
