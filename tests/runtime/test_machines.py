"""The work runs where the horsepower is (card #83, item 4): a second machine
on the floor, reached by the fake `ssh`, and the rule that places work.

The other machine is a second floor under the first's root; its `needle`
is the venv's own script run there by the stand-in `ssh` with that floor's
environment, so every verb the board asks over the wire runs the real code
against the real typed edge, and only the transport is a fake.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from api.cli import main
from board.dial import who_is_home
from board.lane import driver
from domain.dial import Headroom, ScopeHeld
from domain.ending import Cause, Death
from domain.gate import Gate
from domain.launch import LaunchVerdict, Start
from domain.machine import Machine, MachineRoom, choose_machine
from domain.session import Session, SessionKind, SessionSlot, SessionState
from domain.slot import Make, Placement
from domain.window import WindowKind
from infrastructure.store import Store, StoreRefusal
from runtime import launch, windows
from runtime.service import Runtime
from tests.floor import Floor

NOW = datetime(2026, 9, 9, 20, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    monkeypatch.setattr(windows, "WINDOW_VERIFY_SECONDS", 1.5)
    monkeypatch.setenv("NEEDLE_DB", str(tmp_path / "board.db"))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    return root


@pytest.fixture
def ground(tmp_path: Path) -> Path:
    """The laptop's own record: a card in it runs on the laptop, whatever
    the rooms say."""
    root = tmp_path / "laptop-record"
    (root / ".git").mkdir(parents=True)
    return root


def _machine(name: str, **fields: object) -> Machine:
    base: dict[str, object] = {
        "name": name,
        "machine_id": f"id-{name}",
        "host": None,
        "desktop": False,
        "ground": None,
        "command": "needle",
        "added_at": NOW,
    }
    base.update(fields)
    return Machine.model_validate(base)


def _room(available_gb: float, *, full: bool = False, sentence: str | None = None) -> Headroom:
    return Headroom(
        available=int(available_gb * 1024**3),
        swap_free=8 * 1024**3,
        floor=5 * 1024**3,
        full=full,
        sentence=sentence,
        read_at=NOW,
        total=32 * 1024**3,
    )


def _reading(
    machine: Machine, room: Headroom | None, *, here: bool = False, why=None
) -> MachineRoom:
    return MachineRoom(machine=machine, here=here, room=room, why=why, high_water=None, killed=0)


# ── the rule, pure ────────────────────────────────────────────────────


def test_a_card_in_a_machines_own_record_runs_on_that_machine_or_nowhere():
    laptop = _machine("laptop", desktop=True, ground="/home/x/laptop-record")
    rented = _machine("rented", host="rented")
    chosen, why = choose_machine(
        [_reading(laptop, _room(9.0), here=True), _reading(rented, _room(24.0))],
        "/home/x/laptop-record",
    )
    assert chosen is laptop and "records" in why
    # Its ground full is #53's refusal with that machine's numbers, never a
    # move to the machine with room (Codex's reading, pass 2).
    full = _room(1.0, full=True, sentence="the machine is full: 1.0 GB available, 5 GB needed")
    chosen, why = choose_machine(
        [_reading(laptop, full, here=True), _reading(rented, _room(24.0))], "/home/x/laptop-record"
    )
    assert chosen is None and "1.0 GB available, 5 GB needed" in why and "nowhere else" in why


def test_the_one_machine_a_board_knows_places_as_before_and_its_start_rechecks_the_floor(
    machine_floor: Floor, store: Store, repo: Path
):
    only = _machine("DH", desktop=True)
    full = _room(2.0, full=True, sentence="the machine is full: 2.0 GB available, 5 GB needed")
    chosen, why = choose_machine([_reading(only, full, here=True)], "/p")
    assert chosen is only, "the door and the start refuse a full machine in their own words"
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    started = Runtime(store).start(
        Start(repo=str(repo), card="card-2-full", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.DEAD
    assert started.reason == "the machine is full: 2.0 GB available, 5 GB needed"


def test_every_other_card_runs_on_the_horsepower_with_room_then_the_desktop_then_nowhere():
    laptop = _machine("laptop", desktop=True)
    rented = _machine("rented", host="rented")
    full = _room(2.0, full=True, sentence="the machine is full: 2.0 GB available, 5 GB needed")

    chosen, why = choose_machine(
        [_reading(laptop, _room(9.0), here=True), _reading(rented, _room(24.0))], "/p"
    )
    assert chosen is rented and "horsepower" in why

    chosen, why = choose_machine(
        [_reading(laptop, _room(9.0), here=True), _reading(rented, full)], "/p"
    )
    assert chosen is laptop and "desktop" in why

    chosen, why = choose_machine(
        [_reading(laptop, full, here=True), _reading(rented, None, why="rented did not answer")],
        "/p",
    )
    assert chosen is None
    assert "rented did not answer" in why and "2.0 GB available, 5 GB needed" in why


def test_a_board_that_knows_one_machine_places_as_it_always_has():
    only = _machine("DH", desktop=True)
    chosen, why = choose_machine([_reading(only, None, here=True)], "/p")
    assert chosen is only and "one machine" in why


# ── the store ─────────────────────────────────────────────────────────


def test_a_machine_is_one_row_and_its_marks_are_kept_per_day(store: Store):
    store.add_machine(_machine("laptop", desktop=True))
    with pytest.raises(StoreRefusal, match="already on the board"):
        store.add_machine(_machine("laptop"))
    with pytest.raises(StoreRefusal, match="already on the board as 'laptop'"):
        store.add_machine(_machine("twin", machine_id="id-laptop"))

    gb = 1024**3
    assert store.note_high_water("laptop", available=9 * gb, total=16 * gb, at=NOW)
    assert not store.note_high_water("laptop", available=10 * gb, total=16 * gb, at=NOW)
    assert store.note_high_water(
        "laptop", available=3 * gb, total=16 * gb, at=NOW + timedelta(hours=1)
    )
    assert store.note_high_water(
        "laptop", available=8 * gb, total=16 * gb, at=NOW + timedelta(days=1)
    )
    mark = store.high_water("laptop")
    assert mark is not None and mark.used == 13 * gb and mark.day == NOW.date()
    later = store.high_water("laptop", since=NOW + timedelta(days=1))
    assert later is not None and later.used == 8 * gb
    assert [m.day for m in store.high_waters("laptop")] == [
        NOW.date(),
        (NOW + timedelta(days=1)).date(),
    ]
    assert store.remove_machine("laptop") and not store.remove_machine("laptop")


def test_a_kill_is_counted_against_the_machine_the_session_ran_on(store: Store):
    def death(session_id: str, cause: Cause) -> Death:
        return Death(
            session_id=session_id,
            project="p",
            card_number=1,
            cause=cause,
            words=cause.value,
            evidence="oomd",
            last_alive_at=NOW - timedelta(hours=2),
            named_at=NOW - timedelta(hours=1),
            settled=True,
        )

    store.record_death(death("s-rented", Cause.LANE_KILLED))
    store.record_death(death("s-laptop", Cause.DAEMON_KILLED))
    store.record_death(death("s-old", Cause.LANE_KILLED))
    store.record_death(death("s-wall", Cause.WALL))
    store.record_session_slot(
        SessionSlot(
            session_id="s-rented", slot="a", card="c", scope="u", recorded_at=NOW, machine="rented"
        )
    )
    since = NOW - timedelta(days=1)
    assert [d.session_id for d in store.killed_on("rented", since=since, here="laptop")] == [
        "s-rented"
    ]
    # A record with no machine is the board's own machine's.
    assert sorted(d.session_id for d in store.killed_on("laptop", since=since, here="laptop")) == [
        "s-laptop",
        "s-old",
    ]
    assert store.killed_on("laptop", since=NOW, here="laptop") == []


# ── the runtime, over the wire ────────────────────────────────────────


@pytest.fixture
def two_machines(machine_floor: Floor, store: Store, ground: Path) -> tuple[Runtime, Floor]:
    """This floor as the laptop (the desktop, the ground of the laptop's
    record), and a second floor as the rented machine with more room."""
    machine_floor.set_memory(available_gb=9.0, swap_free_gb=8.0)
    other = machine_floor.lay_host("rented", available_gb=24.0)
    store.add_machine(
        Machine(
            name="laptop",
            machine_id=machine_floor.machine_id,
            host=None,
            desktop=True,
            ground=str(ground),
            command="needle",
            added_at=NOW,
        )
    )
    store.add_machine(
        Machine(
            name="rented",
            machine_id=other.machine_id,
            host="rented",
            desktop=False,
            ground=None,
            command="needle",
            added_at=NOW,
        )
    )
    return Runtime(store), other


def test_the_board_reads_every_machines_room_and_the_head_names_each(two_machines):
    runtime, _ = two_machines
    rooms = runtime.rooms()
    by_name = {r.machine.name: r for r in rooms}
    assert by_name["laptop"].here and not by_name["rented"].here
    assert by_name["laptop"].room is not None and by_name["laptop"].room.available == 9 * 1024**3
    assert by_name["rented"].room is not None and by_name["rented"].room.available == 24 * 1024**3
    assert by_name["rented"].room.total == 32 * 1024**3


def test_a_queue_holding_an_event_older_than_an_hour_is_counted_on_the_machines_line(
    two_machines, machine_floor: Floor
):
    """Card #124, item 3: the hook's queue in each machine's data folder is
    the trace — empty when the board answers, growing when it does not —
    and an event still there after an hour is counted on that machine's
    line, on either machine, through the same room read; an empty queue
    and a fresh event count nothing. The queue is where the hook writes it,
    not beside the store, which the floor lays elsewhere (Codex's pass 2,
    finding 1); a queue that could not be read, and a machine whose older
    needle answers without the count, are said as not read and never as
    zero (finding 2)."""
    import time

    from api.runtime_cli import describe_room

    runtime, other = two_machines
    assert machine_floor.data_dir != Path(os.environ["NEEDLE_DB"]).parent
    old, fresh = time.time() - 2 * 3600, time.time() - 60
    (machine_floor.data_dir / "hook-queue.jsonl").write_text(
        f'{{"at": {old}, "session_id": "s1"}}\n{{"at": {fresh}, "session_id": "s2"}}\nnot json\n'
    )
    (other.data_dir / "hook-queue.jsonl").write_text("")
    by_name = {r.machine.name: r for r in runtime.rooms()}
    assert by_name["laptop"].room is not None and by_name["laptop"].room.stale_queue == 1
    assert by_name["rented"].room is not None and by_name["rented"].room.stale_queue == 0
    assert "; 1 queued over an hour — the board did not answer" in describe_room(by_name["laptop"])
    assert "queue" not in describe_room(by_name["rented"])
    (other.data_dir / "hook-queue.jsonl").write_text(f'{{"at": {old}, "session_id": "s3"}}\n')
    rented = next(r for r in runtime.rooms() if r.machine.name == "rented")
    assert rented.room is not None and rented.room.stale_queue == 1

    (machine_floor.data_dir / "hook-queue.jsonl").unlink()
    (machine_floor.data_dir / "hook-queue.jsonl").mkdir()
    laptop = next(r for r in runtime.rooms() if r.machine.name == "laptop")
    assert laptop.room is not None and laptop.room.stale_queue is None
    assert "; its queue of session messages was not read" in describe_room(laptop)
    older = Headroom.model_validate(laptop.room.model_dump(mode="json", exclude={"stale_queue"}))
    assert older.stale_queue is None

    # A write the hook was cut off in leaves half a character at the end;
    # the whole lines still count and the room is read (call 95, 2.2).
    (machine_floor.data_dir / "hook-queue.jsonl").rmdir()
    whole = f'{{"at": {old}, "session_id": "s4", "message": "déjà vu"}}\n'.encode()
    torn = '{"at": 1, "message": "é'.encode()[:-1]
    (machine_floor.data_dir / "hook-queue.jsonl").write_bytes(whole + torn)
    laptop = next(r for r in runtime.rooms() if r.machine.name == "laptop")
    assert laptop.room is not None and laptop.room.stale_queue == 1


def test_a_machine_that_does_not_answer_is_a_room_of_none_with_the_transports_words(
    two_machines, machine_floor: Floor
):
    runtime, _ = two_machines
    machine_floor.host_down("rented")
    rented = next(r for r in runtime.rooms() if r.machine.name == "rented")
    assert rented.room is None and rented.why is not None and "rented did not answer" in rented.why
    chosen, why = runtime.place("/p/other")
    assert chosen is not None and chosen.name == "laptop"


def test_where_picks_the_machine_by_ground_then_by_room_and_asks_that_machines_rule(
    two_machines, repo: Path, ground: Path, machine_floor: Floor
):
    runtime, _ = two_machines
    on_ground = runtime.where(None, [], repo=str(ground))
    assert on_ground.placement is not None and on_ground.placement.machine == "laptop"
    elsewhere = runtime.where(None, [], repo=str(repo))
    assert elsewhere.placement is not None and elsewhere.placement.machine == "rented"
    # The rule was asked on the other machine: its `claude-acct` answered,
    # through the fake `ssh`, and the answer is the same typed value.
    asked = [c for c in machine_floor.state()["ssh_calls"] if c["host"] == "rented"]
    assert any("where" in " ".join(c["words"]) for c in asked)
    assert elsewhere.placement.slot == "alpha"

    machine_floor.update(hosts={})  # nothing laid: rented unreachable, laptop has room
    fallen = runtime.where(None, [], repo=str(repo))
    assert fallen.placement is not None and fallen.placement.machine == "laptop"


def test_no_room_anywhere_is_refused_with_every_machines_numbers(
    two_machines, repo: Path, machine_floor: Floor
):
    runtime, other = two_machines
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    other.set_memory(available_gb=1.5, swap_free_gb=8.0)
    answer = runtime.where(None, [], repo=str(repo))
    assert answer.placement is None
    assert "laptop: the machine is full: 2.0 GB available, 5 GB needed" in answer.reason
    assert "rented: the machine is full: 1.5 GB available, 5 GB needed" in answer.reason
    started = runtime.start(
        Start(repo=str(repo), card="card-1-nowhere", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.DEAD and "no machine has room" in (started.reason or "")


def test_a_lane_started_from_here_runs_on_the_rented_machine_and_the_board_records_it(
    two_machines, repo: Path, machine_floor: Floor, store: Store
):
    runtime, other = two_machines
    started = runtime.start(
        Start(repo=str(repo), card="card-7-far-away", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.ALIVE, started.reason
    assert started.session is not None and started.placement is not None
    assert started.session.machine == "rented" and started.placement.machine == "rented"
    # The session registered on the other floor, not this one.
    assert (other.config_dir("alpha") / "jobs" / started.session.short_id).is_dir()
    assert not (machine_floor.config_dir("alpha") / "jobs" / started.session.short_id).exists()
    record = store.session_slot(started.session.session_id)
    assert record is not None and record.machine == "rented" and record.card == "card-7-far-away"

    # The one list carries it, stamped, beside this machine's rows.
    rows = {s.short_id: s for s in runtime.sessions()}
    assert rows[started.session.short_id].machine == "rented"
    assert rows[started.session.short_id].pid is not None

    # A window into it opens on the desktop, attached over the tunnel to
    # the multiplexer session on the other machine, and both prove it.
    opened = runtime.window(started.session.short_id, None)
    assert opened.window.kind == WindowKind.LANE
    command = machine_floor.state()["spawned"][-1]["command"][-1]
    assert command.startswith("exec ssh -t rented -- ")
    assert "tmux new-session -A -s needle-lane-card-7-far-away" in command
    assert f"claude attach {started.session.short_id}" in command
    # The multiplexer session exists on the rented machine, and only there.
    held = machine_floor.state()["tmux"]
    assert "needle-lane-card-7-far-away" in held[other.machine_id]
    assert "needle-lane-card-7-far-away" not in held.get(machine_floor.machine_id, {})

    # Stopping it goes through the other machine's runtime and is proven there.
    stopped = runtime.stop(started.session.short_id)
    assert stopped.gone
    assert all(s.pid is None for s in runtime.sessions() if s.short_id == started.session.short_id)


def test_a_card_in_the_laptops_own_record_runs_on_the_laptop(
    two_machines, ground: Path, machine_floor: Floor
):
    runtime, other = two_machines
    started = runtime.start(
        Start(repo=str(ground), card="card-3-mine", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.ALIVE, started.reason
    assert started.session is not None and started.session.machine == "laptop"
    assert (machine_floor.config_dir("alpha") / "jobs" / started.session.short_id).is_dir()
    assert not (other.config_dir("alpha") / "jobs").exists()
    # A window into a session on the desktop's own machine is a plain attach.
    opened = runtime.window(started.session.short_id, None)
    command = machine_floor.state()["spawned"][-1]["command"][-1]
    assert command.startswith("CLAUDE_CONFIG_DIR=") and "ssh" not in command
    assert opened.window.kind == WindowKind.LANE


# ── the verbs ─────────────────────────────────────────────────────────


def test_machine_add_reads_the_identity_from_the_machine_itself(
    machine_floor: Floor, ground: Path, capsys
):
    other = machine_floor.lay_host("rented")
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    out = capsys.readouterr().out
    assert "Registered laptop" in out and "this machine, the desktop" in out
    assert f"Registered rented ({other.machine_id[:8]}…), reached as rented" in out
    assert main(["machine", "add", "again", "--host", "rented"]) == 1
    assert "already on the board as 'rented'" in capsys.readouterr().err
    assert main(["machine", "add", "ghost", "--host", "nowhere"]) == 1
    assert "could not reach nowhere" in capsys.readouterr().err

    assert main(["machines"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("laptop (here)  desktop  ") and "0 killed today" in lines[0]
    assert lines[1].startswith("rented  horsepower  ") and "available" in lines[1]

    assert main(["machine", "rm", "rented"]) == 0
    assert main(["machine", "rm", "rented"]) == 1


def test_a_machine_with_a_live_session_or_no_answer_is_not_forgotten_from_the_command_line(
    machine_floor: Floor, repo: Path, capsys
):
    """The one list is the evidence (Codex's fifth pass): a reading has no
    worktree and a session older than a day may still run, so removal
    reads the sessions, not the records' age."""
    machine_floor.lay_host("rented", available_gb=24.0)
    assert main(["machine", "add", "laptop", "--desktop"]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    assert (
        main(["start", str(repo), "card-9-reading", "read it", "--effort", "high", "--windowless"])
        == 0
    )
    capsys.readouterr()
    assert main(["machine", "rm", "rented"]) == 1
    assert "still runs 1 session(s)" in capsys.readouterr().err
    machine_floor.host_down("rented")
    assert main(["machine", "rm", "rented"]) == 1
    assert "did not answer" in capsys.readouterr().err


def test_the_loops_readers_answer_from_the_command_line(machine_floor: Floor, capsys):
    assert main(["machine", "add", "laptop", "--desktop"]) == 0
    capsys.readouterr()
    assert main(["room"]) == 0
    assert "room: 16.0 GB available" in capsys.readouterr().out
    assert main(["where", "--high-water", "laptop"]) == 0
    assert "laptop: no memory reading yet" in capsys.readouterr().out
    store = Store(Path(__import__("os").environ["NEEDLE_DB"]))
    store.note_high_water("laptop", available=6 * 1024**3, total=16 * 1024**3, at=NOW)
    store.close()
    assert main(["where", "--high-water", "laptop"]) == 0
    assert "laptop: high-water 10.0 GB used of 16.0 GB on 2026-09-09" in capsys.readouterr().out
    assert main(["where", "--high-water", "moon"]) == 1
    assert main(["machine", "timing", "laptop", "pytest", "812.4"]) == 0
    assert "laptop: pytest 812.4 s, recorded" in capsys.readouterr().out


# ── the face ──────────────────────────────────────────────────────────


def test_the_start_preview_names_the_machine_only_when_the_placement_carries_one():
    placement = Placement(
        slot="alpha", make=Make.CLAUDE, model=None, config_dir="/x", why="room on alpha"
    )
    assert driver(placement) == "alpha"
    assert driver(placement.model_copy(update={"machine": "rented"})) == "alpha on rented"


def test_a_group_is_matched_to_a_session_on_its_own_machine_never_by_pid_alone():
    def session(machine: str, pid: int) -> Session:
        return Session(
            slot="alpha",
            config_dir="/x/alpha",
            short_id=f"s-{machine}",
            session_id=f"s-{machine}-0000",
            kind=SessionKind.BACKGROUND,
            name="card-1",
            cwd="/p",
            worktree=None,
            state=SessionState.WORKING,
            recorded="working",
            detail="",
            pid=pid,
            scope=None,
            model=None,
            effort=None,
            stale=False,
            wall=None,
            intent="",
            created_at=None,
            updated_at=None,
            resumed_from=None,
            doing=None,
            machine=machine,
        )

    laptop_group = ScopeHeld(
        unit="needle-card-1.scope",
        pids=[4242],
        commands={4242: "claude"},
        lineage={},
        machine="laptop",
    )
    rented_group = ScopeHeld(
        unit="needle-card-2.scope",
        pids=[4242],
        commands={4242: "sleep 9"},
        lineage={},
        machine="rented",
    )
    states = who_is_home([laptop_group, rented_group], [session("laptop", 4242)])
    assert [s.home for s in states] == [["s-laptop"], []]
    assert states[1].nobody_home and states[1].strangers == ["sleep 9"]
    assert [s.machine for s in states] == ["laptop", "rented"]


# ── the second pass's fixes (Codex's cold read, 2026-09-09) ──────────


def test_a_machine_that_stops_answering_leaves_its_sessions_unread_never_ended(
    two_machines, repo: Path, machine_floor: Floor
):
    runtime, _ = two_machines
    started = runtime.start(
        Start(repo=str(repo), card="card-8-unread", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.session is not None
    runtime.sessions()  # the pass that read it while it answered
    machine_floor.host_down("rented")
    rows = {s.short_id: s for s in runtime.sessions()}
    # The last rows read stand, stamped, with their process; and the
    # machine is named unread so nothing acts on an ending there.
    assert rows[started.session.short_id].pid is not None
    assert rows[started.session.short_id].machine == "rented"
    assert "rented" in runtime.unread and "did not answer" in runtime.unread["rented"]
    # No group of an unread machine is offered to the sweep.
    assert all(group.machine != "rented" for group in runtime.scopes() or [])
    machine_floor.host_down("rented", False)
    runtime.sessions()
    assert "rented" not in runtime.unread


def test_a_launch_whose_reply_never_came_is_unconfirmed_not_dead(
    two_machines, repo: Path, machine_floor: Floor, monkeypatch: pytest.MonkeyPatch
):
    from runtime import remote

    runtime, _ = two_machines
    monkeypatch.setattr(remote, "START_SECONDS", 0.5)
    hosts = machine_floor.state()["hosts"]
    hosts["rented"]["env"]["NEEDLE_FAKE_SLOW"] = "3"
    machine_floor.update(hosts=hosts)
    started = runtime.start(
        Start(repo=str(repo), card="card-9-slow", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.UNCONFIRMED
    assert started.reason is not None and "may have landed" in started.reason


def test_a_lanes_worktree_edits_tip_and_documents_are_read_where_the_lane_lives(
    two_machines, repo: Path, machine_floor: Floor, tmp_path: Path
):
    """The other machine's checkout is this one's, laid out the same, so the
    proof is the routing: every read of a lane placed on the rented machine
    goes over the wire, and a lane placed here does not."""
    from tests.api.test_doors import git

    runtime, _ = two_machines
    git(repo, "init", "-q", "-b", "develop")
    git(repo, "commit", "-q", "--allow-empty", "-m", "root")
    lane = repo / ".claude" / "worktrees" / "card-3-far"
    git(repo, "worktree", "add", "-q", "-b", "card-3-far", str(lane))
    (lane / "docs" / "plans").mkdir(parents=True)
    (lane / "docs" / "plans" / "p.md").write_text("# p\n\n### 1. one\nDone means: x.\n**Met:** y\n")
    (lane / "docs" / "reviews").mkdir()
    (lane / "docs" / "reviews" / "r.md").write_text("# r\n\n**Plan:** docs/plans/p.md\n")
    # Read as the board would: the rented machine answers for its worktrees
    # and the board remembers which machine each was seen on.
    found = runtime.worktrees(str(repo))
    assert str(lane) in found and found[str(lane)] == "card-3-far"
    runtime._lane_machines[str(lane)] = "rented"
    before = len(machine_floor.state()["ssh_calls"])
    assert "docs/" in runtime.edits(str(lane))
    tip = runtime.lane_tip(str(repo), "card-3-far", path=str(lane))
    assert tip.tip is not None and tip.birth is not None
    docs = runtime.lane_docs(str(lane), ["docs/plans/p.md"])
    assert docs.plan is not None and "**Met:** y" in docs.plan
    assert docs.reviews == [], "the review records are read only once every item is met"
    records = runtime.lane_docs(str(lane), [], reviews=True).reviews
    assert [r.path for r in records] == ["docs/reviews/r.md"]
    asked = [" ".join(c["words"]) for c in machine_floor.state()["ssh_calls"][before:]]
    assert any("edits" in a for a in asked) and any("tip" in a for a in asked)
    assert any("lane-docs" in a for a in asked)
    # A lane on this machine is read here, with no wire.
    runtime._lane_machines[str(lane)] = "laptop"
    count = len(machine_floor.state()["ssh_calls"])
    assert runtime.lane_docs(str(lane), ["docs/plans/p.md"]).plan is not None
    assert len(machine_floor.state()["ssh_calls"]) == count


def test_a_fresh_conversation_on_the_rented_machine_gets_its_own_multiplexer_session(
    two_machines, repo: Path, machine_floor: Floor
):
    runtime, other = two_machines
    first = runtime.discuss(repo=str(repo), card="card-4-talk", brief="hi", effort=None, what="#4")
    second = runtime.discuss(repo=str(repo), card="card-4-talk", brief="hi", effort=None, what="#4")
    held = machine_floor.state()["tmux"][other.machine_id]
    names = [n for n in held if n.startswith("needle-board-discuss-card-4-talk-")]
    assert len(names) == 2 and names[0] != names[1]
    assert first[1][:8] in names[0] and second[1][:8] in names[1]
    assert not any(h.get("attached") for h in held.values()), (
        "a fresh conversation never reattaches"
    )


def test_a_machine_with_work_on_it_is_not_forgotten(two_machines, repo: Path, store: Store):
    runtime, _ = two_machines
    started = runtime.start(
        Start(repo=str(repo), card="card-6-busy", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.session is not None and started.session.machine == "rented"
    from domain.lane import LaneRecord

    store.record_lane(
        LaneRecord(
            project="p",
            card_number=6,
            name="card-6-busy",
            path=f"{repo}/.claude/worktrees/card-6-busy",
            branch="card-6-busy",
            birth=None,
            tip=None,
            first_seen=NOW,
            last_seen=NOW,
            gone_at=None,
            folded_at=None,
            trunk_synced_at=None,
            main_synced_at=None,
            machine="rented",
        )
    )
    with pytest.raises(StoreRefusal, match="still holds the lane of p #6"):
        store.remove_machine("rented")
    # A lane gone from the machine still leaves the session started there
    # today: a reading has no worktree, and a lane's is read a pass later
    # than its start (Codex's fourth pass), so a day must pass first.
    store.record_lane(store.lanes("p")[0].model_copy(update={"gone_at": NOW}))
    with pytest.raises(StoreRefusal, match="had a session started on it in the last day"):
        store.remove_machine("rented")
    old = store.session_slot(started.session.session_id)
    assert old is not None
    store.record_session_slot(old.model_copy(update={"recorded_at": NOW - timedelta(days=2)}))
    assert store.remove_machine("rented")
    # A name the board does not know routes nowhere, never here.
    ghost = runtime.machine_named("moon")
    assert ghost.host is None and not runtime.is_here(ghost)
    assert runtime.boots("moon") == [] and runtime.limits("alpha", machine_name="moon") is None


def test_the_days_mark_only_ever_goes_down(store: Store):
    gb = 1024**3
    assert store.note_high_water("laptop", available=10 * gb, total=16 * gb, at=NOW)
    assert store.note_high_water("laptop", available=3 * gb, total=16 * gb, at=NOW)
    # A writer that read 10 before the 3 landed and now writes 7 cannot
    # raise the mark: the compare is the database's, not the reader's.
    assert not store.note_high_water("laptop", available=7 * gb, total=16 * gb, at=NOW)
    mark = store.high_water("laptop")
    assert mark is not None and mark.least_available == 3 * gb


def test_machines_json_carries_the_latest_timing_per_step(machine_floor: Floor, capsys):
    import json

    assert main(["machine", "add", "laptop", "--desktop"]) == 0
    assert main(["machine", "timing", "laptop", "pytest", "900"]) == 0
    assert main(["machine", "timing", "laptop", "pytest", "812.4"]) == 0
    assert main(["machine", "timing", "laptop", "vitest", "14.2"]) == 0
    capsys.readouterr()
    assert main(["machines", "--json"]) == 0
    rooms = json.loads(capsys.readouterr().out)
    timings = {t["what"]: t["seconds"] for t in rooms[0]["timings"]}
    assert timings == {"pytest": 812.4, "vitest": 14.2}


# ── the third pass's fixes (Codex's re-read, 2026-09-09) ─────────────


def test_a_colleague_on_another_machine_is_refused_by_name_and_nothing_runs_here(
    two_machines, repo: Path, machine_floor: Floor
):
    runtime, _ = two_machines
    started = runtime.start(
        Start(repo=str(repo), card="card-5-far", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.session is not None
    session = runtime.session(started.session.short_id)
    launched = len(machine_floor.state()["launch_log"])
    answer = runtime.call(session, brief="hello?", name="call-1", answer="/tmp/none")
    assert answer.verdict == LaunchVerdict.DEAD
    assert answer.reason is not None and "runs on rented" in answer.reason
    assert len(machine_floor.state()["launch_log"]) == launched, "the laptop's launcher was not run"


def test_a_planning_sessions_scope_is_named_as_such_on_the_head():
    from domain.dial import Meminfo, ScopeMemory, headroom

    room = headroom(
        Meminfo(available=9 * 1024**3, swap_total=0, swap_free=0, total=16 * 1024**3),
        5 * 1024**3,
        NOW,
        scopes=[
            ScopeMemory(
                unit="needle-planning-card-7-example.scope",
                held=6 * 1024**3,
                project="proj",
                card_number=7,
            )
        ],
    )
    assert room.full and room.sentence is not None
    assert "proj #7's planning session holds 6.0 GB" in room.sentence


def test_a_sighting_keeps_its_machine_up_to_date(store: Store):
    from domain.ending import Sighting

    def seen(machine: str) -> Sighting:
        return Sighting(
            session_id="s-1",
            project="p",
            card_number=1,
            pid=4242,
            scope=None,
            boot_id=None,
            first_seen=NOW,
            last_seen=NOW,
            machine=machine,
        )

    store.record_sighting(seen("laptop"))
    store.record_sighting(seen("rented"))
    found = store.sighting("s-1")
    assert found is not None and found.machine == "rented"


def test_the_loop_writes_no_sighting_and_reads_no_boot_for_an_unread_machine(
    machine_floor: Floor, repo: Path, ground: Path
):
    """The loop itself, over the CLI's store: a session on a machine that
    did not answer this pass leaves its sighting as it was, and a named
    machine with no boots read is unknown, never this machine's boot."""
    from api.board_cli import _board
    from domain.ending import Boot
    from domain.lane import Lane, LaneState

    other = machine_floor.lay_host("rented")
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    store, live, runtime, loops, _ = _board()
    try:
        runtime.unread["rented"] = "rented did not answer"
        session = Session(
            slot="alpha",
            config_dir=str(other.config_dir("alpha")),
            short_id="far00001",
            session_id="far00001-0000-4000-8000-000000000000",
            kind=SessionKind.BACKGROUND,
            name="card-1-far",
            cwd="/p",
            worktree=None,
            state=SessionState.WORKING,
            recorded="working",
            detail="",
            pid=4242,
            scope="needle-card-1-far.scope",
            model=None,
            effort=None,
            stale=False,
            wall=None,
            intent="",
            created_at=NOW,
            updated_at=NOW,
            resumed_from=None,
            doing=None,
            machine="rented",
        )
        lane = Lane(
            card_number=1,
            name="card-1-far",
            path="/p",
            state=LaneState.WORKING,
            sentence="",
            session=session,
            question=None,
            said=None,
            said_at=None,
            discussing=[],
            window_open=False,
            hands_on_since=NOW,
            died=None,
            moved=None,
            folded=False,
            trunk_synced=False,
            main_synced=False,
            edits=[],
            declared=[],
            colliding=None,
        )
        loops._sightings("p", {1: lane}, NOW)
        assert store.sighting(session.session_id) is None
        loops._boots = {
            "laptop": [
                Boot(index=0, boot_id="LAPTOP-BOOT", first_entry=NOW, last_entry=NOW),
            ]
        }
        assert loops._current_boot("rented") is None
        assert (
            loops._current_boot("") is not None and loops._current_boot("").boot_id == "LAPTOP-BOOT"
        )
    finally:
        store.close()


def test_the_heads_word_is_the_boards_full_only_when_no_machine_has_room(
    machine_floor: Floor, ground: Path
):
    from api.board_cli import _board

    other = machine_floor.lay_host("rented", available_gb=24.0)
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    store, live, runtime, loops, _ = _board()
    try:
        room = loops.headroom_now()
        assert not room.full and room.sentence is None, "the rented machine has room"
        assert live.headroom is not None and not live.headroom.full
        other.set_memory(available_gb=1.5, swap_free_gb=8.0)
        room = loops.headroom_now()
        assert room.full and room.sentence is not None
        assert "2.0 GB available, 5 GB needed" in room.sentence
        assert "rented: the machine is full: 1.5 GB available, 5 GB needed" in room.sentence
    finally:
        store.close()


def test_a_lane_on_the_rented_machine_is_resumed_there_with_its_card_and_reason(
    two_machines, repo: Path, machine_floor: Floor, store: Store
):
    """The board's own comeback of a lane on another machine goes through
    that machine's `needle resume` with the card and the cause; the first
    live comeback (Hello Revenue #503, 2026-09-10) died on a TypeError in
    the board's own forwarding before any wire call, and no test had ever
    resumed a lane elsewhere."""
    runtime, other = two_machines
    started = runtime.start(
        Start(repo=str(repo), card="card-7-far-away", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert started.verdict == LaunchVerdict.ALIVE, started.reason
    assert started.session is not None
    resumed = runtime.resume(
        started.session.short_id,
        prompt=None,
        card="card-7-far-away",
        reason="its allowance ran out",
    )
    words = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])]
    asked = [w for w in words if f"needle resume {started.session.short_id}" in w]
    assert asked, words[-3:]
    assert "--card card-7-far-away" in asked[-1] and "--reason" in asked[-1]
    assert resumed.verdict == LaunchVerdict.ALIVE, resumed.reason
    assert resumed.session is not None and resumed.session.machine == "rented"
    record = store.session_slot(resumed.session.session_id)
    assert record is not None and record.machine == "rented" and record.card == "card-7-far-away"
