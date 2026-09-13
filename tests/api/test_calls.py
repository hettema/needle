"""Asking a colleague takes a minute, not ten, and nobody waits blind (plan
17), on the served board over the floor: a lane whose card names a note on
the machine's watercooler hears the note as its word, once, and never its
own; `needle call` resumes a colleague warm with the note as its brief and
`needle wait` returns within a second of the answer landing, before the
ceiling when the colleague ends without it, and with the wall's reason when
it is blocked; the loop tends a call — a walled colleague nobody else tends
is moved once and the call follows the fork, and a second wall within the
hour parks."""

import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from domain.gate import Gate
from domain.launch import LaunchVerdict, WindowlessStart
from domain.session import SessionState
from runtime.service import Runtime
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, lane_path, reconcile, start
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


def word(
    client: TestClient, cwd: str, wrote: str | None = None, session: str | None = None
) -> list[str]:
    params = {"cwd": cwd}
    if wrote:
        params["wrote"] = wrote
    if session:
        params["session"] = session
    response = client.get("/api/word", params=params)
    assert response.status_code == 200, response.text
    return response.json()["sentences"]


def plan_of(repo: Path, number: int = CARD) -> Path:
    for path in (repo / "docs" / "plans").glob("*.md"):
        if "metered" in path.name:
            return path
    raise AssertionError(f"no plan for #{number} in the fixture")


def colleague(client: TestClient, repo: Path, floor: Floor, *fates: dict) -> str:
    """A background session in the checkout whose turn is done: a colleague
    that can be called. Answers its short id."""
    floor.script_launches(*fates)
    runtime = Runtime(client.app.state.loops.live.store)
    started = runtime.start_windowless(
        WindowlessStart(repo=str(repo), card="colleague-x", brief="be there", effort=Gate.HIGH)
    )
    assert started.verdict == LaunchVerdict.ALIVE and started.session is not None, started.reason
    short = started.session.short_id
    deadline = time.monotonic() + 4
    while runtime.session(short).state != SessionState.DONE:
        assert time.monotonic() < deadline, "the colleague never finished its turn"
        time.sleep(0.1)
    return short


def a_note(floor: Floor, text: str = "# From Codex — the ask\n\nWhich of the two?\n") -> Path:
    path = floor.discussion / "from-codex-topic.md"
    path.write_text(text, encoding="utf-8")
    return path


# ── item 2: a lane hears a note ────────────────────────────────────────


def test_a_lane_whose_card_names_a_note_hears_it_once_and_never_its_own(
    client: TestClient, machine_floor: Floor, repo: Path
):
    plan = plan_of(repo)
    plan.write_text(
        plan.read_text(encoding="utf-8")
        + "\nThe thread is `~/.cache/omarchy/claude-acct/discussion/from-codex-topic.md`.\n",
        encoding="utf-8",
    )
    start(client)
    reconcile(client)
    lane = lane_path(repo)
    assert word(client, lane) == [], "nothing on the machine's watercooler yet"

    note = a_note(machine_floor)
    reconcile(client)
    assert word(client, lane) == [
        f"A note landed on the machine's watercooler: {note} — # From Codex — the ask"
    ]
    assert word(client, lane) == [], "said once"

    # The lane appends its reply under the same head (the 09:15 shape):
    # its own write, named by the hook, is never read back to it.
    note.write_text(note.read_text(encoding="utf-8") + "\n# From the lane\n\nthe first.\n")
    reconcile(client)
    assert word(client, lane, wrote=str(note)) == []
    assert word(client, lane) == []

    time.sleep(0.02)
    note.write_text(note.read_text(encoding="utf-8") + "\n# From Codex — again\n\nthanks.\n")
    os.utime(note, None)
    reconcile(client)
    assert word(client, lane) == [
        f"A note changed on the machine's watercooler: {note} — # From Codex — the ask"
    ]

    other = machine_floor.discussion / "from-codex-other.md"
    other.write_text("# elsewhere\n", encoding="utf-8")
    reconcile(client)
    assert word(client, lane) == [], "a note the card does not name is not the lane's"


# ── items 1 and 2: call and wait from the command line ─────────────────


