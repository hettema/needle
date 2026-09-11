"""Every Start assigns one team before the work (card #58, item 1): it is
in the brief, on the card and in its history, it is written once and a
restart keeps it, a plan's own line pins it, and the reading behind it can
be read from the terminal and the API.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from domain.slot import Make
from domain.team import POLICY, Challenge, Conclusion, Hand, Route, Shape
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, detail, git, start
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


def test_start_assigns_a_team_before_the_work_and_says_it_everywhere(
    client: TestClient, machine_floor: Floor, repo: Path
):
    before = detail(client)
    assert before["team"] is None
    said = start(client)
    assert "; team: the accountable hand alone — the hand is claude, alpha; nobody challenges; " in said["said"]
    assert "exploring: exploring alone: fewer than 3 trials" in said["said"]

    brief = machine_floor.state()["launch_log"][0]["argv"][-1]
    assert "YOUR TEAM — assigned by the board before this Start" in brief
    assert "the accountable hand alone — the hand is claude, alpha; nobody challenges" in brief
    assert "nobody challenges your plan before you build" in brief
    assert "run needle call <claude slot> <note>`" in brief and f"Policy {POLICY}." in brief

    after = detail(client)
    team = after["team"]
    assert team["card_number"] == CARD and team["route"]["policy"] == POLICY
    assert team["route"] == {
        "shape": "bounded",
        "challenge": "alone",
        "hand": {"make": "claude", "model": None, "slot": "alpha"},
        "challenger": None,
        "challenger_model": None,
        "conclusion": "exploring",
        "why": "exploring alone: fewer than 3 trials under alone, same-make, different-make "
        "(alone 0, same-make 0, different-make 0)",
        "observations": [],
        "policy": POLICY,
    }
    told = [h for h in after["history"] if h["kind"] == "started" and h["detail"].startswith("team: ")]
    assert len(told) == 1 and told[0]["actor"] == "machine"
    assert told[0]["detail"] == "team: the accountable hand alone — the hand is claude, alpha; " + (
        "nobody challenges; exploring: exploring alone: fewer than 3 trials under alone, "
        "same-make, different-make (alone 0, same-make 0, different-make 0)"
    )

    reading = client.get("/api/projects/proj/team").json()
    assert reading["policy"] == POLICY and [s["shape"] for s in reading["shapes"]] == [
        "judgment",
        "bounded",
        "reading",
    ]
    assert all(s["conclusion"] == "exploring" for s in reading["shapes"])
    assert [a["card_number"] for a in reading["assigned"]] == [CARD]


def test_a_card_keeps_the_team_its_first_start_assigned(
    client: TestClient, machine_floor: Floor, repo: Path
):
    store = client.app.state.live.store
    held = Route(
        shape=Shape.BOUNDED,
        challenge=Challenge.DIFFERENT_MAKE,
        hand=Hand(make=Make.CLAUDE, model=None, slot="alpha"),
        challenger=Make.CODEX,
        conclusion=Conclusion.EXPLORING,
        why="the first Start's reading",
        observations=[],
    )
    store.record_composition("proj", CARD, held, datetime(2026, 9, 10, tzinfo=UTC))
    said = start(client)
    assert "; team: a different-make challenge — the hand is claude, alpha; codex challenges; " in said["said"]
    brief = machine_floor.state()["launch_log"][0]["argv"][-1]
    assert "codex challenges; exploring: the first Start's reading" in brief
    assert "run needle call codex --fresh <note>`" in brief
    assert "**Challenged:** <date>, by <who> (call <n>): <N> material corrections before build" in brief
    after = detail(client)
    assert after["team"]["route"]["why"] == "the first Start's reading"
    assert after["team"]["assigned_at"].startswith("2026-09-10")
    assert not [h for h in after["history"] if h["detail"].startswith("team: ")], (
        "a restart writes no second assignment"
    )


def test_a_plans_own_composition_line_pins_the_team_with_its_reason(
    client: TestClient, machine_floor: Floor, repo: Path
):
    plan = next(repo.glob("docs/plans/*metered*"))
    text = plan.read_text(encoding="utf-8")
    pinned = text.replace(
        "**Effort gate:**",
        "**Composition:** same-make challenge — the parser touches money, so a second pair of "
        "eyes of the same make reads it before it lands\n**Effort gate:**",
        1,
    )
    plan.write_text(pinned, encoding="utf-8")
    git(repo, "commit", "-qam", "pin")
    client.app.state.live.rescan("proj")
    said = start(client)
    assert "; team: a same-make challenge — the hand is claude, alpha; claude challenges; pinned: " in said["said"]
    assert "the plan pins it: the parser touches money" in said["said"]
    assert detail(client)["team"]["route"]["conclusion"] == "pinned"


def test_the_terminal_prints_the_reading(client: TestClient, repo: Path, capsys):
    start(client)
    assert main(["team", "proj"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"policy {POLICY}; read ")
    assert "bounded: exploring — fewer than 3 trials" in out
    assert "    alone           0 trials: no challenge before build; 0 escaped a defect (0)" in out
    assert "reading: exploring" in out
    assert f"assigned #{CARD}" in out and "the accountable hand alone" in out
    assert main(["team", "nowhere"]) == 1


def test_a_launch_that_dies_assigns_no_team(client: TestClient, machine_floor: Floor):
    machine_floor.script_launches({"then": "vanish"})
    response = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"anyway": False})
    assert response.status_code == 502
    after = detail(client)
    assert after["team"] is None
    assert not [h for h in after["history"] if h["detail"].startswith("team: ")]
    assert client.get("/api/projects/proj/team").json()["assigned"] == []
