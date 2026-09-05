"""Calling a colleague warm (plan 17), on the floor: the verb resumes a named
session with the brief through the one launch path, refuses what it cannot
truthfully do, follows a colleague no registry holds by its transcript, and
the judge that `needle wait` and the loop share reads the call's state from
the one list and the answer file. Also what the registry now says about a
session — what it resumed from and what it is doing — and the notes on the
machine's watercooler as the board reads them."""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from domain.call import Call, CallOutcome
from domain.gate import Gate
from domain.launch import LaunchVerdict, WindowlessStart
from domain.session import Doing, Session, SessionKind, SessionState
from domain.slot import Handoff, Model
from runtime import calls, discussion, launch, machine, transcripts
from runtime.service import Runtime
from tests.floor import Floor

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


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


def colleague(runtime: Runtime, repo: Path, floor: Floor, *fates: dict) -> Session:
    """A background session in the repository's checkout, with the fates scripted."""
    floor.script_launches(*fates)
    started = runtime.start_windowless(
        WindowlessStart(repo=str(repo), card="colleague-x", brief="be there", effort=Gate.HIGH)
    )
    assert started.verdict == LaunchVerdict.ALIVE and started.session is not None, started.reason
    return started.session


def until(predicate, seconds: float = 4.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    assert predicate()


def session(
    *,
    state: SessionState = SessionState.WORKING,
    pid: int | None = 4242,
    kind: SessionKind = SessionKind.BACKGROUND,
    session_id: str = "aaaa0001-0000-4000-8000-000000000000",
    resumed_from: str | None = None,
    wall: Handoff | None = None,
    detail: str = "",
    slot: str = "alpha",
) -> Session:
    return Session(
        slot=slot,
        config_dir="/x",
        short_id=session_id.split("-")[0],
        session_id=session_id,
        kind=kind,
        name="colleague-x",
        cwd="/srv/p",
        worktree=None,
        state=state,
        recorded=state.value,
        detail=detail,
        pid=pid,
        scope=None,
        model=Model.FABLE,
        effort=None,
        stale=False,
        wall=wall,
        intent="",
        created_at=NOW,
        updated_at=NOW,
        resumed_from=resumed_from,
        doing=None,
    )


def a_call(tmp_path: Path, *, session_id: str = "aaaa0001-0000-4000-8000-000000000000") -> Call:
    return Call(
        id=1,
        session_id=session_id,
        slot="alpha",
        name="colleague-x",
        note=str(tmp_path / "from-codex-topic.md"),
        answer=str(tmp_path / "from-aaaa0001-re-topic.md"),
        brief="read the note",
        caller="/srv/chair",
        called_at=datetime.now(UTC) - timedelta(seconds=1),
        moved=None,
        ended_at=None,
        words=None,
    )


# ── the verb ───────────────────────────────────────────────────────────


def test_a_call_resumes_a_colleague_whose_turn_is_done_with_the_brief_and_nothing_else_runs(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    first = colleague(
        runtime, repo, machine_floor, {"then": "done", "after": 0.3}, {"then": "work"}
    )
    until(lambda: runtime.session(first.short_id).state == SessionState.DONE)

    who = runtime.colleague(first.short_id)
    assert isinstance(who, Session)
    result = runtime.call(
        who,
        brief="Read /srv/d/from-codex.md and answer",
        name=who.name,
        answer="/srv/d/from-x-re-codex.md",
    )

    assert result.verdict == LaunchVerdict.ALIVE and result.session is not None, result.reason
    log = machine_floor.state()["launch_log"]
    assert len(log) == 2, "the runtime's launch path and nothing beside it"
    resumed = log[1]["argv"]
    assert resumed[resumed.index("--resume") + 1] == first.session_id
    assert resumed[-1] == "Read /srv/d/from-codex.md and answer", "the brief is the first request"
    assert result.session.resumed_from == first.session_id, "the registry says what it resumed"
    assert machine_floor.state()["stops"][0]["short"] == first.short_id
    alive = [s for s in runtime.sessions() if s.pid is not None and s.name == "colleague-x"]
    assert len(alive) == 1, "never resumed beside itself"


def test_a_call_refuses_a_terminal_a_turn_in_flight_and_an_empty_brief(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    working = colleague(runtime, repo, machine_floor, {"then": "work"})
    refused = runtime.call(working, brief="a question", name=working.name, answer="/srv/d/a.md")
    assert refused.verdict == LaunchVerdict.DEAD and "working on its turn" in (refused.reason or "")

    empty = runtime.call(working, brief="   ", name=working.name, answer="/srv/d/a.md")
    assert empty.verdict == LaunchVerdict.DEAD and "empty brief" in (empty.reason or "")

    terminal_id = "eeee0001-0000-4000-8000-000000000000"
    machine_floor.write_process("beta", terminal_id, os.getpid(), kind="cli", cwd="/srv/p")
    terminal = runtime.colleague("eeee0001")
    assert isinstance(terminal, Session) and terminal.kind == SessionKind.INTERACTIVE
    no = runtime.call(terminal, brief="a question", name=terminal.name, answer="/srv/d/a.md")
    assert no.verdict == LaunchVerdict.DEAD and "terminal of its own" in (no.reason or "")
    assert len(machine_floor.state()["launch_log"]) == 1, "no second process for any refusal"


def test_a_colleague_no_registry_holds_is_resumed_from_its_transcript_by_id(
    machine_floor: Floor, runtime: Runtime, repo: Path, monkeypatch: pytest.MonkeyPatch
):
    gone = "6f059ca0-0000-4000-8000-000000000000"
    path = machine.transcript_path(str(repo), gone)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"type": "summary", "sessionId": gone})
        + "\n"
        + json.dumps({"type": "user", "cwd": str(repo), "sessionId": gone, "message": {}})
        + "\n",
        encoding="utf-8",
    )
    assert runtime.colleague("nobody") is None
    who = runtime.colleague(gone)
    assert who == (gone, str(repo)), "found by id, its directory read from its own records"

    result = runtime.call(who, brief="Read the note", name="call-6f059ca0", answer="/srv/d/a.md")
    assert result.verdict == LaunchVerdict.ALIVE and result.session is not None, result.reason
    launched = machine_floor.state()["launch_log"][0]
    assert launched["argv"][launched["argv"].index("--resume") + 1] == gone
    assert launched["cwd"] == str(repo) and launched["argv"][-1] == "Read the note"
    assert result.session.resumed_from == gone

    monkeypatch.setattr(launch, "RESUME_SIZE_LIMIT", 10)
    too_big = runtime.call(who, brief="again", name="call-6f059ca0", answer="/srv/d/a.md")
    assert too_big.verdict == LaunchVerdict.DEAD and "above the" in (too_big.reason or "")


