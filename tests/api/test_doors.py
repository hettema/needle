"""The doors and the loops through the API, on the floor (plan 03, acceptance
criteria 1 to 6): Start launches a lane the board sees at once; a session's
hook puts its question on the card and Answer resumes it; Watch, Look and
Stop open and prove; a close needs a signal and the signal moves the card;
a limit moves the lane and a death carries the machine's reason.
"""

import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import loops as loops_mod
from api.app import create_app
from api.cli import main
from board.import_01 import read_01
from domain.card import CardOrigin
from infrastructure.corpus import scan
from infrastructure.live import Live, sweep
from infrastructure.store import Store
from runtime import launch, windows
from tests.conftest import NOW
from tests.floor import Floor

CARD = 253
LANE = "card-253-every-metered-kilowatt-is-billed"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(cwd),
        },
    ).stdout.strip()


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    monkeypatch.setattr(launch, "HANDOFF_GRACE_SECONDS", 1.0)
    monkeypatch.setattr(launch, "STOP_SECONDS", 3.0)
    monkeypatch.setattr(windows, "WINDOW_VERIFY_SECONDS", 1.5)
    monkeypatch.setattr(loops_mod, "FLOOR_SECONDS", 3600.0)
    monkeypatch.setattr(loops_mod, "SIGNAL_SECONDS", 3600.0)
    monkeypatch.setattr(loops_mod, "TRUNK_SECONDS", 3600.0)


@pytest.fixture
def repo(corpus: Path) -> Path:
    """The synthetic project as a git repository with an origin, so lanes and folds are real."""
    origin = corpus.parent / "origin.git"
    origin.mkdir()
    git(origin, "init", "--bare", "-b", "develop")
    git(corpus, "init", "-q", "-b", "develop")
    git(corpus, "add", ".")
    git(corpus, "commit", "-q", "-m", "founding")
    git(corpus, "remote", "add", "origin", str(origin))
    git(corpus, "push", "-q", "origin", "develop", "develop:main")
    git(corpus, "fetch", "-q", "origin")
    return corpus


@pytest.fixture
def client(store: Store, project, card_file_01, repo: Path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("NEEDLE_DB", str(store.path))
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(repo, NOW)), NOW)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    with TestClient(create_app(store, dist=None)) as client:
        yield client


def column_of(client: TestClient, number: int) -> str:
    board = client.get("/api/projects/proj/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return column["definition"]["column"]
    raise AssertionError(f"#{number} is not on the board")


def detail(client: TestClient, number: int = CARD) -> dict:
    return client.get(f"/api/projects/proj/cards/{number}").json()


def summary_of(client: TestClient, number: int = CARD) -> dict:
    board = client.get("/api/projects/proj/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return card
    raise AssertionError(f"#{number} is not on the board")


def lane_path(repo: Path) -> str:
    return str(repo / ".claude" / "worktrees" / LANE)


def post_hook(client: TestClient, kind: str, session_id: str, cwd: str, **fields) -> dict:
    event = {
        "kind": kind,
        "session_id": session_id,
        "cwd": cwd,
        "at": datetime.now(UTC).isoformat(),
        "source": None,
        "message": None,
        "reason": None,
        "error": None,
        "transcript_path": None,
    }
    event.update(fields)
    response = client.post("/api/hooks", json=[event])
    assert response.status_code == 200, response.text
    return response.json()


def reconcile(client: TestClient) -> None:
    """The lane loop, under its own lock: a direct call would race the
    registry watcher, which hears the floor's own state files move."""
    client.portal.call(client.app.state.loops.reconcile)


def read_signals(client: TestClient) -> None:
    client.portal.call(client.app.state.loops.read_signals)


def start(client: TestClient, number: int = CARD, *, anyway: bool = False) -> dict:
    response = client.post(f"/api/projects/proj/cards/{number}/start", json={"anyway": anyway})
    assert response.status_code == 200, response.text
    return response.json()


# ── 1: Start ───────────────────────────────────────────────────────────


def test_start_says_where_it_will_run_launches_there_and_the_card_enters_executing(
    client: TestClient, machine_floor: Floor, repo: Path
):
    before = detail(client)
    in_flight_before = client.get("/api/projects/proj/board").json()["attention"]["in_flight"]
    assert before["doors"]["start"]["offered"] and before["doors"]["start"]["label"] == (
        "Start · fable on alpha"
    )
    assert before["doors"]["placement"]["slot"] == "alpha"
    assert before["doors"]["collision"]["verdict"] == "unknown"
    assert not before["doors"]["watch"]["offered"] and not before["doors"]["answer"]["offered"]

    said = start(client)
    assert said["door"] == "start" and said["said"].startswith("Started ")
    assert (
        ", fable on alpha, at medium, in card-253-every-metered-kilowatt-is-billed" in said["said"]
    )

    launched = machine_floor.state()["launch_log"][0]
    assert (
        launched["cwd"] == str(repo)
        and launched["argv"][launched["argv"].index("--effort") + 1] == "medium"
    )
    assert launched["argv"][launched["argv"].index("--worktree") + 1] == LANE
    brief = launched["argv"][-1]
    assert brief.startswith("#253 — Every metered kilowatt is billed\ncolumn: Up next")
    assert (
        "execute #253" in brief and "launched at medium" in brief and "do not stop to ask" in brief
    )
    assert "needle close proj 253" in brief and "WATCH: <what>" in brief

    assert column_of(client, CARD) == "Executing"
    after = detail(client)
    assert after["summary"]["lane_state"] == "working"
    assert after["summary"]["lane_sentence"].startswith("Working, fable on alpha")
    assert after["lane"]["session"]["short_id"] == launched["short"]
    assert [h["kind"] for h in after["history"][:2]] == ["moved", "started"]
    assert after["history"][0]["actor"] == "machine" and "hands on" in after["history"][0]["detail"]
    assert after["doors"]["watch"]["offered"] and after["doors"]["stop"]["offered"]
    assert not after["doors"]["start"]["offered"] and "hands on" in after["doors"]["start"]["why"]
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["in_flight"] == in_flight_before + 1

    again = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"anyway": False})
    assert again.status_code == 409 and "hands on" in again.json()["detail"]
    assert len(machine_floor.state()["launch_log"]) == 1


