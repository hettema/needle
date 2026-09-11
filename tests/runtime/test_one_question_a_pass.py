"""The board asks another machine one question a pass (card #123).

Every test here stands on two floors: this one as the laptop, and a second
reached by the fake `ssh` as the rented machine, whose `needle` is the
venv's own. Both floors share one filesystem, so a lane's worktree is laid
once and this process's git is told not to see the rented machine's lanes —
the rented machine's `needle` sees every checkout, as a machine with the
same layout does."""

import asyncio
import os
import subprocess
import time
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.board_cli import _board
from api.cli import main
from api.runtime_cli import describe_room
from board.lane import HANDS_ON
from domain.board import Beat
from domain.machine import Machine
from infrastructure import clock
from infrastructure.store import Store
from runtime import git as runtime_git
from tests.floor import Floor
from tests.runtime.test_machines import NOW, quick  # noqa: F401 — the module's autouse fixture


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def lay(
    machine_floor: Floor, corpus: Path, monkeypatch: pytest.MonkeyPatch, request
) -> Iterator[Callable[..., SimpleNamespace]]:
    """A board over the synthetic project with `far` lanes on the rented
    machine and `near` lanes here, each with a live session in its worktree."""
    sleepers: list[subprocess.Popen[bytes]] = []
    stores: list[Store] = []

    def make(
        *, far: int = 3, near: int = 0, command: str = "needle", desktop: str = "laptop"
    ) -> SimpleNamespace:
        git(corpus, "init", "-q", "-b", "develop")
        git(corpus, "add", "-A")
        git(
            corpus,
            "-c",
            "user.email=f@floor",
            "-c",
            "user.name=floor",
            "commit",
            "-q",
            "-m",
            "root",
        )
        other = machine_floor.lay_host("rented", available_gb=24.0)
        registry = Store(Path(os.environ["NEEDLE_DB"]))
        for m in (
            Machine(
                name="laptop",
                machine_id=machine_floor.machine_id,
                host=None,
                desktop=desktop == "laptop",
                ground=None,
                command="needle",
                added_at=NOW,
            ),
            Machine(
                name="rented",
                machine_id=other.machine_id,
                host="rented",
                desktop=desktop == "rented",
                ground=None,
                command=command,
                added_at=NOW,
            ),
        ):
            registry.add_machine(m)
        registry.close()
        assert main(["add", str(corpus)]) == 0
        store, live, runtime, loops, doors = _board()
        stores.append(store)
        slug = next(iter(live.projects))
        numbers = [c.number for c in store.cards(slug)]
        numbers += [9000 + i for i in range(max(0, far + near - len(numbers)))]
        paths: dict[int, tuple[Path, bool]] = {}
        for i, number in enumerate(numbers[: far + near]):
            on_far = i < far
            name = f"card-{number}-{'far' if on_far else 'near'}"
            lane = corpus / ".claude" / "worktrees" / name
            git(corpus, "worktree", "add", "-q", "-b", name, str(lane))
            (lane / "notes.md").write_text("an edit\n", encoding="utf-8")
            sleeper = subprocess.Popen(["sleep", "600"])
            sleepers.append(sleeper)
            floor = other if on_far else machine_floor
            short = f"{'f' if on_far else 'n'}{number:07d}"
            session_id = floor.write_job(
                "alpha", short, cwd=str(lane), worktree=str(lane), name=name
            )
            floor.write_process("alpha", session_id, sleeper.pid, cwd=str(lane), name=name)
            paths[number] = (lane, on_far)
        real = runtime_git.worktrees
        monkeypatch.setattr(
            runtime_git,
            "worktrees",
            lambda repo: {p: b for p, b in real(repo).items() if not p.endswith("-far")},
        )
        return SimpleNamespace(
            other=other,
            store=store,
            live=live,
            runtime=runtime,
            loops=loops,
            doors=doors,
            slug=slug,
            repo=str(corpus),
            far={n: str(p) for n, (p, f) in paths.items() if f},
            near={n: str(p) for n, (p, f) in paths.items() if not f},
        )

    yield make
    for sleeper in sleepers:
        sleeper.kill()
        sleeper.wait()
    for store in stores:
        store.close()


def ssh_words(floor: Floor, since: int = 0) -> list[str]:
    return [" ".join(c["words"]) for c in floor.state().get("ssh_calls", [])[since:]]


def lanes_of(b: SimpleNamespace):
    snapshot = b.live.projects[b.slug].snapshot
    assert snapshot is not None
    return snapshot.lanes


# ── item 1: one question a pass ───────────────────────────────────────