def test_call_resumes_the_colleague_with_the_note_and_wait_returns_as_the_answer_lands(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    short = colleague(client, repo, machine_floor, {"then": "done", "after": 0.3}, {"then": "work"})
    note = a_note(machine_floor)
    answer = machine_floor.discussion / "from-lane-re-topic.md"

    assert (
        main(["call", short, str(note), "--objective", "Say which.", "--answer", str(answer)]) == 0
    )
    said = capsys.readouterr().out
    assert said.startswith("call 1: ") and f"the answer lands in {answer}" in said
    assert "wait for it: needle wait 1" in said
    log = machine_floor.state()["launch_log"]
    assert len(log) == 2
    brief = log[1]["argv"][-1]
    assert brief.startswith(f"A colleague calls you with a question. Read {note} first")
    assert "Say which." in brief and f"write your reply to {answer}" in brief
    store = client.app.state.loops.live.store
    call = store.call(1)
    assert call is not None and call.session_id == log[1]["session_id"] and call.note == str(note)

    def reply() -> None:
        time.sleep(0.6)
        answer.write_text("# From the colleague\n\nThe second.\n", encoding="utf-8")

    threading.Thread(target=reply, daemon=True).start()
    started = time.monotonic()
    assert main(["wait", "1", "--ceiling", "5"]) == 0
    took = time.monotonic() - started
    assert took < 2.0, f"the answer landed at 0.6 s and the wait returned at {took:.1f} s"
    said = capsys.readouterr().out
    assert said.startswith(f"landed: {answer} landed at ") and said.rstrip().endswith(
        "# From the colleague (prose, its first line)"
    ), "a Claude colleague's prose lands as before, read by its first line and said so (card #73)"

    reconcile(client)
    ended = store.call(1)
    assert ended is not None and ended.ended_at is not None and ended.words is not None
    assert ended.words.startswith(f"{answer} landed at "), "the loop read the same landing"
    assert main(["wait", "1", "--ceiling", "1"]) == 0, "a landed answer is landed on every wait"
    assert main(["wait", "9", "--ceiling", "1"]) == 1
    assert "no call 9 is recorded" in capsys.readouterr().err


def test_a_wait_returns_before_the_ceiling_when_the_colleague_ends_without_its_note(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    short = colleague(
        client, repo, machine_floor, {"then": "done", "after": 0.3}, {"then": "done", "after": 1.5}
    )
    note = a_note(machine_floor)
    assert main(["call", short, str(note)]) == 0
    capsys.readouterr()
    started = time.monotonic()
    assert main(["wait", "1", "--ceiling", "20"]) == 1
    assert time.monotonic() - started < 8, "the ceiling was twenty seconds; the truth came first"
    said = capsys.readouterr().out
    assert said.startswith("ended: ") and "finished its turn without its note" in said

    assert main(["call", "nobody", str(note)]) == 1
    assert "no session 'nobody'" in capsys.readouterr().err
    assert main(["call", short, str(machine_floor.discussion / "missing.md")]) == 1
    assert "is not a file" in capsys.readouterr().err


def test_a_walled_colleague_is_moved_once_the_call_follows_and_a_second_wall_parks(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    # The colleague blocks first without the wall detector's file (a
    # question, or the moment before the hook writes it): the loop leaves
    # it and a waiter is told; then the file appears and the loop moves it.
    short = colleague(
        client,
        repo,
        machine_floor,
        {"then": "done", "after": 0.3},
        {
            "then": "wall",
            "after": 2.5,
            "reason": "You've reached your Fable limit.",
            "no_handoff": True,
        },
        {"then": "work"},
    )
    note = a_note(machine_floor)
    assert main(["call", short, str(note)]) == 0
    capsys.readouterr()
    store = client.app.state.loops.live.store
    called = store.call(1)
    assert called is not None
    time.sleep(3.0)

    assert main(["wait", "1", "--ceiling", "5"]) == 1
    said = capsys.readouterr().out
    assert said.startswith("blocked: ") and "is blocked: You've reached your Fable limit." in said
    reconcile(client)
    assert len(machine_floor.state()["launch_log"]) == 2, "a question is nobody's to move"

    runtime = Runtime(store)
    blocked = runtime.session(called.session_id)
    machine_floor.write_handoff(
        called.session_id, **{"from": "alpha"}, account="beta", pid=blocked.pid
    )
    assert main(["wait", "1", "--ceiling", "5"]) == 1
    said = capsys.readouterr().out
    assert (
        said.startswith("blocked: ")
        and "hit a limit on alpha: You've reached your Fable limit." in said
    )

    reconcile(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == 3, "one hop, by the loop"
    assert log[2]["argv"][log[2]["argv"].index("--resume") + 1] == called.session_id
    moved = store.call(1)
    assert moved is not None and moved.ended_at is None
    assert moved.session_id == log[2]["session_id"] and moved.slot == "beta"
    assert moved.moved is not None and moved.moved.startswith(
        # The handoff names beta and no model, so beta is said alone (card #63).
        "colleague-x moved to beta as "
    )
    alive = [s for s in runtime.sessions() if s.pid is not None and s.name == "colleague-x"]
    assert len(alive) == 1, "one call, one colleague"

    # A second wall inside the hour: the handoff names the new session.
    machine_floor.write_handoff(
        moved.session_id, **{"from": "beta"}, account="alpha", pid=alive[0].pid
    )
    reconcile(client)
    assert len(machine_floor.state()["launch_log"]) == 3, "parked, not thrashed"
    parked = store.call(1)
    assert parked is not None and parked.ended_at is not None and parked.words is not None
    assert "hit a limit again within the hour" in parked.words
    assert main(["wait", "1", "--ceiling", "5"]) == 1
    assert "hit a limit again within the hour" in capsys.readouterr().out


def test_a_lane_party_by_a_call_hears_the_answer_as_its_word(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, monkeypatch: pytest.MonkeyPatch
):
    start(client)
    reconcile(client)
    lane = lane_path(repo)
    short = colleague(client, repo, machine_floor, {"then": "done", "after": 0.3}, {"then": "work"})
    note = a_note(machine_floor)
    answer = machine_floor.discussion / "from-colleague-re-topic.md"
    monkeypatch.chdir(lane)
    assert main(["call", short, str(note), "--answer", str(answer)]) == 0
    capsys.readouterr()
    reconcile(client)
    assert word(client, lane) == [
        f"A note landed on the machine's watercooler: {note} — # From Codex — the ask"
    ], "the lane that called is party to the note it called with"
    answer.write_text("# From the colleague\n", encoding="utf-8")
    reconcile(client)
    assert word(client, lane) == [
        f"A note landed on the machine's watercooler: {answer} — # From the colleague"
    ]


# ── plan 57: the same two verbs reach a colleague of the other make ────

WORKER = "01a07123-7d89-78f3-ad15-ee875e35a4c8"


def test_call_codex_resumes_the_worker_and_wait_returns_as_its_last_message_lands(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    machine_floor.write_rollout(WORKER, cwd=str(repo))
    shaped = '{"answer": "The second.", "how_known": "checked", "sources": ["the note"]}'
    machine_floor.script_codex({"then": "answer", "text": shaped, "after": 4.0})
    note = a_note(machine_floor)
    answer = machine_floor.discussion / "from-01a07123-re-topic.md"

    started = time.monotonic()
    assert main(["call", "codex", str(note), "--objective", "Say which."]) == 0
    said = capsys.readouterr().out
    # The bare name says first which session it picked (card #110, item 5).
    assert said.startswith("picked 01a07123, the most recent codex worker; "), said
    assert "\ncall 1: 01a07123 is working on" in said, said
    assert f"the answer lands in {answer}" in said and "wait for it: needle wait 1" in said
    ran = machine_floor.state()["codex_log"]
    assert len(ran) == 1 and ran[0]["id"] == WORKER and ran[0]["answer"] == str(answer)
    brief = ran[0]["prompt"]
    assert brief.startswith(f"A colleague calls you with a question. Read {note} first")
    assert "Say which." in brief and "Answer as your final message" in brief
    assert "Do not write that file yourself" in brief
    assert "`how_known` (checked, recalled or inferred)" in brief, "asked for the one shape"
    assert ran[0]["schema"] == str(answer.with_name("from-01a07123-re-topic.schema.json"))
    assert "--output-schema" in ran[0]["argv"], "held to the shape by Codex itself"
    assert machine_floor.state()["launch_log"] == [], "no Claude session was started for it"

    assert main(["sessions"]) == 0
    listed = capsys.readouterr().out
    assert "codex     01a07123  working  background  codex-01a07123" in listed, listed

    assert main(["wait", "1", "--ceiling", "10"]) == 0
    took = time.monotonic() - started
    said = capsys.readouterr().out
    assert said.startswith(f"landed: {answer} landed at ") and said.rstrip().endswith("The second.")
    assert "(prose" not in said and "not in the shape" not in said, (
        "the verdict's words are the answer field"
    )
    assert took < 9.0, f"the answer landed at about 4 s and the wait returned at {took:.1f} s"
    assert answer.read_text(encoding="utf-8") == shaped

    reconcile(client)
    store = client.app.state.loops.live.store
    ended = store.call(1)
    assert ended is not None and ended.slot == "codex" and ended.ended_at is not None


def test_a_codex_worker_that_ends_with_nothing_is_reported_before_the_ceiling(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    machine_floor.write_rollout(WORKER, cwd=str(repo))
    machine_floor.script_codex({"then": "silent", "after": 1.5})
    note = a_note(machine_floor)
    assert main(["call", WORKER[:8], str(note)]) == 0
    capsys.readouterr()
    started = time.monotonic()
    assert main(["wait", "1", "--ceiling", "20"]) == 1
    assert time.monotonic() - started < 8, "the ceiling was twenty seconds; the truth came first"
    said = capsys.readouterr().out
    assert said.startswith("ended: ") and "without its note" in said

    machine_floor.script_codex({"then": "fail", "stderr": "error: no session found"})
    assert main(["call", WORKER[:8], str(note)]) == 1
    said = capsys.readouterr().out
    assert "not running:" in said and "no session found" in said
    store = client.app.state.loops.live.store
    assert len(store.calls()) == 1, "a launch that failed recorded no second call"


# ── items 4 and 5: the note a colleague picks up as its next word ──────


def test_a_note_reaches_a_colleague_on_no_card_and_stands_until_it_is_picked_up(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    """Card #137, items 4 and 5. Until 2026-09-13 a colleague running in a
    terminal the owner opened himself was refused by name, and the only
    other way to reach one wanted a project and a card number — so a
    colleague working on no card had no address at all, and the
    coordination the owner ordered on card #83 never happened."""
    terminal_id = "eeee0001-0000-4000-8000-000000000000"
    machine_floor.write_process("beta", terminal_id, os.getpid(), kind="cli", cwd=str(repo))
    note = a_note(machine_floor)
    answer = machine_floor.discussion / "from-terminal-re-topic.md"

    assert (
        main(["call", "eeee0001", str(note), "--objective", "Say which.", "--answer", str(answer)])
        == 0
    )
    said = capsys.readouterr().out
    assert "the note is handed to eeee0001" in said, said
    assert "terminal of its own" in said and "wait for it: needle wait 1" in said
    assert machine_floor.state()["launch_log"] == [], "nothing was launched for a note"
    assert machine_floor.state()["stops"] == [], "and nothing was stopped"

    store = client.app.state.loops.live.store
    handed = store.call(1)
    assert handed is not None and handed.handed_at is not None and handed.picked_up_at is None
    assert [c.id for c in store.notes_standing()] == [1]

    # It stands where the owner sees it, and the wait says so rather than
    # answering with silence.
    reconcile(client)
    head = client.app.state.loops.live.machine.notes
    assert len(head) == 1 and "is waiting for" in head[0], head

    assert main(["wait", "1", "--ceiling", "1"]) == 1
    waited = capsys.readouterr().out
    assert "the note was handed to" in waited and "has not been picked up" in waited

    # Its next act picks it up: the brief arrives as the session's word, in
    # a directory that is no lane of any project.
    elsewhere = str(repo)
    reached = word(client, elsewhere, session=terminal_id)
    assert len(reached) == 1 and reached[0].startswith(
        f"A colleague calls you with a question. Read {note} first"
    )
    assert f"write your reply to {answer}" in reached[0]

    again = client.get("/api/word", params={"cwd": elsewhere, "session": terminal_id})
    assert again.status_code == 404, "said once, never twice — and no lane to say anything else"
    picked = store.call(1)
    assert picked is not None and picked.picked_up_at is not None
    assert store.notes_standing() == []

    assert main(["wait", "1", "--ceiling", "1"]) == 1
    waited = capsys.readouterr().out
    assert "picked the note up at" in waited, waited


def test_a_lane_hears_a_note_handed_to_it_beside_its_own_word(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    """One word, two addresses: the lane's drift and watercooler by its
    directory, the notes handed to it by its own session id. The lane is
    mid-turn, which is exactly when a call is not resumed."""
    start(client)
    reconcile(client)
    lane = lane_path(repo)
    busy_id = "dddd0001-0000-4000-8000-000000000000"
    machine_floor.write_job("beta", "dddd0001", session_id=busy_id, cwd=lane, worktree=lane)
    machine_floor.write_process("beta", busy_id, os.getpid(), kind="bg", status="busy", cwd=lane)
    note = a_note(machine_floor)

    assert main(["call", "dddd0001", str(note)]) == 0
    assert "the note is handed to" in capsys.readouterr().out

    said = word(client, lane, session=busy_id)
    assert any("A colleague calls you with a question" in s for s in said)
    assert word(client, lane, session=busy_id) == []


def test_a_note_standing_is_never_read_as_a_colleague_that_finished_without_it(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    """An idle colleague has not finished a turn it never started: the wait
    keeps waiting on a standing note rather than ending the call."""
    terminal_id = "eeee0002-0000-4000-8000-000000000000"
    machine_floor.write_process("beta", terminal_id, os.getpid(), kind="cli", cwd=str(repo))
    note = a_note(machine_floor)
    assert main(["call", "eeee0002", str(note)]) == 0
    capsys.readouterr()

    assert main(["wait", "1", "--ceiling", "1"]) == 1
    said = capsys.readouterr().out
    assert said.startswith("nothing: "), said
    assert "has not been picked up" in said
    store = client.app.state.loops.live.store
    assert store.call(1).ended_at is None, "a standing note never ends the call"
