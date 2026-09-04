"""A start is verified by positive evidence and walks the ladder on a wall;
a move stops where it ran and resumes where the handoff names (plan 02, item 3).

The fake CLI registers sessions the way the real one does and follows the
fate each test scripts. The observation windows are shortened here; the
production values carry their own evidence in `runtime/launch.py`.
"""

from pathlib import Path

import pytest

from domain.gate import Gate
from domain.launch import LaunchVerdict, Start
from domain.session import SessionState
from domain.slot import Model
from runtime import launch
from runtime.service import Runtime
from tests.floor import Floor

BRIEF = "Read the plan and build item 1."


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    monkeypatch.setattr(launch, "HANDOFF_GRACE_SECONDS", 1.0)
    monkeypatch.setattr(launch, "STOP_SECONDS", 3.0)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    return root


@pytest.fixture
def runtime(store) -> Runtime:
    return Runtime(store)


def request(repo: Path, card: str = "card-7-the-thing") -> Start:
    return Start(repo=str(repo), card=card, brief=BRIEF, effort=Gate.XHIGH, from_slot=None)


def test_a_start_is_a_row_with_a_live_process_in_the_worktree_on_the_slot_the_rule_named(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    machine_floor.answer_best("alpha", None, "Fable headroom on alpha")

    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.ALIVE, result.reason
    assert result.session is not None and result.session.slot == "alpha"
    assert result.session.state == SessionState.WORKING and result.session.pid is not None
    assert result.session.worktree == str(repo / ".claude" / "worktrees" / "card-7-the-thing")
    assert [a.verdict for a in result.attempts] == [LaunchVerdict.ALIVE]
    launched = machine_floor.state()["launch_log"][0]
    assert launched["cwd"] == str(repo) and launched["config_dir"] == str(
        machine_floor.config_dir("alpha")
    )
    argv = launched["argv"]
    assert argv[:2] == ["--model", "fable"] and argv[-1] == BRIEF
    assert "--worktree" in argv and argv[argv.index("--worktree") + 1] == "card-7-the-thing"
    assert (
        argv[argv.index("--effort") + 1] == "xhigh"
        and argv[argv.index("-n") + 1] == "card-7-the-thing"
    )
    assert all(flag in argv for flag in launch.PROMPTS_SETTLED)
    record = store.session_slot(result.session.session_id)
    assert record is not None and record.slot == "alpha" and record.card == "card-7-the-thing"
    assert record.scope == "needle-card-7-the-thing.scope"
    assert machine_floor.state()["best_calls"] == [["best", "--json"]], "a start asks the rule live"


def test_the_scope_is_asked_for_and_only_claimed_when_proc_agrees(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.ALIVE
    calls = machine_floor.state()["busctl_calls"]
    assert len(calls) == 1 and "needle-card-7-the-thing.scope" in calls[0] and "PIDs" in calls[0]
    assert str(result.session.pid) in calls[0]
    assert (
        result.scope is None
        and result.reason is not None
        and "not in its own scope" in result.reason
    )


def test_a_launch_that_dies_on_a_wall_walks_to_where_the_handoff_names(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    machine_floor.answer_best("alpha")
    machine_floor.script_launches(
        {
            "then": "wall",
            "reason": "You've reached your Fable limit.",
            "account": "beta",
            "model": None,
        },
        {"then": "work"},
    )

    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.ALIVE, result.reason
    assert [(a.rung.slot, a.verdict) for a in result.attempts] == [
        ("alpha", LaunchVerdict.DEAD),
        ("beta", LaunchVerdict.ALIVE),
    ]
    assert result.attempts[0].reason == "You've reached your Fable limit."
    first, second = machine_floor.state()["launch_log"]
    assert machine_floor.state()["stops"] == [
        {"short": first["short"], "config_dir": str(machine_floor.config_dir("alpha"))}
    ]
    assert second["session_id"] == first["session_id"], "the walk resumes the same session id"
    assert "--resume" in second["argv"] and "--worktree" not in second["argv"]
    assert second["cwd"] == str(repo / ".claude" / "worktrees" / "card-7-the-thing")
    assert second["argv"][-1] == "[claude-acct] Carry on."
    rescues = store.rescues(first["session_id"])
    assert (
        len(rescues) == 1
        and rescues[0].from_rung.slot == "alpha"
        and rescues[0].to_rung.slot == "beta"
    )
    assert rescues[0].reason == "You've reached your Fable limit."
    assert not list(machine_floor.handoff_dir.glob("*.json")), "an acted-on handoff is removed"
    assert store.session_slot(first["session_id"]).slot == "beta"


def test_a_launch_that_vanishes_is_dead_with_the_machines_words(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    machine_floor.script_launches({"then": "vanish"})

    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.DEAD and result.session is None
    assert result.reason is not None and "ended" in result.reason and "stopped" in result.reason
    assert store.session_slots() == [] and len(machine_floor.state()["launch_log"]) == 1


def test_blocked_without_a_handoff_is_dead_and_says_so(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    machine_floor.script_launches({"then": "question", "detail": "asking: which of the two?"})

    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.DEAD
    assert (
        result.reason is not None
        and "no handoff names it: asking: which of the two?" in result.reason
    )
    assert len(machine_floor.state()["stops"]) == 1, "the dead probe is stopped"


def test_nowhere_to_run_starts_nothing(machine_floor: Floor, runtime: Runtime, repo: Path):
    machine_floor.refuse_best("no account with headroom")

    result = runtime.start(request(repo))

    assert result.verdict == LaunchVerdict.DEAD and "no account with headroom" in (
        result.reason or ""
    )
    assert machine_floor.state()["launch_log"] == []


def test_a_directory_without_git_is_refused(runtime: Runtime, tmp_path: Path, machine_floor: Floor):
    result = runtime.start(request(tmp_path))

    assert result.verdict == LaunchVerdict.DEAD and "not a git repository" in (result.reason or "")
    assert machine_floor.state()["best_calls"] == []


def test_stop_ends_the_session_and_proves_it_gone(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    started = runtime.start(request(repo))
    assert started.session is not None

    stopped = runtime.stop(started.session.short_id)

    assert stopped.gone and stopped.words == f"stopped {started.session.short_id}"
    after = runtime.session(started.session.short_id)
    assert after.state == SessionState.ENDED and after.pid is None


def test_a_move_leaves_exactly_one_live_copy_and_records_the_slot(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    started = runtime.start(request(repo))
    assert started.session is not None
    session_id = started.session.session_id
    machine_floor.write_handoff(
        session_id, **{"from": "alpha"}, account="beta", pid=started.session.pid
    )

    moved = runtime.move(started.session.short_id, None)

    assert moved.verdict == LaunchVerdict.ALIVE, moved.reason
    assert (
        moved.session is not None
        and moved.session.slot == "beta"
        and moved.session.session_id == session_id
    )
    copies = [s for s in runtime.sessions() if s.session_id == session_id]
    assert [(c.slot, c.stale, c.pid is not None) for c in sorted(copies, key=lambda c: c.slot)] == [
        ("alpha", True, False),
        ("beta", False, True),
    ]
    assert machine_floor.state()["stops"][0]["config_dir"] == str(machine_floor.config_dir("alpha"))
    resumed = machine_floor.state()["launch_log"][1]
    assert "--resume" in resumed["argv"] and resumed["cwd"] == started.session.worktree
    assert store.session_slot(session_id).slot == "beta"
    assert store.session_slot(session_id).card == "card-7-the-thing"
    assert [r.to_rung.slot for r in store.rescues(session_id)] == ["beta"]
    assert not list(machine_floor.handoff_dir.glob("*.json"))


def test_the_slot_record_survives_a_new_store_and_clearing_the_rescues(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    started = runtime.start(request(repo))
    assert started.session is not None
    session_id = started.session.session_id
    machine_floor.write_handoff(session_id, account="beta")
    runtime.move(started.session.short_id, None)

    from infrastructure.store import Store

    reopened = Store(store.path)
    try:
        assert reopened.session_slot(session_id).slot == "beta"
        assert Runtime(reopened).clear_rescues(started.session.short_id) == 1
        assert reopened.rescues(session_id) == []
        assert reopened.session_slot(session_id).slot == "beta", (
            "clearing rescues never clears the slot"
        )
    finally:
        reopened.close()


def test_a_move_above_the_resume_limit_starts_fresh_with_the_brief(
    machine_floor: Floor, runtime: Runtime, repo: Path, store, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(launch, "RESUME_SIZE_LIMIT", 1024)
    started = runtime.start(request(repo))
    assert started.session is not None
    old = started.session.session_id
    machine_floor.write_transcript(started.session.worktree, old, 4096)
    machine_floor.answer_best("beta", None, "moved by hand")

    moved = runtime.move(started.session.short_id, None)

    assert moved.verdict == LaunchVerdict.ALIVE, moved.reason
    assert moved.session is not None and moved.session.session_id != old
    fresh = machine_floor.state()["launch_log"][1]
    assert "--resume" not in fresh["argv"]
    assert "fresh session" in fresh["argv"][-1] and BRIEF in fresh["argv"][-1]
    assert "fresh session" in store.rescues(old)[0].reason
    assert store.session_slot(moved.session.session_id).slot == "beta"
    assert machine_floor.state()["best_calls"][-1] == [
        "best",
        "--json",
        "--from",
        "alpha",
        "--tried",
        "alpha",
    ]


def test_a_move_asked_for_a_slot_the_rule_would_not_choose_is_refused(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    started = runtime.start(request(repo))
    assert started.session is not None
    machine_floor.answer_best("alpha", None, "beta is out")

    moved = runtime.move(started.session.short_id, "beta")

    assert moved.verdict == LaunchVerdict.DEAD and "would not place" in (moved.reason or "")
    assert len(machine_floor.state()["launch_log"]) == 1


def test_a_stale_copy_is_not_moved(machine_floor: Floor, store):
    """The guard is exercised directly: a `Session` marked stale, so no real
    stop runs and the runner's own pid is never handed to `claude stop`."""
    from domain.session import Session, SessionKind, SessionState

    stale = Session(
        slot="alpha",
        config_dir=str(machine_floor.config_dir("alpha")),
        short_id="eeee1111",
        session_id="eeee1111-0000-4000-8000-000000000000",
        kind=SessionKind.BACKGROUND,
        name="a lane",
        cwd="/x",
        worktree=None,
        state=SessionState.ENDED,
        recorded="done",
        detail="",
        pid=None,
        scope=None,
        model=None,
        effort=None,
        stale=True,
        wall=None,
        intent="",
        created_at=None,
        updated_at=None,
    )

    result = launch.move(store, stale, to=None, card="a lane")

    assert result.verdict == LaunchVerdict.DEAD and "stale copy" in (result.reason or "")
    assert machine_floor.state()["launch_log"] == [] and machine_floor.state()["stops"] == []


def test_an_interactive_session_is_not_moved(machine_floor: Floor, runtime: Runtime):
    """An interactive session is refused before any stop, so passing this
    process's own pid as its live pid can never reach `claude stop`."""
    import os

    machine_floor.write_process(
        "alpha", "ffff2222-0000-4000-8000-000000000000", os.getpid(), kind="interactive"
    )

    result = runtime.move("ffff2222", None)

    assert result.verdict == LaunchVerdict.DEAD
    assert "terminal of its own" in (result.reason or "")
    assert machine_floor.state()["launch_log"] == [] and machine_floor.state()["stops"] == []


def test_short_ids_are_read_from_what_the_cli_prints():
    printed = "Starting background service…\nbackgrounded · \x1b[36m2067d565\x1b[39m · needle-1\n"
    assert launch.short_id_in(printed) == "2067d565"
    assert launch.short_id_in("backgrounded · 2067d565") == "2067d565"
    assert launch.short_id_in("nothing here") is None


def test_the_launch_argv_carries_the_model_the_rule_named():
    from domain.slot import Placement

    placement = Placement(slot="beta", model=Model.OPUS, config_dir="/x", why="")
    argv = launch.argv_for(
        placement, effort=None, name=None, prompt="go", resume=None, worktree=None
    )
    assert argv[1:] == ["--bg", "--model", "opus", *launch.PROMPTS_SETTLED, "go"]