def test_a_card_without_a_gate_or_outside_the_queue_does_not_start(
    client: TestClient, machine_floor: Floor
):
    note = client.post("/api/projects/proj/cards/147/start", json={"anyway": False})
    assert note.status_code == 409 and "no effort gate" in note.json()["detail"]
    assert machine_floor.state()["launch_log"] == []


def test_start_refuses_when_the_rule_finds_nowhere_and_says_so_on_the_card(
    client: TestClient, machine_floor: Floor
):
    machine_floor.refuse_best("no account with headroom")
    machine_floor.script_launches({"then": "vanish"})
    response = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"anyway": False})
    assert response.status_code in (409, 502)
    assert (
        "no account with headroom" in response.json()["detail"]
        or "nowhere" in response.json()["detail"]
    )
    assert column_of(client, CARD) == "Up next"


def test_a_dead_launch_is_502_with_the_machines_words_and_moves_nothing(
    client: TestClient, machine_floor: Floor
):
    machine_floor.script_launches({"then": "vanish"})
    response = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"anyway": False})
    assert response.status_code == 502
    assert "Start failed" in response.json()["detail"] and "ended" in response.json()["detail"]
    assert column_of(client, CARD) == "Up next"
    assert detail(client)["history"][0]["detail"].startswith("Start failed")


def test_a_collision_blocks_start_and_start_anyway_overrides_it_with_the_reason(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """#253's plan names `engine/metering.py`; a live lane for #241 editing it collides."""
    plan = next(repo.glob("docs/plans/*metered*"))
    (repo / "engine").mkdir(exist_ok=True)
    (repo / "engine" / "metering.py").write_text("x\n")
    plan.write_text(plan.read_text() + "\n\nTouches `engine/metering.py`.\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "name the ground")
    git(repo, "push", "-q", "origin", "develop")
    # #241's lane: a real worktree with the file edited, and a live session in it.
    other = repo / ".claude" / "worktrees" / "card-241-the-deploy"
    git(repo, "worktree", "add", "-q", "-b", "card-241-the-deploy", str(other))
    (other / "engine" / "metering.py").write_text("changed\n")
    session_id = machine_floor.write_job(
        "alpha", "beef0241", cwd=str(other), worktree=str(other), name="card-241-the-deploy"
    )
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(other))
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    before = detail(client)
    assert not before["doors"]["start"]["offered"]
    assert before["doors"]["collision"]["verdict"] == "collides"
    assert "#241's lane is editing engine/metering.py right now." in before["doors"]["start"]["why"]
    assert before["doors"]["start_anyway"]["offered"]
    refused = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"anyway": False})
    assert refused.status_code == 409 and "Lane collision" in refused.json()["detail"]

    said = start(client, anyway=True)
    assert "collision overridden: #241's lane is editing engine/metering.py" in said["said"]
    brief = machine_floor.state()["launch_log"][0]["argv"][-1]
    assert "LANE COLLISION OVERRIDDEN by the owner" in brief
    assert column_of(client, CARD) == "Executing"


# ── 2 and 3: the machine moves, the hook, Answer ───────────────────────


