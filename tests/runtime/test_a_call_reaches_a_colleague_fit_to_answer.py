"""The carried defect's two failures (card #110, item 5; the suggestion of
2026-09-07): a call to the bare name landed on a worker at effort none in a
read-only sandbox and nothing said so, and a turn that ended on a tool error
was reported as a colleague that finished without its note. A Codex row now
carries the effort and the sandbox its first turn ran at, read from the
rollout's `turn_context`; a worker's log is read for its last tool error, and
the judge names it."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from domain.call import Call, CallOutcome
from domain.gate import Gate
from runtime import calls, codex
from runtime.service import Runtime
from tests.floor import Floor

WORKER = "01a07bb6-bd09-7032-8b70-ca6c79c5c2f8"
NOW = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)


@pytest.fixture
def runtime(store) -> Runtime:
    return Runtime(store)


def test_a_codex_row_carries_the_effort_and_sandbox_its_turn_ran_at(
    machine_floor: Floor, runtime: Runtime
):
    machine_floor.write_rollout(WORKER, cwd="/tmp/lane", effort="high", sandbox="read-only")
    row = runtime.session(WORKER[:8])
    assert row.effort is Gate.HIGH and row.sandbox == "read-only"
    machine_floor.write_rollout(
        "01a07bb7-bd09-7032-8b70-ca6c79c5c2f8", cwd="/tmp/lane", effort="none"
    )
    off = runtime.session("01a07bb7")
    assert off.effort is None, "a word outside the four gates is no gate, never a guess"
    assert off.sandbox == "workspace-write"
    machine_floor.write_rollout("01a07bb8-bd09-7032-8b70-ca6c79c5c2f8", cwd="/tmp/lane")
    bare = runtime.session("01a07bb8")
    assert bare.effort is None and bare.sandbox is None, "a head without a turn says nothing"


def test_the_last_tool_error_is_read_from_the_workers_log(tmp_path: Path):
    log = tmp_path / "from-01a07bb6-re-glance.log"
    assert codex.last_error(log) is None, "no log, no error"
    log.write_text(
        "OpenAI Codex v0.153.4\n"
        "2026-09-07T12:20:31.634510Z ERROR codex_core::tools::router: error=collab spawn "
        "failed: no thread with id: 01a07bcf-e460-7e63-a660-20331e379478\n"
        "hook: PostToolUse\n",
        encoding="utf-8",
    )
    assert codex.last_error(log) == (
        "collab spawn failed: no thread with id: 01a07bcf-e460-7e63-a660-20331e379478"
    )
    log.write_text("OpenAI Codex v0.153.4\nthe answer\n", encoding="utf-8")
    assert codex.last_error(log) is None


def _call(answer: Path) -> Call:
    return Call(
        id=1,
        session_id=WORKER,
        slot="codex",
        name="codex-01a07bb6",
        note="/tmp/note.md",
        answer=str(answer),
        brief="read",
        caller="/tmp/lane",
        called_at=NOW,
        moved=None,
        ended_at=None,
        words=None,
    )


def test_a_turn_that_ended_on_a_tool_error_is_judged_as_that_error(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    answer = tmp_path / "from-01a07bb6-re-glance.md"
    machine_floor.write_rollout(WORKER, cwd="/tmp/lane")
    call = _call(answer)
    plain = calls.judge(call, runtime.sessions(), why_ended=None, moved_words=None)
    assert plain is not None and plain.outcome is CallOutcome.ENDED
    assert "ended without its note" in plain.words
    codex.log_path(str(answer)).write_text(
        "2026-09-07T12:20:31Z ERROR codex_core::tools::router: error=collab spawn failed: "
        "no thread with id: 01a07bcf\n",
        encoding="utf-8",
    )
    judged = runtime.judge_call(call)
    assert judged is not None and judged.outcome is CallOutcome.ENDED
    assert judged.words == (
        "01a07bb6's turn ended on a tool error, with no final message: collab spawn failed: "
        "no thread with id: 01a07bcf"
    )
    answer.write_text('{"answer": "late", "how_known": "checked", "sources": []}', encoding="utf-8")
    landed = runtime.judge_call(call)
    assert landed is not None and landed.outcome is CallOutcome.LANDED, (
        "an answer that landed after the call is the answer, whatever the log says"
    )


def test_a_turn_context_still_being_written_is_read_whole_next_time_and_a_rewrite_is_seen(
    machine_floor: Floor, runtime: Runtime
):
    """The cold read of round one (call 69): a scan that lands on a line
    still being written must not step past it, and a rollout rewritten in
    place — the floor does, Codex does not — must not answer from what it
    read before."""
    path = machine_floor.write_rollout(WORKER, cwd="/tmp/lane", effort="high", sandbox="read-only")
    whole = path.read_bytes()
    cut = whole.index(b'"turn_context"') + 40
    path.write_bytes(whole[:cut])
    assert runtime.session(WORKER[:8]).effort is None, "half a line is no line"
    with path.open("ab") as f:
        f.write(whole[cut:])
    row = runtime.session(WORKER[:8])
    assert row.effort is Gate.HIGH and row.sandbox == "read-only", "read whole once complete"
    machine_floor.write_rollout(WORKER, cwd="/tmp/lane", effort="low", sandbox="workspace-write")
    again = runtime.session(WORKER[:8])
    assert again.effort is Gate.LOW and again.sandbox == "workspace-write", "the rewrite is seen"
    machine_floor.write_rollout(WORKER, cwd="/tmp/lane")
    assert runtime.session(WORKER[:8]).effort is None, "a rewrite without a turn says nothing"


def test_the_latest_turns_context_answers_not_the_first(machine_floor: Floor, runtime: Runtime):
    """The cold read of round three (call 71) on two real rollouts: a
    worker whose first turn carried no context and a later turn did, and a
    fork carrying its parent's context before its own turn — the row says
    what the session runs at now, which is its latest turn's."""
    import json

    path = machine_floor.write_rollout(WORKER, cwd="/tmp/lane", effort="low", sandbox="read-only")
    later = {
        "timestamp": "2026-09-05T10:00:00.000Z",
        "ordinal": 9,
        "type": "turn_context",
        "payload": {
            "turn_id": "t2",
            "cwd": "/tmp/lane",
            "sandbox_policy": {"type": "workspace-write"},
            "effort": "high",
        },
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(later) + "\n")
        f.write(json.dumps({"type": "event_msg", "payload": {"type": "task_started"}}) + "\n")
        f.write("x" * 70000 + "\n")  # a long tool record after the context, past one block
    row = runtime.session(WORKER[:8])
    assert row.effort is Gate.HIGH and row.sandbox == "workspace-write"
    with path.open("a", encoding="utf-8") as f:
        f.write('{"type": "turn_context", "payload": {"effort": "medium"')  # in flight
    again = runtime.session(WORKER[:8])
    assert again.effort is Gate.HIGH, "a line in flight is not read"