def test_one_pass_asks_the_other_machine_once_and_reads_what_the_verbs_read(
    lay, machine_floor: Floor
):
    b = lay(far=3)
    # The first pass finds the lanes; the second asks about them.
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    before = len(ssh_words(machine_floor))
    b.loops.reconcile_now()
    asked = ssh_words(machine_floor, before)
    assert len(asked) == 1 and "observe --ask -" in asked[0], asked
    observed = lanes_of(b)
    for number in b.far:
        assert observed[number].state in HANDS_ON, observed[number].sentence
        assert observed[number].machine == "rented"

    # The same board read the old way — every read one verb at a time.
    store, live, runtime, loops, _ = _board()
    try:
        runtime.collect = lambda asks, only=None: {}  # type: ignore[method-assign]
        loops.reconcile_now()
        loops.reconcile_now()
        assert runtime.observed == {}
        old = lanes_of(SimpleNamespace(live=live, slug=b.slug))
        for number, path in b.far.items():
            now, then = observed[number], old[number]
            assert (now.state, now.machine, now.path) == (then.state, then.machine, then.path)
            assert now.session is not None and then.session is not None
            assert now.session.short_id == then.session.short_id
            assert sorted(now.edits) == sorted(then.edits) and "notes.md" in now.edits
            branch = Path(path).name
            assert b.runtime.lane_tip(b.repo, branch, path=path) == runtime.lane_tip(
                b.repo, branch, path=path
            )
        rented = sorted(s.short_id for s in b.runtime.sessions() if s.machine == "rented")
        assert rented == sorted(s.short_id for s in runtime.sessions() if s.machine == "rented")
        assert b.runtime.boots("rented") == runtime.boots("rented")
        # A parked lane's limits are read from the answer, never over the wire.
        before_limits = len(ssh_words(machine_floor))
        assert b.runtime.limits("alpha", machine_name="rented") == runtime.limits(
            "alpha", machine_name="rented"
        )
        asked_for_limits = ssh_words(machine_floor, before_limits)
        assert len(asked_for_limits) == 1 and "limits alpha" in asked_for_limits[0], (
            "only the runtime that observed nothing asked"
        )
    finally:
        store.close()


def test_a_machine_whose_needle_predates_the_question_is_read_the_old_way_and_said_behind(
    lay, machine_floor: Floor, tmp_path: Path
):
    older = tmp_path / "older-needle"
    older.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = observe ]; then\n'
        "  echo \"needle: error: argument command: invalid choice: 'observe'\" >&2\n"
        "  exit 2\n"
        "fi\n"
        'exec needle "$@"\n',
        encoding="utf-8",
    )
    older.chmod(0o755)
    b = lay(far=2, command=str(older))
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    seen = b.runtime.observed["rented"]
    assert seen.fresh and seen.behind
    asked = ssh_words(machine_floor)
    assert any("sessions --lean" in a for a in asked) and any(" tip " in a for a in asked)
    lanes = lanes_of(b)
    for number in b.far:
        assert lanes[number].state in HANDS_ON and lanes[number].machine == "rented"
    rented = next(r for r in b.runtime.rooms() if r.machine.name == "rented")
    assert rented.behind and "its needle is behind" in describe_room(rented)


# ── item 2: a silent machine's last answer stands ──────────────────────


def test_a_silent_machine_keeps_its_last_reading_with_its_age_and_nothing_waits_under_the_lock(
    lay, machine_floor: Floor
):
    b = lay(far=2)
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    machine_floor.host_down("rented")
    b.loops.reconcile_now()
    seen = b.runtime.observed["rented"]
    assert not seen.fresh and seen.observation is not None and "rented" in b.runtime.unread
    rented = next(r for r in b.runtime.rooms() if r.machine.name == "rented")
    assert rented.room is not None and rented.why and rented.observed_at is not None
    assert "as last read" in describe_room(rented)
    lanes = lanes_of(b)
    for number in b.far:
        assert lanes[number].state in HANDS_ON, "an old reading moves nothing"
        assert "As rented last answered" in lanes[number].sentence, lanes[number].sentence
    # What runs under the lock asks no machine anything.
    before = len(ssh_words(machine_floor))
    b.loops.apply_now()
    assert ssh_words(machine_floor, before) == []
    # It answers again, and the next pass reads it.
    machine_floor.host_down("rented", False)
    b.loops.reconcile_now()
    assert b.runtime.observed["rented"].fresh and "rented" not in b.runtime.unread
    assert all("last answered" not in lanes_of(b)[n].sentence for n in b.far)