def test_a_stop_with_a_question_asks_you_and_answer_resumes_one_live_copy(
    client: TestClient, machine_floor: Floor, repo: Path
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    session_id, short = launched["session_id"], launched["short"]
    # The session's turn ends with a question: the registry reads done, the hook posts the words.
    state_file = machine_floor.config_dir("alpha") / "jobs" / short / "state.json"
    state = json.loads(state_file.read_text())
    state["state"] = "done"
    state_file.write_text(json.dumps(state))
    received = post_hook(
        client,
        "Stop",
        session_id,
        lane_path(repo),
        message="The parser is in.\n\nShould the gate default to high or medium?",
    )
    assert received == {"received": 1, "attributed": 1}

    asking = detail(client)
    assert asking["summary"]["lane_state"] == "asking"
    assert asking["lane"]["question"].endswith("Should the gate default to high or medium?")
    assert (
        asking["summary"]["lane_sentence"]
        == "Asking you: Should the gate default to high or medium?"
    )
    assert asking["doors"]["answer"]["offered"] and not asking["doors"]["look"]["offered"]
    assert client.get("/api/projects/proj/board").json()["attention"]["asking_you"] >= 1

    empty = client.post(f"/api/projects/proj/cards/{CARD}/answer", json={"text": "  "})
    assert empty.status_code == 409
    answered = client.post(f"/api/projects/proj/cards/{CARD}/answer", json={"text": "High."})
    assert answered.status_code == 200, answered.text
    assert answered.json()["said"].startswith("Answered, and the lane resumed as ")
    resumed = machine_floor.state()["launch_log"][1]
    assert "--resume" in resumed["argv"] and resumed["argv"][-1] == "High."
    assert resumed["cwd"] == lane_path(repo)
    assert resumed["argv"][resumed["argv"].index("--resume") + 1] == session_id
    rows = client.app.state.loops.runtime.sessions()
    live = [s for s in rows if s.pid is not None and s.cwd == lane_path(repo)]
    assert len(live) == 1, "exactly one live copy in the lane"
    after = detail(client)
    assert after["summary"]["lane_state"] == "working"
    assert any(h["kind"] == "answered" and "High." in h["detail"] for h in after["history"])
    assert column_of(client, CARD) == "Executing"


def test_a_hand_move_out_of_executing_is_not_fought_and_is_named(
    client: TestClient, machine_floor: Floor
):
    start(client)
    moved = client.post(
        f"/api/projects/proj/cards/{CARD}/move",
        json={"to": {"column": "Up next", "group": None, "position": 0}},
    )
    assert moved.status_code == 200
    reconcile(client)
    assert column_of(client, CARD) == "Up next", "the machine never fights the owner"
    assert detail(client)["summary"]["lane_state"] == "working"


# ── 4: Watch, Look, Stop ───────────────────────────────────────────────


def test_watch_opens_a_tab_once_stop_ends_the_lane_and_look_takes_its_place(
    client: TestClient, machine_floor: Floor, repo: Path
):
    start(client)
    short = machine_floor.state()["launch_log"][0]["short"]
    watched = client.post(f"/api/projects/proj/cards/{CARD}/watch")
    assert watched.status_code == 200, watched.text
    assert watched.json()["said"].startswith(
        "Window org.omarchy.board-watch-card-253-every-metered-kilowatt-is-billed opened"
    )
    spawned = machine_floor.state()["spawned"][0]
    assert f"exec claude attach {short}" in spawned["command"][-1]
    # A window that is open is a door too (plan 04, item 2): Watch reads
    # "Focus its window" and brings the tab forward, proved by the compositor.
    with_window = detail(client)["doors"]["watch"]
    assert with_window["offered"] and with_window["label"] == "Focus its window"
    again = client.post(f"/api/projects/proj/cards/{CARD}/watch")
    assert again.status_code == 200, again.text
    assert again.json()["said"] == (
        "Focused org.omarchy.board-watch-card-253-every-metered-kilowatt-is-billed; the "
        "compositor reports org.omarchy.board-watch-card-253-every-metered-kilowatt-is-billed "
        "active."
    )
    assert machine_floor.state()["focus_calls"] == ["0xfake0001"]
    assert len(machine_floor.state()["spawned"]) == 1, "focus opens nothing"
    machine_floor.update(focus_works=False)
    unmoved = client.post(f"/api/projects/proj/cards/{CARD}/watch")
    assert unmoved.status_code == 502 and "Focus did not land" in unmoved.json()["detail"]
    assert "still reports" in unmoved.json()["detail"]
    machine_floor.update(focus_works=True)
    look = client.post(f"/api/projects/proj/cards/{CARD}/look")
    assert look.status_code == 409 and "live" in look.json()["detail"]

    stopped = client.post(f"/api/projects/proj/cards/{CARD}/stop")
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["said"].startswith(f"Stopped {short} after")
    assert "the card is in Up next" in stopped.json()["said"], (
        "nothing folded: back where it came from"
    )
    ended = detail(client)
    assert ended["summary"]["lane_state"] == "ended"
    assert ended["summary"]["lane_sentence"].startswith("Lane ended")
    assert not ended["doors"]["watch"]["offered"] and ended["doors"]["look"]["offered"]
    assert ended["doors"]["resume"]["offered"]
    assert any(
        h["actor"] == "machine" and "nothing folded" in h["detail"] for h in ended["history"]
    )

    machine_floor.update(clients=[])
    looked = client.post(f"/api/projects/proj/cards/{CARD}/look")
    assert looked.status_code == 200, looked.text
    assert "Its first line: Fresh session from the transcript of" in looked.json()["said"]
    assert "--fork-session" in machine_floor.state()["spawned"][-1]["command"][-1]


def test_discuss_opens_a_conversation_that_is_never_hands_on(
    client: TestClient, machine_floor: Floor
):
    talked = client.post(f"/api/projects/proj/cards/{CARD}/discuss")
    assert talked.status_code == 200, talked.text
    assert talked.json()["said"].startswith("Discussing in org.omarchy.board-discuss-card-253")
    command = machine_floor.state()["spawned"][0]["command"][-1]
    assert (
        "--session-id" in command
        and "--effort xhigh" in command
        and "needle start-card proj 253" in command
    )
    assert column_of(client, CARD) == "Up next"
    assert detail(client)["doors"]["start"]["offered"], "a discussion never blocks Start"


# ── 5: the close and the signal ────────────────────────────────────────


def archive_plan(repo: Path) -> Path:
    plan = next(repo.glob("docs/plans/*metered*"))
    done = repo / "docs" / "plans" / "done" / plan.name
    shutil.move(plan, done)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "archive")
    return done