def test_a_slot_named_is_its_most_recent_background_session(machine_floor: Floor, runtime: Runtime):
    older = machine_floor.write_job("beta", "bbbb0001", updated_at="2026-09-05T09:00:00Z")
    newer = machine_floor.write_job("beta", "bbbb0002", updated_at="2026-09-05T11:00:00Z")
    machine_floor.write_process("beta", newer, os.getpid(), kind="bg", status="busy")
    who = runtime.colleague("beta")
    assert isinstance(who, Session) and who.session_id == newer and who.session_id != older


# ── the judge ──────────────────────────────────────────────────────────


def test_the_judge_reads_landed_moved_blocked_ended_and_nothing(tmp_path: Path):
    call = a_call(tmp_path)
    working = session()
    assert calls.judge(call, [working], why_ended=None, moved_words=None) is None

    Path(call.answer).write_text("# From the colleague\n\nthe answer\n", encoding="utf-8")
    landed = calls.judge(call, [working], why_ended=None, moved_words=None)
    assert landed is not None and landed.outcome == CallOutcome.LANDED
    assert landed.words.endswith("# From the colleague") and call.answer in landed.words
    Path(call.answer).unlink()

    fork = session(
        session_id="bbbb0002-0000-4000-8000-000000000000", resumed_from=call.session_id, slot="beta"
    )
    dead = session(pid=None, state=SessionState.ENDED)
    moved = calls.judge(call, [dead, fork], why_ended=None, moved_words="You've reached your limit")
    assert moved is not None and moved.outcome == CallOutcome.MOVED
    assert moved.session_id == fork.session_id and moved.slot == "beta"
    assert "moved to beta as bbbb0002: You've reached your limit" in moved.words

    wall = Handoff(
        session_id=call.session_id,
        short_id="aaaa0001",
        from_slot="alpha",
        account="beta",
        model=None,
        prompt="Carry on.",
        reason="You've reached your Fable limit.",
        at=NOW,
        cwd="/srv/p",
        worktree=None,
        pid=4242,
        stopped=False,
        path=str(tmp_path / "h.json"),
    )
    walled = calls.judge(
        call, [session(state=SessionState.BLOCKED, wall=wall)], why_ended=None, moved_words=None
    )
    assert walled is not None and walled.outcome == CallOutcome.BLOCKED
    assert "hit a limit on alpha: You've reached your Fable limit." in walled.words

    asking = calls.judge(
        call,
        [session(state=SessionState.BLOCKED, detail="asking: which?")],
        why_ended=None,
        moved_words=None,
    )
    assert (
        asking is not None
        and asking.outcome == CallOutcome.BLOCKED
        and "asking: which?" in asking.words
    )

    ended = calls.judge(call, [dead], why_ended="the journal says: Killed", moved_words=None)
    assert ended is not None and ended.outcome == CallOutcome.ENDED
    assert "ended without its note: the journal says: Killed" in ended.words

    done = calls.judge(call, [session(state=SessionState.DONE)], why_ended=None, moved_words=None)
    assert done is not None and done.outcome == CallOutcome.ENDED
    assert "finished its turn without its note" in done.words

    nobody = calls.judge(call, [], why_ended=None, moved_words=None)
    assert (
        nobody is not None and nobody.outcome == CallOutcome.ENDED and "no registry" in nobody.words
    )


