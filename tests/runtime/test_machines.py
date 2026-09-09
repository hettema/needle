"""The work runs where the horsepower is (card #83, item 4): a second machine
on the floor, reached by the fake `ssh`, and the rule that places work.

The other machine is a second floor under the first's root; its `needle`
is the venv's own script run there by the stand-in `ssh` with that floor's
environment, so every verb the board asks over the wire runs the real code
against the real typed edge, and only the transport is a fake.
"""

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


def test_a_card_in_a_machines_own_record_runs_on_that_machine_even_when_it_is_full():
    laptop = _machine("laptop", desktop=True, ground="/home/x/laptop-record")
    rented = _machine("rented", host="rented")
    rooms = [
        _reading(laptop, _room(1.0, full=True, sentence="the machine is full: 1.0 GB"), here=True),
        _reading(rented, _room(24.0)),
    ]
    chosen, why = choose_machine(rooms, "/home/x/laptop-record")
    assert chosen is laptop and "records" in why


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
    assert "needle-lane-card-7-far-away" in machine_floor.state()["tmux"]

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