def test_executed_needs_a_signal_and_the_close_writes_rows_and_moves(
    client: TestClient, repo: Path, capsys
):
    by_hand = client.post(
        f"/api/projects/proj/cards/{CARD}/move",
        json={"to": {"column": "Executed", "group": None, "position": 0}},
    )
    assert by_hand.status_code == 409 and "cannot enter Executed" in by_hand.json()["detail"]

    assert (
        main(["close", "proj", str(CARD), "--delivered", "d", "--watch", "nothing readable"]) == 1
    )
    assert "names no reader" in capsys.readouterr().err
    assert (
        main(["close", "proj", str(CARD), "--delivered", "d", "--watch", "x — owner by 2026-09-30"])
        == 1
    )
    assert "archive it" in capsys.readouterr().err

    done = archive_plan(repo)
    watch = f"the plan is archived — file {done.relative_to(repo)} by 2026-12-31 every 1h"
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "the meter bills",
                "--watch",
                watch,
                "--review",
                "docs/reviews/r.md",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.startswith(
        "#253 closed into Executed: DELIVERED, WATCH, REVIEW written"
    )
    client.app.state.loops.live.rescan("proj")
    assert column_of(client, CARD) == "Executed", [
        (h["actor"], h["detail"]) for h in detail(client)["history"][:4]
    ]
    closed = detail(client)
    assert [r["kind"] for r in closed["record"]] == ["DELIVERED", "WATCH", "REVIEW"]
    assert closed["signal"]["kind"] == "file" and closed["signal"]["due"] == "2026-12-31"

    read_signals(client)
    assert column_of(client, CARD) == "Done"
    reading = detail(client)
    assert reading["readings"][0]["delivered"] is True
    assert any(h["kind"] == "signal" and "delivered" in h["detail"] for h in reading["history"])
    assert any(
        h["actor"] == "machine" and "the signal says delivered" in h["detail"]
        for h in reading["history"]
    )


def test_a_signal_only_the_owner_can_read_is_a_question_at_its_due_time(
    client: TestClient, repo: Path
):
    archive_plan(repo)
    today = datetime.now(UTC).date().isoformat()
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "d",
                "--watch",
                f"he saw the invoice — owner by {today}",
            ]
        )
        == 0
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    asked = detail(client)
    assert (
        asked["doors"]["signal"]["offered"]
        and "Only you can read" in asked["doors"]["signal"]["why"]
    )
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["asking_you"] >= 1
    read_signals(client)
    assert column_of(client, CARD) == "Executed", "the board never reads an owner's signal"
    answered = client.post(f"/api/projects/proj/cards/{CARD}/signal", json={"delivered": False})
    assert answered.status_code == 200
    assert column_of(client, CARD) == "Decision moment"


def test_an_unreadable_signal_past_its_due_time_lands_in_decision_moment_with_the_finding(
    client: TestClient, repo: Path, machine_floor: Floor
):
    archive_plan(repo)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "d",
                "--watch",
                f"prod is up — url https://gone.test by {yesterday}",
            ]
        )
        == 0
    )
    client.app.state.loops.live.rescan("proj")
    read_signals(client)
    assert column_of(client, CARD) == "Decision moment"
    history = detail(client)["history"]
    assert history[1]["detail"].startswith("Signal read as unreadable: https://gone.test could not")
    assert "could not be read" in history[0]["detail"] and "has passed" in history[0]["detail"]
    assert history[0]["actor"] == "machine"


# ── plan 04, item 1: the evidence behind a machine placement, doubted when gone ──


def test_a_lane_that_dies_mid_close_is_doubted_on_the_next_read_until_the_loop_moves_it(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """The mover and the doubt read the same facts, so a plain death is moved
    back in the read that sees it. The doubt is for the reads where the mover
    waits: here a close still landing (DELIVERED written, plan not yet
    archived) when the session is killed."""
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    placed = detail(client)["history"][0]
    assert placed["actor"] == "machine" and placed["evidence"] == "hands-on"
    held = summary_of(client)["standing"]
    assert held == {"actor": "machine", "evidence": "hands-on", "state": "held", "words": None}
    # The card file puts three cards in machine columns on 0.1's word alone; the
    # first read doubts those, and this lane adds to and then leaves that count.
    doubted_before = client.get("/api/projects/proj/board").json()["attention"]["doubted"]

    assert main(["row", "proj", str(CARD), "DELIVERED", "the meter bills"]) == 0
    os.kill(launched["pid"], 9)
    (machine_floor.config_dir("alpha") / "sessions" / f"{launched['pid']}.json").unlink()
    reconcile(client)

    assert column_of(client, CARD) == "Executing", "a close still landing is not dragged back"
    doubted = summary_of(client)["standing"]
    assert doubted["state"] == "doubted" and doubted["evidence"] == "hands-on"
    assert doubted["words"].startswith(
        "the board doubts this: no live session has hands on its worktree"
    )
    assert detail(client)["summary"]["standing"] == doubted
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["doubted"] == doubted_before + 1

    done = archive_plan(repo)
    watch = f"the plan is archived — file {done.relative_to(repo)} by 2026-12-31"
    assert main(["row", "proj", str(CARD), "WATCH", watch]) == 0
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    assert column_of(client, CARD) == "Executed"
    landed = detail(client)
    assert landed["history"][0]["evidence"] == "close-landed"
    assert landed["summary"]["standing"]["state"] == "held"
    assert client.get("/api/projects/proj/board").json()["attention"]["doubted"] == doubted_before


def test_the_imports_placements_read_unknown_before_the_first_read_and_are_tested_after(
    store: Store, project, card_file_01, repo: Path
):
    """0.1's word is not evidence: the cards its file put in Executed read
    "evidence unknown" until the loop's first read, which tests each one."""
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(repo, NOW)), NOW)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    live = Live(store)
    live.load()
    executed = [
        s
        for c in live.board("proj").columns
        if c.definition.column == "Executed"
        for g in c.groups
        for s in g.cards
    ]
    assert executed and all(s.standing.state == "unknown" for s in executed)
    assert all(s.standing.actor == "import" for s in executed)
    assert executed[0].standing.words == (
        "imported from Needle 0.1; evidence unknown until the first read"
    )
    with TestClient(create_app(store, dist=None)) as client:
        board = client.get("/api/projects/proj/board").json()
        states = {
            c["number"]: (col["definition"]["column"], c["standing"])
            for col in board["columns"]
            for g in col["groups"]
            for c in g["cards"]
        }
        tested = {n: s for n, (column, s) in states.items() if column == "Executed"}
        assert tested and {s["state"] for s in tested.values()} <= {"held", "doubted"}
        assert any(
            s["state"] == "doubted" and "names no signal the board can read" in s["words"]
            for s in tested.values()
        )
        assert board["attention"]["doubted"] == sum(
            1 for _, s in states.values() if s["state"] == "doubted"
        )


