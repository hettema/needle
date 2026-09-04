"""One list of sessions across every slot, each row checked in /proc (plan 02, item 1)."""

import json
import os

from domain.gate import Gate
from domain.session import SessionKind, SessionState
from domain.slot import Model
from runtime.service import Runtime
from tests.floor import Floor

ME = os.getpid()


def test_a_row_is_live_only_with_its_process_in_proc(machine_floor: Floor, store):
    alive = machine_floor.write_job("alpha", "aaaa1111", state="working", detail="thinking")
    machine_floor.write_process("alpha", alive, ME)
    machine_floor.write_job("beta", "bbbb2222", state="working", detail="thinking")
    reused = machine_floor.write_job("beta", "cccc3333", state="done")
    machine_floor.write_process("beta", reused, ME, start="1")

    rows = {s.short_id: s for s in Runtime(store).sessions()}

    assert rows["aaaa1111"].state == SessionState.WORKING and rows["aaaa1111"].pid == ME
    assert rows["aaaa1111"].slot == "alpha" and rows["aaaa1111"].kind == SessionKind.BACKGROUND
    assert rows["bbbb2222"].state == SessionState.ENDED and rows["bbbb2222"].pid is None
    assert rows["bbbb2222"].recorded == "working", "the registry's word is kept, not believed"
    assert rows["cccc3333"].state == SessionState.ENDED, "a reused pid is not the session's"


def test_the_live_copy_wins_and_the_stale_copy_is_named(machine_floor: Floor, store):
    session_id = machine_floor.write_job(
        "alpha", "dddd4444", state="done", updated_at="2026-09-04T09:00:00Z"
    )
    machine_floor.write_job(
        "beta",
        "dddd4444",
        state="working",
        session_id=session_id,
        updated_at="2026-09-04T09:05:00Z",
    )
    machine_floor.write_process("beta", session_id, ME)

    rows = [s for s in Runtime(store).sessions() if s.session_id == session_id]

    live = [r for r in rows if not r.stale]
    stale = [r for r in rows if r.stale]
    assert [r.slot for r in live] == ["beta"] and live[0].state == SessionState.WORKING
    assert [r.slot for r in stale] == ["alpha"] and stale[0].state == SessionState.ENDED


def test_with_no_live_copy_the_newest_record_stands(machine_floor: Floor, store):
    session_id = machine_floor.write_job(
        "alpha", "eeee5555", state="done", updated_at="2026-09-04T09:00:00Z"
    )
    machine_floor.write_job(
        "beta",
        "eeee5555",
        state="stopped",
        session_id=session_id,
        updated_at="2026-09-04T09:05:00Z",
    )

    rows = {s.slot: s for s in Runtime(store).sessions() if s.session_id == session_id}

    assert not rows["beta"].stale and rows["alpha"].stale
    assert rows["beta"].state == SessionState.ENDED


def test_the_default_directory_is_read_under_the_slot_holding_its_identity(
    machine_floor: Floor, store
):
    path = machine_floor.claude_home / "jobs" / "ffff6666" / "state.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "state": "done",
                "sessionId": "ffff6666-0000-4000-8000-000000000000",
                "cwd": "/x",
                "name": "by hand",
            }
        )
    )

    row = next(s for s in Runtime(store).sessions() if s.short_id == "ffff6666")

    assert row.slot == "alpha" and row.config_dir == str(machine_floor.claude_home)


def test_an_interactive_session_is_listed_from_its_process_record(machine_floor: Floor, store):
    machine_floor.write_process(
        "beta",
        "abcd0000-0000-4000-8000-000000000000",
        ME,
        kind="interactive",
        status="busy",
        cwd="/work",
        name="work-9z",
    )

    row = next(s for s in Runtime(store).sessions() if s.short_id == "abcd0000")

    assert row.kind == SessionKind.INTERACTIVE and row.state == SessionState.WORKING
    assert row.name == "work-9z" and row.cwd == "/work" and row.slot == "beta"


def test_a_wall_rides_on_the_row_and_the_flags_are_read(machine_floor: Floor, store):
    session_id = machine_floor.write_job(
        "alpha",
        "1a2b3c4d",
        state="blocked",
        detail="You've reached your Fable limit.",
        model="fable",
        effort="high",
        worktree="/repo/.claude/worktrees/card-1",
    )
    machine_floor.write_process("alpha", session_id, ME)
    machine_floor.write_handoff(session_id, account="beta", model="opus")

    row = next(s for s in Runtime(store).sessions() if s.short_id == "1a2b3c4d")

    assert row.state == SessionState.BLOCKED
    assert row.wall is not None and row.wall.account == "beta" and row.wall.model == Model.OPUS
    assert row.model == Model.FABLE and row.effort == Gate.HIGH
    assert row.worktree == "/repo/.claude/worktrees/card-1"


def test_an_unreadable_handoff_is_named_not_skipped(machine_floor: Floor, store):
    (machine_floor.handoff_dir / "broken.json").write_text("{not json")
    (machine_floor.handoff_dir / "half.json.tmp").write_text("{}")

    unreadable = Runtime(store).handoffs().unreadable

    assert unreadable == [str(machine_floor.handoff_dir / "broken.json")]
