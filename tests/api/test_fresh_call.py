"""A call reaches a colleague fit to answer, and can ask for a fresh one
(card #110, item 5), on the floor: `needle call codex --fresh` starts a new
thread of the other make at the effort named, records it as a row and
`needle wait` lands its answer; a bare-name call says first which session it
picked, at what effort and in what sandbox; and a turn that ends on a tool
error is reported as that error, never as a colleague that finished without
its note (the carried defect's two failures)."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from tests.api import test_doors as doors
from tests.api.test_calls import WORKER, a_note
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


def test_a_fresh_call_starts_a_new_thread_records_it_and_wait_lands_the_answer(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, monkeypatch
):
    monkeypatch.chdir(repo)
    machine_floor.write_rollout(WORKER, cwd=str(repo), effort="low", sandbox="workspace-write")
    shaped = '{"answer": "The premise holds.", "how_known": "checked", "sources": ["engine"]}'
    machine_floor.script_codex({"then": "answer", "text": shaped, "after": 1.5})
    note = a_note(machine_floor)
    assert main(["call", "codex", str(note), "--fresh", "--objective", "Break it."]) == 0
    said = capsys.readouterr().out
    assert said.startswith("call 1: a fresh codex thread "), said
    assert "effort high, sandbox read-only" in said and "wait for it: needle wait 1" in said
    ran = machine_floor.state()["codex_log"]
    assert len(ran) == 1 and ran[0]["fresh"] is True, "a new thread, not a resume"
    assert ran[0]["id"] != WORKER
    argv = ran[0]["argv"]
    assert "read-only" in argv and "model_reasoning_effort=high" in argv
    assert argv[argv.index("-C") + 1] == str(repo)
    assert ran[0]["prompt"].startswith(f"A colleague calls you with a question. Read {note} first")
    assert "Break it." in ran[0]["prompt"]
    store = client.app.state.loops.live.store
    row = store.call(1)
    assert row is not None and row.slot == "codex" and row.session_id == ran[0]["id"]
    assert Path(row.answer).name.startswith("from-codex-fresh-")

    assert main(["wait", "1", "--ceiling", "10"]) == 0
    said = capsys.readouterr().out
    assert said.startswith("landed: ") and said.rstrip().endswith("The premise holds.")
    # The row holds the answer's words from the wait, before the loop's next
    # beat (the cold read of round eleven), so a close can quote it at once.
    ended = store.call(1)
    assert ended is not None and ended.ended_at is not None
    assert ended.words is not None and ended.words.endswith("The premise holds.")


def test_a_fresh_call_names_the_other_make_and_a_low_effort_is_named(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, monkeypatch
):
    monkeypatch.chdir(repo)
    note = a_note(machine_floor)
    assert main(["call", "alpha", str(note), "--fresh"]) == 1
    assert "call codex --fresh" in capsys.readouterr().err
    machine_floor.script_codex({"then": "answer", "text": "words", "after": 0.5})
    assert main(["call", "codex", str(note), "--fresh", "--effort", "low"]) == 0
    assert "effort low" in capsys.readouterr().out
    assert "model_reasoning_effort=low" in machine_floor.state()["codex_log"][0]["argv"]


def test_a_bare_name_call_says_first_which_session_it_picked_and_what_it_ran_at(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    machine_floor.write_rollout(WORKER, cwd=str(repo), effort="none", sandbox="read-only")
    machine_floor.script_codex({"then": "answer", "text": "the answer", "after": 0.5})
    note = a_note(machine_floor)
    assert main(["call", "codex", str(note)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == (
        "picked 01a07123, the most recent codex worker; its latest turn ran at effort unknown "
        "in sandbox read-only — name a session id to choose another, or --fresh for a new "
        "thread at the effort you name"
    ), lines[0]
    assert lines[1].startswith("call 1: 01a07123 is working on")

    machine_floor.write_rollout(
        "01a07999-7d89-78f3-ad15-ee875e35a4c8",
        cwd=str(repo),
        effort="high",
        sandbox="workspace-write",
        started_at="2026-09-05T10:00:00.000Z",
    )
    machine_floor.script_codex({"then": "answer", "text": "the answer", "after": 0.5})
    assert main(["call", "codex", str(note)]) == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith(
        "picked 01a07999, the most recent codex worker; its latest turn ran at effort high "
    )
    assert "workspace-write" in first


def test_a_turn_that_ends_on_a_tool_error_is_reported_as_that_error(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    rollout = machine_floor.write_rollout(WORKER, cwd=str(repo), effort="high", sandbox="read-only")
    machine_floor.script_codex(
        {"then": "error", "after": 2.5, "error": "collab spawn failed: no thread with id: 01a07bcf"}
    )
    note = a_note(machine_floor)
    assert main(["call", WORKER[:8], str(note)]) == 0
    capsys.readouterr()
    # A resumed turn opens with its own context, carried over from the last
    # (the cold read of round four): the row still says what it runs at.
    assert rollout.read_text(encoding="utf-8").count('"turn_context"') == 2
    picked = next(s for s in client.app.state.loops.runtime.sessions() if s.short_id == WORKER[:8])
    assert (
        picked.effort is not None
        and picked.effort.value == "high"
        and picked.sandbox == "read-only"
    )
    started = time.monotonic()
    assert main(["wait", "1", "--ceiling", "20"]) == 1
    assert time.monotonic() - started < 10, "the truth came before the ceiling"
    said = capsys.readouterr().out
    assert said.startswith(
        "ended: 01a07123's turn ended on a tool error, with no final message: "
    ), said
    assert "collab spawn failed: no thread with id: 01a07bcf" in said
    assert "without its note" not in said


def test_a_resumed_turn_keeps_a_missing_setting_missing(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    """Pass two's reader: the fake's resume carried an earlier turn's word
    into a latest context whose effort was null, concealing an absent
    setting from every test reading the row. A real worker's context
    carried effort null on 2026-09-07; the row says unknown for it."""
    import json

    rollout = machine_floor.write_rollout(WORKER, cwd=str(repo), effort="high", sandbox="read-only")
    with rollout.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "type": "turn_context",
                    "payload": {"turn_id": "t2", "effort": None, "sandbox_policy": {"type": None}},
                }
            )
            + "\n"
        )
    machine_floor.script_codex({"then": "answer", "text": "words", "after": 0.5})
    note = a_note(machine_floor)
    assert main(["call", WORKER[:8], str(note)]) == 0
    capsys.readouterr()
    contexts = [
        json.loads(line)["payload"]
        for line in rollout.read_text(encoding="utf-8").splitlines()
        if '"turn_context"' in line
    ]
    assert len(contexts) == 3 and contexts[-1]["effort"] is None
    assert contexts[-1]["sandbox_policy"]["type"] is None
    picked = next(s for s in client.app.state.loops.runtime.sessions() if s.short_id == WORKER[:8])
    assert picked.effort is None and picked.sandbox is None