# ── 6: rescue and the machine's reason ─────────────────────────────────


def test_a_lane_that_dies_on_a_limit_is_moved_and_the_card_says_where(
    client: TestClient, machine_floor: Floor
):
    start(client)
    client.post(f"/api/projects/proj/cards/{CARD}/watch")
    launched = machine_floor.state()["launch_log"][0]
    state_file = machine_floor.config_dir("alpha") / "jobs" / launched["short"] / "state.json"
    state = json.loads(state_file.read_text())
    state["state"] = "blocked"
    state["detail"] = "You've reached your Fable limit."
    state_file.write_text(json.dumps(state))
    machine_floor.write_handoff(
        launched["session_id"], **{"from": "alpha"}, account="beta", pid=launched["pid"]
    )
    reconcile(client)

    moved = detail(client)
    assert any(
        h["kind"] == "rescued" and h["detail"] == "Moved to fable on beta, new window opened."
        for h in moved["history"]
    ), [h["detail"] for h in moved["history"]]
    assert moved["lane"]["session"]["slot"] == "beta"
    assert moved["summary"]["lane_sentence"].startswith(
        "Moved to fable on beta, new window opened."
    )
    assert column_of(client, CARD) == "Executing"
    assert len(machine_floor.state()["spawned"]) == 2