def test_an_answer_written_before_the_call_is_not_the_answer(tmp_path: Path):
    call = a_call(tmp_path)
    Path(call.answer).write_text("old\n", encoding="utf-8")
    old = time.time() - 60
    os.utime(call.answer, (old, old))
    assert calls.answer_landed(call) is None
    Path(call.answer).write_text("old\nnew\n", encoding="utf-8")
    assert calls.answer_landed(call) is not None


# ── the registry's two new facts ───────────────────────────────────────


def _record(kind: str, blocks: list, *, stamp: str, sidechain: bool = False) -> str:
    return json.dumps(
        {
            "type": kind,
            "isSidechain": sidechain,
            "timestamp": stamp,
            "message": {"role": kind, "content": blocks},
        }
    )


def _tool(name: str, **given) -> dict:
    return {"type": "tool_use", "id": "t", "name": name, "input": given}


def test_the_registry_says_what_a_session_resumed_from_and_what_a_live_one_is_doing(
    machine_floor: Floor, runtime: Runtime
):
    origin = machine_floor.write_job("alpha", "aaaa0001", state="done")
    fork = machine_floor.write_job("alpha", "aaaa0002", resumed_from=origin, cwd="/srv/p")
    machine_floor.write_process("alpha", fork, os.getpid(), cwd="/srv/p")
    path = machine.transcript_path("/srv/p", fork)
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                _record(
                    "assistant",
                    [_tool("Read", file_path="/srv/p/a.md")],
                    stamp="2026-09-05T10:00:00.000Z",
                ),
                _record(
                    "assistant",
                    [_tool("Bash", command="ls\nls -a", description="list")],
                    stamp="2026-09-05T10:00:05.000Z",
                ),
                _record(
                    "assistant",
                    [_tool("Grep", pattern="x")],
                    stamp="2026-09-05T10:00:09.000Z",
                    sidechain=True,
                ),
                _record(
                    "assistant",
                    [{"type": "text", "text": "done"}],
                    stamp="2026-09-05T10:00:10.000Z",
                ),
                "not json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows = {s.session_id: s for s in runtime.sessions()}
    assert rows[origin].resumed_from is None and rows[origin].doing is None, (
        "an ended row does nothing"
    )
    assert rows[fork].resumed_from == origin
    assert rows[fork].doing == Doing(
        step="Bash ls", at=datetime(2026, 9, 5, 10, 0, 5, tzinfo=UTC)
    ), "the last main-thread tool use, never a subagent's"


def test_a_transcript_tail_without_a_tool_use_is_no_step():
    assert transcripts.last_step("/nowhere", "nobody") is None


# ── the machine's watercooler, read ────────────────────────────────────


def test_the_notes_are_read_oldest_change_first_with_their_first_lines(machine_floor: Floor):
    first = machine_floor.discussion / "from-codex-topic.md"
    first.write_text("# From Codex — the ask\n\nbody\n", encoding="utf-8")
    old = time.time() - 30
    os.utime(first, (old, old))
    second = machine_floor.discussion / "from-claude-topic.md"
    second.write_text("\n# From Claude\n", encoding="utf-8")
    (machine_floor.discussion / "notes.txt").write_text("not a note", encoding="utf-8")
    notes = discussion.notes()
    assert [n.path for n in notes] == [str(first), str(second)]
    assert notes[0].first_line == "# From Codex — the ask" and notes[1].first_line == ""
    assert notes[0].at < notes[1].at

    text = (
        "read `~/.cache/omarchy/claude-acct/discussion/from-codex-topic.md` and "
        f"{machine_floor.discussion}/from-x.md; not docs/discussion.md"
    )
    assert discussion.named_in(text) == {str(first), str(machine_floor.discussion / "from-x.md")}
    assert discussion.in_directory(str(first)) and not discussion.in_directory("/tmp/from-x.md")
