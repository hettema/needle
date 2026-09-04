"""Defects fix themselves (plan 11), on the floor: a code lane cannot close
without a review record (item 1); the dial is on the head, persists and is
audited (item 3); with it on, the oldest `Fix: now` defect is planned by a
windowless session and, once its plan lands, started by the machine with
*started by the dial* on the card, one at a time under the number (items
4 and 6); `his` and unmarked defects are never started and a planning
session's question leaves the card to the owner (item 4); a `Fix: when`
trigger is read by the signal loop and delivered makes the defect eligible
(item 5); `needle fixes` counts the loop (item 6)."""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from infrastructure import clock
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.attention import claim_count
from tests.api.test_doors import CARD, archive_plan, column_of, detail, git, read_signals, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

TIDE = "The tide clock drifts a minute a day"
TIDE_PATH = "docs/slice-suggestions/2026-09-04-the-tide-clock-drifts-a-minute-a-day.md"


def board(client: TestClient) -> dict:
    return client.get("/api/projects/proj/board").json()


def number_of(client: TestClient, title: str) -> int:
    for column in board(client)["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["title"] == title:
                    return card["number"]
    raise AssertionError(f"no card titled {title!r}")


def tick(client: TestClient) -> None:
    client.portal.call(client.app.state.dial.tick)


def turn(client: TestClient, *, on: bool, lanes: int) -> dict:
    response = client.post("/api/dial", json={"on": on, "lanes": lanes})
    assert response.status_code == 200, response.text
    return response.json()


def write_defect(repo: Path, stem: str, title: str, head: str, body: str = "x") -> str:
    path = repo / "docs" / "slice-suggestions" / f"{stem}.md"
    path.write_text(
        f"# {title}\n\n**Kind:** defect\n{head}\n**Found by:** the owner, 2026-09-05.\n\n"
        f"## Observation\n\n{body}\n\n## What would hold it\n\nThe fix.\n",
        encoding="utf-8",
    )
    return f"docs/slice-suggestions/{stem}.md"


def land_plan(repo: Path, suggestion_path: str, stem: str, title: str, *, terrain: str = "") -> str:
    """What the planning session does: the plan carrying the suggestion,
    committed in the project's checkout, the suggestion moved to done/."""
    plan = repo / "docs" / "plans" / f"{stem}.md"
    plan.write_text(
        f"# {title}\n\n**Status:** PENDING\n**Written:** 2026-09-05, by the dial's planning "
        f"session\n**Effort gate:** medium — one edit and a check\n**Carries:** {suggestion_path}\n"
        "**Class:** a boot check refuses a clock that disagrees with the office\n\n"
        f"## Intent\n\nThe display reads the office's clock.{terrain}\n\n"
        "### 1. The clock\n\nDone means: the display never keeps its own.\n",
        encoding="utf-8",
    )
    done = repo / "docs" / "slice-suggestions" / "done" / Path(suggestion_path).name
    done.parent.mkdir(exist_ok=True)
    text = (repo / suggestion_path).read_text(encoding="utf-8")
    lines = text.split("\n")
    lines.insert(2, f"**Carried by:** docs/plans/{stem}.md")
    done.write_text("\n".join(lines), encoding="utf-8")
    (repo / suggestion_path).unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "plan by the dial")
    return f"docs/plans/{stem}.md"


# ── item 3: the dial ───────────────────────────────────────────────────


def test_the_dial_is_off_until_turned_persists_and_is_audited_as_the_owners(
    client: TestClient, store: Store
):
    state = board(client)["dial"]
    assert state == {
        "dial": {"on": False, "lanes": 1, "changed_at": None, "first_on_at": None},
        "running": 0,
        "quiet": True,
    }
    turned = turn(client, on=True, lanes=2)
    assert turned["dial"]["on"] is True and turned["dial"]["lanes"] == 2
    assert turned["dial"]["changed_at"] is not None
    assert turned["dial"]["first_on_at"] == turned["dial"]["changed_at"]
    assert board(client)["dial"]["dial"]["lanes"] == 2
    changes = store.dial_changes()
    assert [(c.actor.value, c.on, c.lanes) for c in changes] == [("owner", True, 2)]
    # A turn that changes nothing writes nothing; a restart keeps the setting.
    turn(client, on=True, lanes=2)
    assert len(store.dial_changes()) == 1
    reopened = Store(store.path)
    try:
        assert reopened.dial().on is True and reopened.dial().lanes == 2
        assert reopened.rail_at_on(), "the rail was recorded at the first turn to on"
    finally:
        reopened.close()
    off = turn(client, on=False, lanes=2)
    assert off["dial"]["on"] is False and off["dial"]["first_on_at"] is not None
    assert [(c.on, c.lanes) for c in store.dial_changes()] == [(True, 2), (False, 2)]


