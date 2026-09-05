"""A colleague of any make can be called warm and seen at work (plan 57),
on the floor: the one colleague concept resolves a Codex worker by name,
id or prefix and refuses the ambiguous, the absent, the terminal and the
busy with the true reason; the one call resumes it with `codex exec
resume`, the answer lands through the existing record without a manual
relay, and the existing judge reads it; the one list shows Codex rows
beside Claude rows, a malformed or vanished rollout hides nothing, and
`doing` is the tool's name and never its input."""

import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from domain.call import Call, CallOutcome
from domain.launch import LaunchVerdict
from domain.session import Session, SessionKind, SessionState
from runtime import codex, launch
from runtime.service import Ambiguous, Runtime
from tests.floor import Floor

WORKER = "01a07123-7d89-78f3-ad15-ee875e35a4c8"
OLDER = "01a07100-0000-7000-8000-000000000001"
CHAIR = "01a06f2b-f714-7af3-b221-fe8877909fe4"
SECRET = 'await tools.exec_command({cmd: "cat ~/.credentials"})'


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "STOP_SECONDS", 3.0)


@pytest.fixture
def runtime(store) -> Runtime:
    return Runtime(store)


def until(predicate, seconds: float = 4.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    assert predicate()


def a_process_on(session_id: str) -> subprocess.Popen:
    """A live process that names the rollout the way `codex exec resume`
    does: the id after `resume` in its argv."""
    child = subprocess.Popen(
        # `; true` keeps the shell from exec'ing the sleep in its own place,
        # which would drop the id from the argv the runtime reads.
        ["sh", "-c", "sleep 300; true", "codex", "exec", "resume", session_id],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return child


def end(child: subprocess.Popen) -> None:
    for pid in [child.pid]:
        subprocess.run(["pkill", "-TERM", "-P", str(pid)], check=False)
    child.terminate()
    child.wait(timeout=5)


# ── item 1: the colleague concept resolves a Codex worker ─────────────


def test_the_bare_name_is_the_most_recent_worker_and_an_id_or_prefix_is_that_rollout(
    machine_floor: Floor, runtime: Runtime
):
    machine_floor.write_rollout(OLDER, cwd="/srv/older", started_at="2026-09-05T08:00:00.000Z")
    time.sleep(0.02)
    newest = machine_floor.write_rollout(WORKER, cwd="/srv/newest")
    machine_floor.write_rollout(CHAIR, source="cli", cwd="/srv/chair")
    os.utime(newest, None)

    by_name = runtime.colleague("codex")
    assert isinstance(by_name, Session)
    assert by_name.session_id == WORKER and by_name.slot == "codex", "the newest worker"
    assert by_name.kind == SessionKind.BACKGROUND and by_name.cwd == "/srv/newest"

    by_id = runtime.colleague(WORKER)
    by_prefix = runtime.colleague(WORKER[:8])
    assert isinstance(by_id, Session) and by_id.session_id == WORKER
    assert isinstance(by_prefix, Session) and by_prefix.session_id == WORKER

    assert runtime.colleague("01a0ffff") is None, "an absent prefix names nobody"
    assert runtime.colleague("nobody-at-all") is None


def test_a_prefix_naming_two_rollouts_is_refused_naming_both(
    machine_floor: Floor, runtime: Runtime
):
    twin = WORKER[:8] + "-aaaa-7000-8000-000000000002"
    machine_floor.write_rollout(WORKER)
    machine_floor.write_rollout(twin, started_at="2026-09-05T10:00:00.000Z")

    with pytest.raises(Ambiguous) as refused:
        runtime.colleague(WORKER[:8])
    assert WORKER in str(refused.value) and twin in str(refused.value)
    assert "name one" in str(refused.value)


def test_a_terminal_and_a_busy_worker_are_refused_with_the_reason_and_nothing_runs(
    machine_floor: Floor, runtime: Runtime
):
    machine_floor.write_rollout(CHAIR, source="cli", mid_turn=False)
    machine_floor.write_rollout(WORKER)
    busy = a_process_on(WORKER)
    try:
        chair = runtime.colleague(CHAIR)
        assert isinstance(chair, Session) and chair.kind == SessionKind.INTERACTIVE
        refused = runtime.call(chair, brief="a question", name=chair.name, answer="/srv/a.md")
        assert refused.verdict == LaunchVerdict.DEAD
        assert "terminal of its own" in (refused.reason or "")

        worker = runtime.colleague(WORKER)
        assert isinstance(worker, Session)
        assert worker.pid == busy.pid and worker.state == SessionState.WORKING
        refused = runtime.call(worker, brief="a question", name=worker.name, answer="/srv/a.md")
        assert refused.verdict == LaunchVerdict.DEAD
        assert "working on its turn" in (refused.reason or "")
    finally:
        end(busy)
    assert machine_floor.state()["codex_log"] == [], "no resume ran for a refusal"


def test_a_source_this_reader_does_not_know_is_shown_by_its_word_and_never_called(
    machine_floor: Floor, runtime: Runtime
):
    machine_floor.write_rollout(WORKER, source="mcp")
    row = runtime.colleague(WORKER)
    assert isinstance(row, Session)
    assert row.kind == SessionKind.INTERACTIVE and row.recorded == "mcp"
    assert runtime.colleague("codex") is None, "an unknown source is no worker"
    refused = runtime.call(row, brief="a question", name=row.name, answer="/srv/a.md")
    assert refused.verdict == LaunchVerdict.DEAD
    assert "source 'mcp'" in (refused.reason or "") and "only an `exec` rollout" in (
        refused.reason or ""
    )
    assert machine_floor.state()["codex_log"] == []


def test_claude_resolution_is_unchanged_beside_the_codex_rows(
    machine_floor: Floor, runtime: Runtime
):
    claude = machine_floor.write_job("alpha", "aaaa1111", state="done")
    machine_floor.write_process("alpha", claude, os.getpid())
    machine_floor.write_rollout(WORKER)

    who = runtime.colleague("aaaa1111")
    assert isinstance(who, Session) and who.slot == "alpha" and who.session_id == claude
    on_slot = runtime.colleague("alpha")
    assert isinstance(on_slot, Session) and on_slot.session_id == claude


# ── item 2: the one call resumes Codex and the existing wait judges it ─


def _call(runtime: Runtime, session: Session, answer: Path, brief: str = "Read the note") -> Call:
    at = datetime.now(UTC)
    result = runtime.call(session, brief=brief, name=session.name, answer=str(answer))
    assert result.verdict == LaunchVerdict.ALIVE and result.session is not None, result.reason
    return runtime.store.record_call(
        session_id=result.session.session_id,
        slot=result.session.slot,
        name=result.session.name,
        note="/srv/note.md",
        answer=str(answer),
        brief=brief,
        caller="/srv",
        at=at,
    )


def test_the_call_resumes_the_rollout_with_the_brief_and_the_answer_lands_in_the_record(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    machine_floor.write_rollout(WORKER, cwd=str(tmp_path))
    machine_floor.script_codex({"then": "answer", "text": "pong, says the worker", "after": 3.0})
    answer = tmp_path / "from-01a07123-re-note.md"
    worker = runtime.colleague(WORKER)
    assert isinstance(worker, Session)

    call = _call(runtime, worker, answer, brief="Read /srv/note.md; answer in one word")

    ran = machine_floor.state()["codex_log"]
    assert len(ran) == 1 and ran[0]["id"] == WORKER
    assert ran[0]["prompt"] == "Read /srv/note.md; answer in one word"
    assert ran[0]["answer"] == str(answer), "Codex writes its last message there itself"
    assert "-s" not in ran[0]["argv"] and "danger-full-access" not in " ".join(ran[0]["argv"])
    assert call.session_id == WORKER and call.slot == "codex"

    # While it works: the one list shows the worker working, by its process.
    row = next(s for s in runtime.sessions() if s.session_id == WORKER)
    assert row.state == SessionState.WORKING and row.pid is not None
    assert row.doing is not None and row.doing.step == "exec"
    assert runtime.judge_call(call) is None, "nothing yet, the worker is at work"

    until(lambda: runtime.judge_call(call) is not None, seconds=6.0)
    verdict = runtime.judge_call(call)
    assert verdict is not None and verdict.outcome == CallOutcome.LANDED
    assert "pong, says the worker" in verdict.words
    assert answer.read_text(encoding="utf-8") == "pong, says the worker"

    until(lambda: next(s for s in runtime.sessions() if s.session_id == WORKER).pid is None)
    row = next(s for s in runtime.sessions() if s.session_id == WORKER)
    assert row.state == SessionState.ENDED, "removed or ended truthfully afterward"


def test_a_worker_that_answers_before_the_launch_is_verified_still_lands(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    machine_floor.write_rollout(WORKER, cwd=str(tmp_path))
    machine_floor.script_codex({"then": "answer", "text": "quick", "after": 0.1})
    answer = tmp_path / "a.md"
    worker = runtime.colleague(WORKER)
    assert isinstance(worker, Session)

    call = _call(runtime, worker, answer)

    verdict = runtime.judge_call(call)
    assert verdict is not None and verdict.outcome == CallOutcome.LANDED, verdict


def test_a_worker_that_ends_with_nothing_is_reported_ended_not_silently_empty(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    machine_floor.write_rollout(WORKER, cwd=str(tmp_path))
    machine_floor.script_codex({"then": "silent", "after": 1.3})
    answer = tmp_path / "a.md"
    worker = runtime.colleague(WORKER)
    assert isinstance(worker, Session)

    call = _call(runtime, worker, answer)

    until(lambda: runtime.judge_call(call) is not None, seconds=6.0)
    verdict = runtime.judge_call(call)
    assert verdict is not None and verdict.outcome == CallOutcome.ENDED
    assert "without its note" in verdict.words


def test_a_launch_that_fails_leaves_no_running_call(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    machine_floor.write_rollout(WORKER, cwd=str(tmp_path))
    machine_floor.script_codex({"then": "fail", "stderr": "error: no session found for that id"})
    worker = runtime.colleague(WORKER)
    assert isinstance(worker, Session)

    result = runtime.call(worker, brief="a question", name=worker.name, answer=str(tmp_path / "a"))

    assert result.verdict == LaunchVerdict.DEAD
    assert "without an answer" in (result.reason or "")
    assert "no session found" in (result.reason or "")
    assert result.attempts and result.attempts[0].rung.slot == "codex"
    assert runtime.store.calls(open_only=True) == []
    assert runtime.store.session_slot(WORKER) is None


def test_a_codex_worker_is_stopped_by_signal_and_never_moved(
    machine_floor: Floor, runtime: Runtime, tmp_path: Path
):
    machine_floor.write_rollout(WORKER, cwd=str(tmp_path))
    machine_floor.script_codex({"then": "linger"})
    worker = runtime.colleague(WORKER)
    assert isinstance(worker, Session)
    result = runtime.call(worker, brief="stay", name=worker.name, answer=str(tmp_path / "a"))
    assert result.verdict == LaunchVerdict.ALIVE and result.session is not None
    assert result.session.pid is not None

    moved = runtime.move(WORKER[:8], None)
    assert moved.verdict == LaunchVerdict.DEAD and "does not move it" in (moved.reason or "")

    stopped = runtime.stop(WORKER[:8])
    assert stopped.gone and stopped.slot == "codex"
    until(lambda: next(s for s in runtime.sessions() if s.session_id == WORKER).pid is None)


# ── item 3: one session list shows Codex doing ─────────────────────────


def test_mixed_rows_render_in_one_list_and_a_bad_rollout_hides_nothing(
    machine_floor: Floor, runtime: Runtime
):
    claude = machine_floor.write_job("alpha", "aaaa1111", state="working", detail="thinking")
    machine_floor.write_process("alpha", claude, os.getpid())
    machine_floor.write_rollout(WORKER, cwd="/srv/w", tool="exec", tool_input=SECRET)
    machine_floor.write_rollout(CHAIR, source="cli", cwd="/srv/c", mid_turn=True, tool="wait")
    machine_floor.write_rollout(OLDER, malformed=True)
    stale = machine_floor.write_rollout(
        "01a07000-0000-7000-8000-000000000009", started_at="2026-09-04T01:00:00.000Z"
    )
    two_days = time.time() - 2 * 24 * 3600
    os.utime(stale, (two_days, two_days))
    busy = a_process_on(CHAIR)
    try:
        rows = {s.session_id: s for s in runtime.sessions()}
    finally:
        end(busy)

    assert rows[claude].slot == "alpha" and rows[claude].state == SessionState.WORKING
    worker = rows[WORKER]
    assert worker.slot == "codex" and worker.state == SessionState.ENDED and worker.pid is None
    assert worker.name == "codex-01a07123" and worker.cwd == "/srv/w"
    assert worker.doing is None, "an ended session is not doing anything"
    chair = rows[CHAIR]
    assert chair.kind == SessionKind.INTERACTIVE and chair.state == SessionState.WORKING
    assert chair.doing is not None and chair.doing.step == "wait"
    assert chair.recorded == "cli", "the rollout's own source word"
    assert OLDER not in rows, "a malformed rollout is skipped"
    assert "01a07000-0000-7000-8000-000000000009" not in rows, "an old, ended rollout is not listed"


def test_doing_is_the_tools_name_and_never_its_input(machine_floor: Floor, runtime: Runtime):
    machine_floor.write_rollout(WORKER, tool="exec", tool_input=SECRET, mid_turn=True)
    busy = a_process_on(WORKER)
    try:
        row = next(s for s in runtime.sessions() if s.session_id == WORKER)
    finally:
        end(busy)
    assert row.doing is not None and row.doing.step == "exec"
    assert "credentials" not in row.model_dump_json()
    assert row.intent == "" and row.detail == ""


def test_a_rollout_that_vanishes_between_the_listing_and_the_read_hides_nothing(
    machine_floor: Floor, runtime: Runtime, monkeypatch: pytest.MonkeyPatch
):
    kept = machine_floor.write_rollout(WORKER)
    gone = machine_floor.write_rollout(OLDER, started_at="2026-09-05T08:00:00.000Z")
    real = codex._rollout_of

    def vanishing(path: Path):
        if path == gone:
            gone.unlink(missing_ok=True)
        return real(path)

    monkeypatch.setattr(codex, "_rollout_of", vanishing)
    rows = {s.session_id for s in runtime.sessions()}
    assert WORKER in rows and OLDER not in rows and kept.exists()


def test_an_older_rollout_is_reached_by_id_though_not_listed(
    machine_floor: Floor, runtime: Runtime
):
    old = machine_floor.write_rollout(OLDER, started_at="2026-09-01T08:00:00.000Z")
    ago = time.time() - 5 * 24 * 3600
    os.utime(old, (ago, ago))
    assert OLDER not in {s.session_id for s in runtime.sessions()}
    found = runtime.colleague(OLDER)
    assert isinstance(found, Session) and found.session_id == OLDER