def test_the_boards_own_lanes_are_applied_while_another_machine_is_slow(lay, machine_floor: Floor):
    b = lay(far=1, near=1)
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    hosts = machine_floor.state()["hosts"]
    hosts["rented"]["env"]["NEEDLE_FAKE_SLOW"] = "6"
    machine_floor.update(hosts=hosts)

    async def passes() -> tuple[float, bool]:
        asked = clock.now()
        began = time.monotonic()
        await b.loops.reconcile(every=False)
        own = time.monotonic() - began
        rented_then = b.runtime.observed["rented"].asked_at
        waited_for_rented = rented_then is not None and rented_then >= asked
        await b.loops.reconcile()
        return own, waited_for_rented

    own, waited = asyncio.run(passes())
    assert own < 5.0 and not waited, "the board's own machine never waits on the rented one"
    assert b.runtime.observed["rented"].fresh
    assert b.runtime.observed["laptop"].fresh


# ── items 3 and 4: the lock, and the measure ───────────────────────────


def test_the_lock_is_held_under_a_second_a_pass_with_thirty_lanes_on_two_machines(lay):
    b = lay(far=15, near=15)

    async def passes() -> None:
        for _ in range(3):
            await b.loops.reconcile()

    asyncio.run(passes())
    beat = b.loops.last_beat
    assert beat is not None and set(beat.collection) <= {"laptop", "rented"}
    assert beat.lock_seconds < 1.0, beat
    assert b.store.beats(limit=1)[0].lock_seconds == beat.lock_seconds


def test_the_last_pass_says_whether_its_click_was_answered(machine_floor: Floor, capsys):
    assert main(["beats", "--last"]) == 1
    assert "no pass has been timed yet" in capsys.readouterr().out
    store = Store(Path(os.environ["NEEDLE_DB"]))
    try:
        store.record_beat(
            Beat(
                at=NOW,
                collection={"laptop": 0.4, "rented": 1.2},
                lock_seconds=0.08,
                door="watch",
                door_wait=0.05,
                door_seconds=0.3,
            )
        )
        store.record_beat(
            Beat(at=NOW + timedelta(seconds=30), collection={"laptop": 0.4}, lock_seconds=0.07)
        )
    finally:
        store.close()
    assert main(["beats", "--last"]) == 0
    out = capsys.readouterr().out
    assert "collection: laptop 0.4 s · lock held 0.07 s · no click during the pass" in out
    assert "last click: watch answered in 0.35 s" in out
    store = Store(Path(os.environ["NEEDLE_DB"]))
    try:
        store.record_beat(
            Beat(
                at=NOW + timedelta(seconds=60),
                collection={"laptop": 0.4},
                lock_seconds=1.4,
                door="start",
                door_wait=1.2,
                door_seconds=0.2,
            )
        )
    finally:
        store.close()
    assert main(["beats", "--last"]) == 0
    out = capsys.readouterr().out
    assert "click: start waited 1.20 s and took 0.20 s" in out and "answered" not in out


# ── item 3: under the lock, bookkeeping only ───────────────────────────


def test_the_apply_starts_no_process_and_asks_no_machine(
    lay, machine_floor: Floor, monkeypatch: pytest.MonkeyPatch
):
    b = lay(far=3, near=3)
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    # As the server's pass does it: every fold proved before the lock.
    b.runtime.collect(b.loops._asks())
    b.loops._proofs = b.loops._prove()
    started: list[str] = []
    real_init = subprocess.Popen.__init__

    def watching(self, args, *rest, **kwargs):
        started.append(str(args)[:120])
        return real_init(self, args, *rest, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "__init__", watching)
    before = len(ssh_words(machine_floor))
    b.loops.apply_now()
    monkeypatch.setattr(subprocess.Popen, "__init__", real_init)
    assert started == [], started
    assert ssh_words(machine_floor, before) == []


def test_a_stop_on_either_machine_is_on_the_card_and_its_ending_is_named_outside_the_lock(
    lay, machine_floor: Floor
):
    b = lay(far=1, near=1)
    asked_under_lock: list[str] = []
    applying = b.loops.apply_now

    def watched() -> None:
        before = len(ssh_words(machine_floor))
        applying()
        # A question out to a machine runs beside the apply, and an act the
        # pass makes (a launch, a stop, a session put back in its group) is
        # the lock's by the plan's ruling; a read the wire carried meanwhile
        # was asked under the lock.
        reads = (
            "sessions",
            "boots",
            "room",
            "tip",
            "edits",
            "lane-docs",
            "worktrees",
            "cause",
            "limits",
            "where",
            "dispatches",
            "transcript-size",
            "scopes --held",
        )
        asked_under_lock.extend(
            w
            for w in ssh_words(machine_floor, before)
            if any(f"needle {verb} " in w or f"needle {verb}'" in w for verb in reads)
        )

    b.loops.apply_now = watched  # type: ignore[method-assign]
    stopped: dict[int, object] = {}

    async def story() -> None:
        # One event loop for the whole story: the loops' lock belongs to the
        # loop that first waited on it.
        for _ in range(2):
            await b.loops.reconcile()
        lanes = lanes_of(b)
        (far,), (near,) = list(b.far), list(b.near)
        for number in (far, near):
            session = lanes[number].session
            assert session is not None and lanes[number].state in HANDS_ON
            stopped[number] = session
            assert b.runtime.stop(session.short_id).gone
        # The door's apply: the acts stand in the observations, no machine read.
        before = len(ssh_words(machine_floor))
        applying()
        assert ssh_words(machine_floor, before) == []
        after = lanes_of(b)
        assert after[far].state not in HANDS_ON, after[far].sentence
        assert after[near].state not in HANDS_ON, after[near].sentence
        # The passes that follow name both endings, and ask nothing under the lock.
        for _ in range(2):
            await b.loops.reconcile()

    asyncio.run(story())
    assert asked_under_lock == [], asked_under_lock
    sessions = stopped
    deaths = b.store.deaths(b.slug)
    assert all(s.session_id in deaths for s in sessions.values())  # type: ignore[attr-defined]