def test_a_lane_killed_otherwise_carries_the_machines_reason(
    client: TestClient, machine_floor: Floor
):
    start(client)
    launched = machine_floor.state()["launch_log"][0]
    machine_floor.update(
        journal={
            f"needle-{LANE}.scope": [
                "claude[4242]: Killed process 4242 (claude) total-vm:9GB oom-kill",
            ]
        }
    )
    os.kill(launched["pid"], 9)
    (machine_floor.config_dir("alpha") / "sessions" / f"{launched['pid']}.json").unlink()
    reconcile(client)

    dead = detail(client)
    assert dead["summary"]["lane_state"] == "ended"
    assert "Killed process 4242 (claude)" in dead["lane"]["died"]
    assert dead["doors"]["resume"]["offered"] and dead["doors"]["look"]["offered"]
    assert column_of(client, CARD) == "Up next"
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["lanes_ended"] == 1

    resumed = client.post(f"/api/projects/proj/cards/{CARD}/resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["said"].startswith("Resumed as ")
    assert column_of(client, CARD) == "Executing"


# ── plan 07: conversations and lanes that know each other ──────────────


def test_idea_opens_a_conversation_the_rail_lists_and_a_document_it_writes_is_born_from_it(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """Item 1: Idea in the head opens a conversation in the project's checkout
    with the brief and the owner's first line; it is in discussion on the rail
    while its session lives and never hands on a tree; a document naming the
    conversation becomes a card whose history says where it was born."""
    board_before = client.get("/api/projects/proj/board").json()
    assert board_before["attention"]["in_discussion"] == 0 and board_before["conversations"] == []
    opened = client.post(
        "/api/projects/proj/idea", json={"text": "should berths be priced by the metre?"}
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["said"].startswith(
        "Talking in org.omarchy.board-idea-proj, fable on alpha"
    )
    spawned = machine_floor.state()["spawned"][0]
    assert spawned["app_id"] == "org.omarchy.board-idea-proj"
    command = spawned["command"][-1]
    assert command.startswith(f"cd {repo} &&"), "the conversation runs in the project's checkout"
    assert "--effort xhigh" in command and "--session-id" in command
    session_id = command.split("--session-id ")[1].split()[0]
    short = session_id[:8]
    assert f"conversation {short}" in command, "the brief names the conversation to be named back"
    assert "should berths be priced by the metre?" in command and "answer it" in command
    assert "The corpus is the only way in" in command and "Write nothing else" in command

    # No process yet: the window was spawned but the fake launcher runs nothing.
    assert client.get("/api/projects/proj/board").json()["attention"]["in_discussion"] == 0
    machine_floor.write_job("alpha", short, session_id=session_id, cwd=str(repo), name="idea")
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(repo), kind="interactive")
    reconcile(client)
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["in_discussion"] == 1
    talk = board["conversations"][0]
    assert talk["what"] == "Idea" and talk["short_id"] == short and talk["card_number"] is None
    assert board["attention"]["in_flight"] == board_before["attention"]["in_flight"], (
        "a conversation is never hands on a tree"
    )
    assert all(
        c["lane_state"] == "none"
        for col in board["columns"]
        for g in col["groups"]
        for c in g["cards"]
    )

    # The session writes a suggestion that names the conversation; the watcher cards it.
    (repo / "docs" / "slice-suggestions" / "2026-09-04-berths-by-the-metre.md").write_text(
        "# Berths priced by the metre\n\n"
        "**Found by:** the owner, from the board's Idea door on 2026-09-04 "
        f"(conversation {short})\n"
        "**Kind:** idea\n\n## Observation\n\nA berth is priced by the slot, not the boat.\n",
        encoding="utf-8",
    )
    client.app.state.loops.live.rescan("proj")
    born = client.get("/api/projects/proj/board").json()
    number = next(
        c["number"]
        for col in born["columns"]
        for g in col["groups"]
        for c in g["cards"]
        if c["title"] == "Berths priced by the metre"
    )
    history = detail(client, number)["history"]
    today = datetime.now(UTC).date().isoformat()
    assert history[-1]["kind"] == "born"
    assert (
        f"Born from a conversation on {today} ({short} on alpha, from the Idea door)."
        in history[-1]["detail"]
    )

    # An empty first line: the session asks.
    machine_floor.update(clients=[])
    again = client.post("/api/projects/proj/idea", json={"text": ""})
    assert again.status_code == 200, again.text
    second = machine_floor.state()["spawned"][1]["command"][-1]
    assert "ask him, in one line, what is on his mind" in second


def test_two_lanes_in_one_file_collide_on_both_cards_know_each_other_and_the_fold_says_so(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    """Item 2: two lanes with overlapping actual edits are colliding on the next
    read, on both cards and the rail; each lane's brief names the other with
    its footprint; a watercooler line from one is on the other's card; a fold
    over the other's edits is named on both cards and in the watercooler."""
    start(client)
    mine = Path(lane_path(repo))
    # #241's lane: a real worktree with a live session, editing README.md.
    other = repo / ".claude" / "worktrees" / "card-241-the-deploy"
    git(repo, "worktree", "add", "-q", "-b", "card-241-the-deploy", str(other))
    (other / "README.md").write_text("their edit\n")
    (other / "theirs.py").write_text("x\n")
    session_id = machine_floor.write_job(
        "alpha", "beef0241", cwd=str(other), worktree=str(other), name="card-241-the-deploy"
    )
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(other))
    reconcile(client)
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["colliding"] == 0
    assert summary_of(client, 241)["colliding"] is None

    # Every lane's brief names the other live lanes with their footprints.
    brief = client.get("/api/projects/proj/cards/253/brief").text
    assert "Other lanes with hands on this project right now:" in brief
    assert "#241 " in brief and "Touching: README.md, theirs.py." in brief
    assert "say so in the watercooler first" in brief and "needle watercooler proj 253" in brief
    assert "(nothing said yet)" in brief

    # #253 drifts into README.md: colliding on both cards on the next read.
    (mine / "README.md").write_text("my edit\n")
    reconcile(client)
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["colliding"] == 2
    assert summary_of(client, CARD)["colliding"] == {
        "verdict": "collides",
        "sentence": "#241's lane is also editing README.md.",
        "files": ["README.md"],
        "cards": [241],
    }
    assert summary_of(client, 241)["colliding"]["sentence"] == (
        "#253's lane is also editing README.md."
    )
    lane = detail(client)["lane"]
    assert lane["edits"] == ["README.md"] and lane["colliding"]["files"] == ["README.md"]

    # A watercooler line from #241 is on #253's card and in its brief.
    line = "README.md is mine until the fold; leave it"
    assert main(["watercooler", "proj", "241", line]) == 0
    assert "#241 said it" in capsys.readouterr().out
    client.app.state.loops.live.bump()
    board = client.get("/api/projects/proj/board").json()
    assert board["watercooler"][-1]["card_number"] == 241
    assert board["watercooler"][-1]["text"] == line
    assert detail(client)["watercooler"][-1]["text"] == line
    assert f"#241: {line}" in client.get("/api/projects/proj/cards/253/brief").text
    assert main(["watercooler", "proj"]) == 0
    assert f"#241: {line}" in capsys.readouterr().out
    assert main(["watercooler", "proj", "241", "  "]) == 1

    # #253 folds over #241's edit: said on both cards and in the watercooler.
    git(mine, "add", "-A")
    git(mine, "commit", "-q", "-m", "my edit")
    assert main(["fold", "--worktree", str(mine)]) == 0
    out = capsys.readouterr().out
    assert "The watercooler, before the fold:" in out
    assert f"#241: {line}" in out
    assert "this fold lands over #241's edits in README.md" in out
    assert "folded:" in out
    client.app.state.loops.live.bump()
    mine_history = [h["detail"] for h in detail(client)["history"]]
    assert "Folded over #241's edits in README.md" in mine_history
    theirs_history = [h["detail"] for h in detail(client, 241)["history"]]
    assert "#253 folded over this lane's edits in README.md; re-verify them at the fold" in (
        theirs_history
    )
    last = client.get("/api/projects/proj/board").json()["watercooler"][-1]
    assert last["card_number"] is None
    assert last["text"] == "#253 folded over #241's edits in README.md"


# ── plan 10: a running lane hears the board ────────────────────────────


def word_of(client: TestClient, cwd: str) -> list[str]:
    response = client.get("/api/word", params={"cwd": cwd})
    assert response.status_code == 200, response.text
    return response.json()["sentences"]


def test_a_running_lane_hears_its_drift_and_the_other_lanes_lines_once(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """Plan 10, item 1, on the two-lane fixture: A drifts into B's file and
    A's word names B's edits once; B's watercooler line reaches A's word
    once and never B's own; the open card shows when A last heard and what;
    the mark is where it was after the store is reopened."""
    start(client)
    mine = Path(lane_path(repo))
    other = repo / ".claude" / "worktrees" / "card-241-the-deploy"
    git(repo, "worktree", "add", "-q", "-b", "card-241-the-deploy", str(other))
    (other / "README.md").write_text("their edit\n")
    session_id = machine_floor.write_job(
        "alpha", "beef0241", cwd=str(other), worktree=str(other), name="card-241-the-deploy"
    )
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(other))
    reconcile(client)
    assert word_of(client, str(mine)) == [], "nothing has happened since the brief"
    assert client.get("/api/word", params={"cwd": str(repo)}).status_code == 404
    assert client.get("/api/word", params={"cwd": "/elsewhere"}).status_code == 404
    assert detail(client)["heard"] is None

    # A drifts into B's file: named once, with the ask; then nothing.
    (mine / "README.md").write_text("my edit\n")
    reconcile(client)
    assert word_of(client, str(mine / "docs")) == [
        "#241's lane is also editing README.md. Say in the watercooler what you are doing there."
    ]
    assert word_of(client, str(mine)) == []
    heard = detail(client)["heard"]
    assert heard["collision"] == "#241's lane is also editing README.md."
    assert heard["text"].startswith("#241's lane is also editing README.md.")
    assert heard["at"] is not None

    # B's line reaches A once; B never hears its own, only its side of the drift.
    line = "README.md is mine until the fold; leave it"
    assert main(["watercooler", "proj", "241", line]) == 0
    assert "hears it inside its own session within a minute" in capsys.readouterr().out
    assert word_of(client, str(mine)) == [f"#241 said on the watercooler: {line}"]
    assert word_of(client, str(mine)) == []
    assert word_of(client, str(other)) == [
        "#253's lane is also editing README.md. Say in the watercooler what you are doing there."
    ]
    assert word_of(client, str(other)) == []
    heard = detail(client)["heard"]
    assert heard["text"] == f"#241 said on the watercooler: {line}"
    assert heard["watercooler_id"] == 1

    # The mark survives the board: a fresh store reads the same one.
    reopened = Store(store.path)
    try:
        assert reopened.heard_mark("proj", CARD) == client.app.state.live.store.heard_mark(
            "proj", CARD
        )
    finally:
        reopened.close()

    # B leaves the file: the clearing is said once, and B's fold over A's
    # edit reaches A as the board's line.
    (other / "README.md").unlink()
    reconcile(client)
    assert word_of(client, str(mine)) == [
        "The collision has cleared: no other live lane is editing a file this lane is editing."
    ]
    assert word_of(client, str(mine)) == []
    assert word_of(client, str(other)) == [
        "The collision has cleared: no other live lane is editing a file this lane is editing."
    ]
    git(mine, "add", "-A")
    git(mine, "commit", "-q", "-m", "my edit")
    (other / "README.md").write_text("their edit again\n")
    reconcile(client)
    assert word_of(client, str(other))[0].startswith("#253's lane is also editing README.md.")
    assert main(["fold", "--worktree", str(mine)]) == 0
    capsys.readouterr()
    assert word_of(client, str(other)) == [
        "The board said on the watercooler: #253 folded over #241's edits in README.md"
    ]


# ── plan 06: the board at a glance ─────────────────────────────────────


def test_an_archived_document_moves_its_card_when_nothing_has_hands_on_it(
    client: TestClient, repo: Path
):
    """Item 1: an Up next card's plan is archived with no lane on the card;
    on the next read it is in Decision moment with the reason and the
    document on its history; with DELIVERED and a readable WATCH it is
    Executed instead."""
    assert column_of(client, CARD) == "Up next"
    done = archive_plan(repo)
    live = client.app.state.loops.live
    live.rescan("proj")
    reconcile(client)
    assert column_of(client, CARD) == "Decision moment"
    history = detail(client)["history"]
    assert history[0]["kind"] == "moved" and history[0]["evidence"] == "document-archived"
    assert history[0]["actor"] == "machine"
    assert f"its plan was archived (docs/plans/done/{done.name})" in history[0]["detail"]
    assert "no session wrote it up on the board" in history[0]["detail"]
    assert history[1]["kind"] == "archived" and done.name in history[1]["detail"]
    assert summary_of(client)["standing"]["state"] == "held"
    # Nothing moves it again, and Decision moment is where it waits for the owner.
    reconcile(client)
    assert column_of(client, CARD) == "Decision moment"

    # A card with its close written up, and a plan archived by hand: Executed.
    other = 241
    path = repo / summary_of(client, other)["document_path"]
    from domain.card import Actor
    from domain.row import Row, RowKind

    live.add_row("proj", other, Row(kind=RowKind.DELIVERED, text="the metre"), Actor.SESSION)
    live.add_row(
        "proj",
        other,
        Row(kind=RowKind.WATCH, text="the tariff page — file docs/tariff.md by 2026-09-30"),
        Actor.SESSION,
    )
    shutil.move(path, repo / "docs" / "plans" / "done" / path.name)
    live.rescan("proj")
    reconcile(client)
    assert column_of(client, other) == "Executed"
    row = detail(client, other)["history"][0]
    assert row["evidence"] == "close-landed" and "the close landed" in row["detail"]


def test_plan_opens_a_plan_writing_conversation_for_one_suggestion_or_several(
    client: TestClient, machine_floor: Floor, repo: Path
):
    """Item 5: Plan on a suggestion card opens a conversation in the
    project's checkout with the brief; over a selection it is one plan for
    all of them; the rail lists it once; a plan card refuses."""
    reconcile(client)
    in_flight_before = client.get("/api/projects/proj/board").json()["attention"]["in_flight"]
    first, second = 252, 242
    for number in (first, second):
        assert summary_of(client, number)["plan"]["offered"], f"#{number} offers Plan"
        assert detail(client, number)["doors"]["plan"]["offered"]
    paths = {n: summary_of(client, n)["document_path"] for n in (first, second)}

    one = client.post("/api/projects/proj/plan", json={"numbers": [first]})
    assert one.status_code == 200, one.text
    assert one.json()["said"].startswith(
        f"Planning #{first} in org.omarchy.board-plan-card-{first}-"
    )
    command = machine_floor.state()["spawned"][0]["command"][-1]
    assert command.startswith(f"cd {repo} &&"), "the conversation runs in the project's checkout"
    assert "--effort xhigh" in command and "--session-id" in command
    assert "**Carries:**" in command and paths[first] in command
    # The brief travels shell-quoted, so the phrases checked carry no apostrophe.
    assert f"#{first} becomes the plan" in command and "same number and history" in command
    assert "docs/plans/README.md describes" in command, "no skill: the README's shape"
    assert "never writes into it" in command and "Ask the owner in this window" in command
    assert detail(client, first)["history"][0]["kind"] == "discussed"

    # Several, with the project's own plan-writing skill.
    (repo / ".claude" / "skills" / "hm-plan-write").mkdir(parents=True)
    together = client.post("/api/projects/proj/plan", json={"numbers": [first, second]})
    assert together.status_code == 200, together.text
    assert together.json()["said"].startswith(
        f"Planning #{first}, #{second} in org.omarchy.board-plan-cards-{first}-{second}"
    )
    command = machine_floor.state()["spawned"][1]["command"][-1]
    assert "/hm-plan-write" in command and "these 2 suggestions together" in command
    assert paths[first] in command and paths[second] in command
    assert "the other cards fold under it" in command
    session_id = command.split("--session-id ")[1].split()[0]
    short = session_id[:8]
    machine_floor.write_job("alpha", short, session_id=session_id, cwd=str(repo), name="plan")
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(repo), kind="interactive")
    reconcile(client)
    board = client.get("/api/projects/proj/board").json()
    assert board["attention"]["in_discussion"] == 1
    assert board["conversations"][0]["what"] == f"Plan #{second}, #{first}"
    assert board["attention"]["in_flight"] == in_flight_before, (
        "a conversation is never hands on a tree"
    )

    refused = client.post("/api/projects/proj/plan", json={"numbers": [CARD]})
    assert refused.status_code == 409 and "not behind a live suggestion" in refused.json()["detail"]
    empty = client.post("/api/projects/proj/plan", json={"numbers": []})
    assert empty.status_code == 409


def test_a_plan_that_lands_citing_suggestions_takes_the_first_card_and_folds_the_rest(
    client: TestClient, repo: Path
):
    """Item 5: when a plan citing three live suggestions lands, the first
    suggestion's card is the plan's card (same number, in Planned), the other
    two fold under it and follow it; nothing is retyped and no second card
    is born; the brief and the page say what the card carries."""
    from tests.conftest import write_suggestion

    live = client.app.state.loops.live
    first, second = 252, 242
    write_suggestion(repo, "2026-09-04-a-third-idea", title="A third idea")
    live.rescan("proj")
    third = next(
        c["number"]
        for col in client.get("/api/projects/proj/board").json()["columns"]
        for g in col["groups"]
        for c in g["cards"]
        if c["title"] == "A third idea"
    )
    paths = [summary_of(client, n)["document_path"] for n in (first, second, third)]
    before = client.get("/api/projects/proj/board").json()
    unplanned_before = (
        before["attention"]["unplanned_ideas"] + before["attention"]["unplanned_defects"]
    )

    plan = repo / "docs" / "plans" / "2026-09-04-three-together.md"
    plan.write_text(
        "# Three together\n\n**Status:** PENDING\n**Effort gate:** high — three at once.\n"
        "**Carries:** " + ", ".join(paths) + "\n\n## Intent\n\nOne slice carries three.\n",
        encoding="utf-8",
    )
    effects = live.rescan("proj")
    assert [r.card_number for r in effects.relinked] == [first]
    assert [(f.card_number, f.into) for f in effects.folded] == [(second, first), (third, first)]
    assert effects.born == [], "no second card for a plan that carries a suggestion"

    leader = summary_of(client, first)
    assert leader["place"]["column"] == "Planned"
    assert leader["document_state"] == "plan"
    assert leader["document_path"] == "docs/plans/2026-09-04-three-together.md"
    assert [f["number"] for f in leader["folded"]] == [second, third]
    board = client.get("/api/projects/proj/board").json()
    shown = {c["number"] for col in board["columns"] for g in col["groups"] for c in g["cards"]}
    assert second not in shown and third not in shown, "folded cards sit under their leader"
    assert board["documents_without_card"] == [], "carried suggestions are not without a card"
    after = board["attention"]["unplanned_ideas"] + board["attention"]["unplanned_defects"]
    assert after == unplanned_before - 3
    history = detail(client, first)["history"]
    assert history[0]["kind"] == "moved" and "a plan appeared for it" in history[0]["detail"]
    assert (
        history[1]["kind"] == "linked" and "carries this card's suggestion" in history[1]["detail"]
    )
    folded_row = detail(client, second)["history"][0]
    assert folded_row["kind"] == "folded-into" and f"Folded into #{first}" in folded_row["detail"]
    brief = client.get(f"/api/projects/proj/cards/{first}/brief").text
    assert f"carries: #{second} " in brief and f"carries: #{third} " in brief
    assert f"folded: into #{first}" in client.get(f"/api/projects/proj/cards/{second}/brief").text

    # The leader moves; the folded cards go with it. A folded card is not moved alone.
    moved = client.post(
        f"/api/projects/proj/cards/{first}/move",
        json={"to": {"column": "Up next", "group": None, "position": 0}},
    )
    assert moved.status_code == 200, moved.text
    cards = {c.number: c for c in live.store.cards("proj")}
    assert cards[second].place.column.value == "Up next" and cards[third].folded_into == first
    assert "followed #252" in detail(client, second)["history"][0]["detail"]
    alone = client.post(
        f"/api/projects/proj/cards/{second}/move",
        json={"to": {"column": "Backlog", "group": None, "position": 0}},
    )
    assert alone.status_code == 409 and f"folded into #{first}" in alone.json()["detail"]
    # The next read changes nothing more.
    assert live.rescan("proj").empty()
