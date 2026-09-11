"""A full machine admits nothing new, and a lane that comes back is one lane
(plan 53), on the floor: the lane loop reads the machine on every pass and
each lane's scope beside it, a lane holding as much as the floor reads full
with its name on the head and the beat opens nothing until it shrinks (item
1); a background session with hands on a lane's worktree outside the lane's
scope is put back in it, once, with the card saying so, and a scope oomd
left failed is reset first (item 2)."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from domain.dial import MEMORY_FLOOR_BYTES
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import TIDE, board, number_of, tick, turn, verify
from tests.api.test_doors import detail, git, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

LANE = "card-241-the-deploy"
UNIT = f"needle-{LANE}.scope"
GB = 1024**3


def lane_241(repo: Path, machine_floor: Floor) -> str:
    """#241's lane: a real worktree with a live background session in it,
    whose process is this test's own — so its cgroup is whatever holds
    pytest, never the lane's scope, exactly the state a resumed session is
    in."""
    other = repo / ".claude" / "worktrees" / LANE
    git(repo, "worktree", "add", "-q", "-b", LANE, str(other))
    session_id = machine_floor.write_job(
        "beta", "beef0241", cwd=str(other), worktree=str(other), name=LANE
    )
    machine_floor.write_process("beta", session_id, os.getpid(), cwd=str(other))
    return session_id


def scope_reads(machine_floor: Floor) -> list[list[str]]:
    return [
        call
        for call in machine_floor.state()["systemctl_calls"]
        if call[:2] == ["--user", "show"] and "MemoryCurrent" in call
    ]


def test_the_machine_is_read_on_every_pass_and_a_lane_past_the_floor_admits_nothing(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    tide = number_of(client, TIDE)
    live = client.app.state.loops.live
    lane_241(repo, machine_floor)
    live.rescan("proj")
    reconcile(client)
    # The pass asks each machine what the board knew when it asked (card
    # #123): the lane is first seen on the pass above, and its group is
    # read by name from the next — a group nobody has put the lane in yet
    # holds nothing to read.
    reconcile(client)
    # The pass asked the user manager what the lane's scope holds, by the
    # name the lane was given at Start — one call, whether or not the dial
    # is on a beat.
    assert scope_reads(machine_floor)[-1] == [
        "--user",
        "show",
        "-p",
        "Id",
        "-p",
        "MemoryCurrent",
        UNIT,
    ]
    assert board(client)["dial"]["full"] is None, "a scope with no value is not a lane"
    read_so_far = len(scope_reads(machine_floor))
    turn(client, on=True, lanes=2)
    verify(client, machine_floor, tide)
    assert len(scope_reads(machine_floor)) > read_so_far, "every beat and pass reads the lanes"

    # The lane grows to the floor: the next pass — no beat — reads full and
    # names the lane, and the beat opens nothing while it stands.
    machine_floor.update(scopes={UNIT: {"MemoryCurrent": str(int(5.5 * GB))}})
    reconcile(client)
    grown = "the machine is full: proj #241's lane holds 5.5 GB, past the 5 GB floor"
    assert board(client)["dial"]["full"] == grown
    opened = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == opened, "nothing opened under the floor"
    waiting = {w["card_number"]: w["why"] for w in client.get("/api/fixes").json()["waiting"]}
    assert waiting[tide] == grown
    # Short memory names the biggest lane beside the numbers.
    machine_floor.update(scopes={UNIT: {"MemoryCurrent": str(int(1.2 * GB))}})
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    reconcile(client)
    assert board(client)["dial"]["full"] == (
        "the machine is full: 2.0 GB available, 5 GB needed; "
        "the biggest lane is proj #241's lane at 1.2 GB"
    )
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == opened
    # Room again: the pass reads it, and the beat plans the verified defect.
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    reconcile(client)
    assert board(client)["dial"]["full"] is None
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == opened + 1, "the beat opens again"
    assert machine_floor.state()["launch_log"][-1]["argv"][-1].startswith(
        "A plan to write for a defect the dial took"
    )
    # A reading the manager could not make is full, and says so; the floor
    # is the one constant and nothing raised it.
    machine_floor.update(systemctl_fails=True)
    reconcile(client)
    assert board(client)["dial"]["full"] == (
        "the machine is full: what its lanes hold could not be read"
    )
    assert board(client)["dial"]["full"] is not None


def test_a_session_with_hands_on_a_lane_is_put_back_in_its_scope_once_and_the_card_says_so(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    # The lane's scope lingers as failed after oomd's kill, as nine did on
    # this machine on 2026-09-07: the manager refuses a new scope under that
    # name until it is reset.
    machine_floor.update(scopes={UNIT: {"ActiveState": "failed", "LoadState": "loaded"}})
    live = client.app.state.loops.live
    session_id = lane_241(repo, machine_floor)
    live.rescan("proj")
    reconcile(client)
    calls = machine_floor.state()["systemctl_calls"]
    assert ["--user", "reset-failed", UNIT] in calls
    adopts = [c for c in machine_floor.state()["busctl_calls"] if UNIT in c]
    assert len(adopts) == 1 and str(os.getpid()) in adopts[0]
    # The lane's space is capped at the floor (card #107): one property
    # beside the pids, typed as the manager wants it.
    tail = adopts[0][adopts[0].index("MemoryHigh") :]
    assert tail[:3] == ["MemoryHigh", "t", str(MEMORY_FLOOR_BYTES)], adopts[0]
    rows = [
        h
        for h in detail(client, 241)["history"]
        if h["kind"] == "scoped" and h["detail"].startswith("Asked")
    ]
    assert len(rows) == 1
    assert rows[0]["detail"].startswith(
        f"Asked the machine to put beef0241 back in {UNIT} from "
    ), rows[0]["detail"]
    assert rows[0]["actor"] == "machine"
    record = store.session_slot(session_id)
    assert record is not None and (record.card, record.scope) == (LANE, UNIT)
    assert machine_floor.state()["scopes"][UNIT]["ActiveState"] == "inactive", "reset first"
    # Once per session: the next passes ask nothing again and add no row.
    reconcile(client)
    reconcile(client)
    assert len([c for c in machine_floor.state()["busctl_calls"] if UNIT in c]) == 1
    scoped = [h for h in detail(client, 241)["history"] if h["kind"] == "scoped"]
    assert len([h for h in scoped if h["detail"].startswith("Asked")]) == 1
    # The scope the fake manager holds stood without the floor as its high
    # mark (card #107): set once through the manager, said once, and read
    # as held on every pass after.
    sets = [c for c in machine_floor.state()["systemctl_calls"] if "set-property" in c]
    assert sets == [
        ["--user", "set-property", "--runtime", UNIT, f"MemoryHigh={MEMORY_FLOOR_BYTES}"]
    ]
    assert len([h for h in scoped if h["detail"].startswith(f"Held {UNIT} at 5 GB (the high mark")]) == 1
    assert machine_floor.state()["scopes"][UNIT]["MemoryHigh"] == str(MEMORY_FLOOR_BYTES)


def test_one_scope_that_refuses_the_floors_mark_does_not_cost_the_others_theirs(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """Codex's reading of the live-read fix (card #107): one scope whose set
    fails must not drop the mark, or the note, of the others in the pass."""
    other = f"needle-{doors.LANE}.scope"
    machine_floor.update(
        scopes={
            UNIT: {"ActiveState": "active", "LoadState": "loaded"},
            other: {"ActiveState": "active", "LoadState": "loaded"},
        },
        setprop_refuses=[UNIT],
    )
    lane_241(repo, machine_floor)
    doors.start(client)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    sets = [c[3] for c in machine_floor.state()["systemctl_calls"] if "set-property" in c]
    assert set(sets) == {UNIT, other}, sets
    assert sets.count(other) == 1, "set once, then read as held"
    assert sets.count(UNIT) >= 1, "the refusing scope is asked again on every pass"
    scopes = machine_floor.state()["scopes"]
    assert scopes[other]["MemoryHigh"] == str(MEMORY_FLOOR_BYTES)
    assert "MemoryHigh" not in scopes[UNIT], "the refusing scope keeps what it had"
    held = [h for h in detail(client)["history"] if h["detail"].startswith(f"Held {other} ")]
    assert len(held) == 1, "the scope that was set is answered"
    assert not [h for h in detail(client, 241)["history"] if h["detail"].startswith("Held ")]


def test_a_move_the_machine_refused_is_said_once_on_the_card(
    client: TestClient, machine_floor: Floor, repo: Path
):
    machine_floor.update(busctl_fails=True)
    live = client.app.state.loops.live
    lane_241(repo, machine_floor)
    live.rescan("proj")
    reconcile(client)
    reconcile(client)
    rows = [h for h in detail(client, 241)["history"] if h["kind"] == "scoped"]
    assert len(rows) == 1
    assert rows[0]["detail"].startswith(f"Could not put beef0241 back in {UNIT} from ")
    assert rows[0]["detail"].endswith("Unit already exists")
