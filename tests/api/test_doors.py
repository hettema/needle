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
from infrastructure.live import sweep
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
    again = client.post(f"/api/projects/proj/cards/{CARD}/watch")
    assert again.status_code == 409 and "already open" in again.json()["detail"]
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