# ── items 4 and 6: the path from the rail to a running lane ────────────


def test_with_the_dial_on_the_oldest_now_defect_is_planned_then_started_by_the_dial(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    tide = number_of(client, TIDE)
    live = client.app.state.loops.live
    # A second `now` defect, younger: it waits until the first folds.
    write_defect(
        repo,
        "2026-09-05-the-gate-log-loses-its-last-line",
        "The gate log loses its last line",
        "**Fix:** now",
    )
    live.rescan("proj")
    reconcile(client)
    gate_log = number_of(client, "The gate log loses its last line")

    # Off: nothing starts by itself, however eligible the rail is (acceptance 5).
    tick(client)
    assert machine_floor.state()["launch_log"] == []
    assert main(["fixes", "all"]) == 0
    assert "no fix lane yet" in capsys.readouterr().out

    turn(client, on=True, lanes=1)
    tick(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == 1, "one defect per beat, and the number is one"
    planning = log[0]
    assert planning["cwd"] == str(repo) and "--worktree" not in planning["argv"]
    assert planning["argv"][planning["argv"].index("-n") + 1].startswith(f"planning-card-{tide}-")
    assert planning["argv"][planning["argv"].index("--effort") + 1] == "xhigh"
    brief = planning["argv"][-1]
    assert brief.startswith("A plan to write for a defect the dial took, on Harbourmaster")
    assert "never EnterWorktree" in brief and "Five rules" in brief
    assert "`**Class:**" in brief and f"needle row proj {tide} ASK" in brief
    assert f"**Carries:** {TIDE_PATH}" in brief and "git pull --rebase origin develop" in brief

    opened = detail(client, tide)
    assert opened["summary"]["planning"]["session_id"] == planning["session_id"]
    assert opened["summary"]["state"]["word"] == "being planned · alpha"
    assert opened["summary"]["state"]["meaning"] == "live"
    assert opened["summary"]["lane_state"] == "none", "a planning session is never hands on"
    assert opened["history"][0]["detail"].startswith(
        f"The dial took it: planning session {planning['short']}, fable on alpha"
    )
    assert opened["history"][0]["actor"] == "machine"
    state = board(client)
    assert claim_count(state, "planning") == 1
    assert state["dial"]["running"] == 1
    assert detail(client, gate_log)["summary"]["planning"] is None

    # The number is full: another beat plans nothing more.
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == 1

    # The planning session's plan lands: the card becomes the plan's, and
    # the dial opens Start itself, as the machine.
    land_plan(
        repo,
        TIDE_PATH,
        "2026-09-05-the-quay-clock-is-the-offices",
        "The quay clock is the office's",
    )
    live.rescan("proj")
    assert column_of(client, tide) == "Planned"
    tick(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == 2, ("the plan landed, so the dial started the lane", store.fix_lanes("proj"))
    started = log[1]
    assert started["argv"][started["argv"].index("--worktree") + 1].startswith(f"card-{tide}-")
    assert started["argv"][started["argv"].index("--effort") + 1] == "medium", "the plan's gate"
    assert column_of(client, tide) == "Executing"
    history = detail(client, tide)["history"]
    started_row = next(h for h in history if h["kind"] == "started")
    assert started_row["actor"] == "machine" and "started by the dial" in started_row["detail"]
    assert any("The plan landed" in h["detail"] for h in history)
    assert detail(client, tide)["summary"]["planning"] is None
    lanes = store.fix_lanes("proj")
    assert [(f.card_number, f.stage.value) for f in lanes] == [(tide, "started")]
    assert lanes[0].planned_at is not None and lanes[0].started_at is not None
    assert board(client)["dial"]["running"] == 1 and board(client)["dial"]["quiet"] is False
    # The second defect still waits: the fix lane counts until it folds.
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == 2

    # The fix lane folds: it stops counting, and the next beat takes the next defect.
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    (worktree / "quay.py").write_text("clock = office\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "the clock")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    capsys.readouterr()
    tick(client)
    lanes = store.fix_lanes("proj")
    assert lanes[0].stage.value == "folded" and lanes[0].ended_at is not None
    assert len(machine_floor.state()["launch_log"]) == 3, "the next defect is planned"
    next_planning = machine_floor.state()["launch_log"][2]
    assert next_planning["argv"][next_planning["argv"].index("-n") + 1].startswith(
        f"planning-card-{gate_log}-"
    )
    assert [(f.card_number, f.stage.value) for f in store.fix_lanes("proj")] == [
        (tide, "folded"),
        (gate_log, "planning"),
    ]

    # The loop, counted (item 6).
    report = client.get("/api/fixes").json()
    assert report["dial"]["on"] is True
    first = report["lanes"][0]
    assert first["card_number"] == tide and first["stage"] == "folded"
    assert first["folded"] is True and first["reviewed"] is False
    assert first["stopped_to_ask"] is False and first["fold_reverted"] is False
    assert first["class_closer"] == "a boot check refuses a clock that disagrees with the office"
    assert report["rail_now"][0]["project"] == "proj"
    assert report["rail_at_first_on"][0]["total"] == 3, "the boat, the tide clock and the gate log"
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert f"proj #{tide}" in out and "folded; folded; no review record" in out
    assert "class: a boot check refuses" in out
    assert "2 fix lanes, 1 closed: 0 folded with a review record" in out
    assert "rail proj:" in out and "(was 3 at dial-on)" in out


def test_his_and_unmarked_defects_are_never_started_and_a_question_leaves_the_card_to_the_owner(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    live = client.app.state.loops.live
    # The fixture's only `now` defect is marked his for this test; the night
    # audit defect has no Fix: line at all.
    tide_file = repo / TIDE_PATH
    tide_file.write_text(
        tide_file.read_text(encoding="utf-8").replace("**Fix:** now —", "**Fix:** his —"),
        encoding="utf-8",
    )
    live.rescan("proj")
    reconcile(client)
    turn(client, on=True, lanes=3)
    tick(client)
    assert machine_floor.state()["launch_log"] == []
    tide = number_of(client, TIDE)
    assert detail(client, tide)["summary"]["fix"]["mark"] == "his"
    audit = number_of(client, "The night audit re-reads the whole harbour log")
    assert detail(client, audit)["summary"]["kind"] == "defect"
    assert detail(client, audit)["summary"]["fix"] is None
    assert detail(client, audit)["document"]["fix_note"] == "no Fix: line"

    # A `now` defect whose planning session finds a decision that is his:
    # the ASK row on the card ends the dial's part, and it is not taken again.
    write_defect(
        repo,
        "2026-09-05-the-berth-map-hides-the-fuel-dock",
        "The berth map hides the fuel dock",
        "**Fix:** now",
    )
    live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The berth map hides the fuel dock")
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == 1
    assert (
        main(["row", "proj", str(number), "ASK", "should the dock be a berth or a landmark?"]) == 0
    )
    tick(client)
    fixes = store.fix_lanes("proj")
    assert [(f.card_number, f.stage.value) for f in fixes] == [(number, "asked")]
    assert fixes[0].note == "should the dock be a berth or a landmark?"
    history = detail(client, number)["history"]
    assert any(
        h["detail"]
        == "The planning session left it to you: should the dock be a berth or a landmark?"
        for h in history
    )
    assert detail(client, number)["summary"]["planning"] is None
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == 1, "asked: the owner's from here"
    assert board(client)["dial"]["running"] == 0


def test_a_planning_session_that_dies_ends_the_dials_part_and_the_card_says_why(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    turn(client, on=True, lanes=1)
    machine_floor.script_launches({"then": "vanish", "after": 1.5})
    tick(client)
    tide = number_of(client, TIDE)
    assert store.fix_lanes("proj")[0].stage.value == "planning"
    import time

    time.sleep(2.5)
    tick(client)
    fix = store.fix_lanes("proj")[0]
    assert fix.stage.value == "ended" and fix.note is not None
    assert fix.note.startswith("the planning session ended without a plan")
    assert detail(client, tide)["history"][0]["detail"] == fix.note
    assert detail(client, tide)["summary"]["planning"] is None
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == 1, "not taken again"


# ── item 1: the close refuses a code lane without a review record ──────


def test_a_code_lane_cannot_close_without_a_review_record_and_a_docs_lane_can(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    doors.start(client)
    started = machine_floor.state()["launch_log"][0]
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    (worktree / "engine").mkdir(exist_ok=True)
    (worktree / "engine" / "meter.py").write_text("bill = True\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "the meter")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    capsys.readouterr()
    done = archive_plan(repo)
    watch = f"the plan is archived — file {done.relative_to(repo)} by 2026-12-31 every 1h"
    assert main(["close", "proj", str(CARD), "--delivered", "bills", "--watch", watch]) == 1
    err = capsys.readouterr().err
    assert f"#{CARD}'s lane folded code (engine/meter.py)" in err
    assert f"a file at {repo}/docs/reviews/<file>.md" in err
    assert column_of(client, CARD) == "Executing", "nothing was written"
    assert [r["kind"] for r in detail(client)["record"]] == []
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "bills",
                "--watch",
                watch,
                "--review",
                "docs/reviews/2026-09-05-the-meter.md",
            ]
        )
        == 1
    )
    err = capsys.readouterr().err
    assert "is not in the project's tree; expected" in err
    assert f"{repo}/docs/reviews/2026-09-05-the-meter.md" in err
    (repo / "docs" / "reviews").mkdir(exist_ok=True)
    (repo / "docs" / "reviews" / "2026-09-05-the-meter.md").write_text("# Review\n")
    assert (
        main(
            [
                "close",
                "proj",
                str(CARD),
                "--delivered",
                "bills",
                "--watch",
                watch,
                "--review",
                "docs/reviews/2026-09-05-the-meter.md",
            ]
        )
        == 0
    )
    assert "DELIVERED, WATCH, REVIEW" in capsys.readouterr().out
    client.app.state.loops.live.rescan("proj")
    assert column_of(client, CARD) == "Executed"
    assert claim_count(board(client), "no review") == 0


def test_a_docs_only_close_passes_without_a_review_and_the_head_counts_it(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    doors.start(client)
    started = machine_floor.state()["launch_log"][0]
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    plan = next(worktree.glob("docs/plans/*metered*"))
    shutil.move(plan, worktree / "docs" / "plans" / "done" / plan.name)
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "archive")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    capsys.readouterr()
    live = client.app.state.loops.live
    live.rescan("proj")
    watch = f"the plan is archived — file docs/plans/done/{plan.name} by 2026-12-31 every 1h"
    assert main(["close", "proj", str(CARD), "--delivered", "the docs", "--watch", watch]) == 0
    assert "DELIVERED, WATCH written" in capsys.readouterr().out
    live.rescan("proj")
    assert column_of(client, CARD) == "Executed"
    state = board(client)
    assert claim_count(state, "no review") == 1
    shipped = next(
        c
        for col in state["columns"]
        for g in col["groups"]
        for c in g["cards"]
        if c["number"] == CARD
    )
    assert "no review" in shipped["claims"]


# ── item 5: a trigger is a signal ──────────────────────────────────────


def test_a_when_trigger_is_read_on_the_cadence_and_delivered_makes_the_defect_eligible(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, monkeypatch
):
    live = client.app.state.loops.live
    # The fixture's `now` defect would be taken first; it is his for this test.
    tide_file = repo / TIDE_PATH
    tide_file.write_text(
        tide_file.read_text(encoding="utf-8").replace("**Fix:** now —", "**Fix:** his —"),
        encoding="utf-8",
    )
    write_defect(
        repo,
        "2026-09-05-the-tariff-page-names-no-season",
        "The tariff page names no season",
        "**Fix:** when the tariff page exists — file docs/tariff.md by 2026-12-31 every 1h",
    )
    live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The tariff page names no season")
    opened = detail(client, number)
    assert opened["summary"]["fix"]["mark"] == "when"
    assert opened["trigger"]["kind"] == "file" and opened["trigger"]["target"] == "docs/tariff.md"
    read_signals(client)
    waiting = detail(client, number)
    assert waiting["readings"][0]["delivered"] is False
    assert "does not exist" in waiting["readings"][0]["words"]
    assert column_of(client, number) == "Backlog", "a trigger's reading moves nothing"
    turn(client, on=True, lanes=1)
    tick(client)
    assert machine_floor.state()["launch_log"] == [], "not delivered: the defect waits"

    (repo / "docs" / "tariff.md").write_text("# Tariff\n", encoding="utf-8")
    read_signals(client)
    assert len(detail(client, number)["readings"]) == 1, "not due again yet"
    later = datetime.now(UTC) + timedelta(hours=1, minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    read_signals(client)
    fired = detail(client, number)
    assert fired["readings"][0]["delivered"] is True
    assert column_of(client, number) == "Backlog"
    tick(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == 1 and log[0]["argv"][log[0]["argv"].index("-n") + 1].startswith(
        f"planning-card-{number}-"
    ), "delivered: eligible as a now"


def test_a_session_trigger_starts_a_reading_and_cannot_tell_asks_the_owner_without_moving(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    live = client.app.state.loops.live
    write_defect(
        repo,
        "2026-09-05-a-slip-is-mailed-before-its-berth-is-let",
        "A slip is mailed before its berth is let",
        "**Fix:** when a second such slip exists — session the mail log for a duplicate slip since "
        "2026-09-05 by 2026-12-31 every 1d",
    )
    live.rescan("proj")
    reconcile(client)
    number = number_of(client, "A slip is mailed before its berth is let")
    read_signals(client)
    launched = machine_floor.state()["launch_log"][0]
    assert launched["argv"][launched["argv"].index("-n") + 1].startswith(f"reading-card-{number}-")
    brief = launched["argv"][-1]
    assert brief.startswith(f"A reading of #{number}'s trigger")
    assert "The trigger to read: a second such slip exists" in brief
    assert "the dial may take the card; nothing moves" in brief
    assert detail(client, number)["summary"]["reading"]["session_id"] == launched["session_id"]

    words = "the mail log holds one slip since the fifth; a second would decide it"
    assert main(["reading", "proj", str(number), "cannot-tell", words]) == 0
    assert "the owner is asked with your words" in capsys.readouterr().out
    assert column_of(client, number) == "Backlog"
    reconcile(client)
    state = board(client)
    assert claim_count(state, "signal asking") == 1
    assert state["asks"][0] == {
        "number": number,
        "title": "A slip is mailed before its berth is let",
        "what": "a second such slip exists",
        "due": "2026-12-31",
        "kind": "session",
        "evidence": words,
    }
    asked = detail(client, number)
    assert asked["doors"]["signal"]["offered"]
    assert asked["summary"]["state"]["word"] == "trigger for you to read"
    assert asked["summary"]["state"]["meaning"] == "yours"
    answered = client.post(f"/api/projects/proj/cards/{number}/signal", json={"delivered": True})
    assert answered.status_code == 200, answered.text
    assert "the defect is eligible for the dial" in answered.json()["said"]
    assert column_of(client, number) == "Backlog"
    assert detail(client, number)["readings"][0]["actor"] == "owner"
    # A replacement WATCH row is not how a trigger is changed.
    assert (
        main(
            [
                "reading",
                "proj",
                str(number),
                "delivered",
                "x",
                "--watch",
                "y — file z by 2026-12-31",
            ]
        )
        == 1
    )
    assert "lives on the suggestion's Fix: when line" in capsys.readouterr().err


# ── the owner's terminal ───────────────────────────────────────────────


def test_needle_dial_reads_and_turns_the_dial_from_the_terminal(
    client: TestClient, store: Store, capsys
):
    assert main(["dial"]) == 0
    assert capsys.readouterr().out.startswith("auto-fix off, 1 fix lane at most; 0 live now")
    assert main(["dial", "on", "--lanes", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("auto-fix on, 2 fix lanes at most; 0 live now; the machine is quiet")
    assert "first turned on" in out
    assert [(c.actor.value, c.on, c.lanes) for c in store.dial_changes()] == [("owner", True, 2)]
    assert main(["dial", "--lanes", "0"]) == 0
    assert capsys.readouterr().out.startswith("auto-fix on, 0 fix lanes at most")
    assert board(client)["dial"]["dial"]["lanes"] == 0