# ── the review's findings (Codex, call 105) ────────────────────────────


def test_the_newest_act_on_a_session_stands_over_an_older_answer(lay):
    from runtime.service import Answer

    b = lay(far=1)
    b.loops.reconcile_now()
    b.loops.reconcile_now()
    rented = b.runtime.machine_named("rented")
    seen = b.runtime.observed["rented"]
    session = next(s for s in seen.observation.sessions if s.pid is not None)
    asked = clock.now()
    b.runtime._put_acted(rented, session)
    b.runtime._put_acted(rented, session.model_copy(update={"pid": None}))
    old_answer = Answer(rented, seen.observation, False, None, asked, 0.1)
    assert b.runtime._accept(old_answer)
    rows = [s for s in b.runtime.sessions() if s.session_id == session.session_id]
    assert [r.pid for r in rows] == [None], "the stop is newer than the launch"


def test_a_machine_is_unread_until_its_first_answer_and_nothing_reads_it_over_the_wire(
    lay, machine_floor: Floor
):
    b = lay(far=1)
    b.loops.reconcile_now()
    late = machine_floor.lay_host("late")
    hosts = machine_floor.state()["hosts"]
    hosts["late"]["env"]["NEEDLE_FAKE_SLOW"] = "4"
    machine_floor.update(hosts=hosts)
    b.store.add_machine(
        Machine(
            name="late",
            machine_id=late.machine_id,
            host="late",
            desktop=False,
            ground=None,
            command="needle",
            added_at=NOW,
        )
    )
    b.runtime.ask_machines(b.loops._asks())
    assert "late" in b.runtime.unread
    before = len(ssh_words(machine_floor))
    b.runtime.rooms()
    b.runtime.sessions()
    b.runtime.scopes()
    b.runtime.boots("late")
    b.runtime.limits("alpha", machine_name="late")
    assert [w for w in ssh_words(machine_floor, before) if "observe --ask" not in w] == []


def test_another_machines_group_is_read_from_its_answer(lay, machine_floor: Floor):
    b = lay(far=1)
    b.loops.reconcile_now()
    before = len(ssh_words(machine_floor))
    assert b.runtime.scope_pids("needle-card-1-far.scope", machine_name="rented") == []
    assert ssh_words(machine_floor, before) == []
    machine_floor.host_down("rented")
    b.loops.reconcile_now()
    before = len(ssh_words(machine_floor))
    assert b.runtime.scope_pids("needle-card-1-far.scope", machine_name="rented") is None
    assert ssh_words(machine_floor, before) == []


def test_a_failed_answer_keeps_the_question_time_of_what_it_keeps(lay, machine_floor: Floor):
    b = lay(far=1)
    b.loops.reconcile_now()
    kept = b.runtime.observed["rented"].asked_at
    machine_floor.host_down("rented")
    b.loops.reconcile_now()
    seen = b.runtime.observed["rented"]
    assert not seen.fresh and seen.observation is not None
    assert seen.asked_at == kept, "the windows it lists are read against their own question"


def test_an_older_needle_on_the_desktop_answers_its_limits_and_windows(
    lay, machine_floor: Floor, tmp_path: Path
):
    older = tmp_path / "older-needle"
    older.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = observe ]; then echo "invalid choice: observe" >&2; exit 2; fi\n'
        'exec needle "$@"\n',
        encoding="utf-8",
    )
    older.chmod(0o755)
    b = lay(far=1, command=str(older), desktop="rented")
    b.loops.reconcile_now()
    seen = b.runtime.observed["rented"]
    assert seen.fresh and seen.behind
    assert seen.observation is not None and seen.observation.windows is not None
    assert "alpha" in seen.observation.limits
    before = len(ssh_words(machine_floor))
    b.runtime.limits("alpha", machine_name="rented")
    assert ssh_words(machine_floor, before) == [], "a park reads the answer, not the wire"
