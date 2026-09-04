"""The runtime's verbs on the command line, run in-process on the fixture floor."""

import json
from pathlib import Path

import pytest

from api.cli import main
from runtime import launch, windows
from tests.floor import Floor


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    monkeypatch.setattr(windows, "WINDOW_VERIFY_SECONDS", 1.5)
    monkeypatch.setenv("NEEDLE_DB", str(tmp_path / "needle.db"))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    return root


def test_where_prints_the_rules_answer(machine_floor: Floor, capsys):
    machine_floor.answer_best("beta", None, "Fable headroom on beta")

    assert main(["where", "--from", "alpha", "--tried", "alpha:fable"]) == 0
    assert capsys.readouterr().out.strip() == "fable on beta — Fable headroom on beta"
    assert machine_floor.state()["best_calls"][-1] == [
        "best",
        "--json",
        "--cached",
        "--from",
        "alpha",
        "--tried",
        "alpha:fable",
    ]

    machine_floor.refuse_best("no account with headroom")
    assert main(["where", "--live"]) == 1
    assert capsys.readouterr().out.startswith("nowhere: ")


def test_start_sessions_window_stop_from_the_command_line(machine_floor: Floor, repo: Path, capsys):
    assert (
        main(["start", str(repo), "card-4-the-verb", "do the thing", "--effort", "high", "--json"])
        == 0
    )
    started = json.loads(capsys.readouterr().out)
    assert started["verdict"] == "alive" and started["session"]["slot"] == "alpha"
    short = started["session"]["short_id"]

    assert main(["sessions"]) == 0
    listed = capsys.readouterr().out
    assert short in listed and "working" in listed and "card-4-the-verb" in listed

    assert main(["window", short]) == 0
    assert capsys.readouterr().out.startswith(
        f"opened org.omarchy.lane-card-4-the-verb (0xfake0001) into {short}"
    )
    assert main(["window", short]) == 1
    assert "already has a window" in capsys.readouterr().err

    assert main(["rescues", short]) == 0
    assert capsys.readouterr().out.strip() == f"no rescues recorded for {short}"

    assert main(["stop", short]) == 0
    assert capsys.readouterr().out.startswith(f"{short} on alpha: gone after")
    assert main(["sessions", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["state"] for r in rows if r["short_id"] == short] == ["ended"]


def test_move_and_rescues_from_the_command_line(machine_floor: Floor, repo: Path, capsys):
    main(["start", str(repo), "card-5-moves", "go", "--json"])
    started = json.loads(capsys.readouterr().out)
    short, session_id = started["session"]["short_id"], started["session"]["session_id"]
    machine_floor.write_handoff(
        session_id, account="beta", reason="You've hit your session limit · resets 12pm"
    )

    assert main(["move", short]) == 0
    said = capsys.readouterr().out
    assert said.startswith(f"{short} is alive: card-5-moves on beta with fable")
    assert main(["rescues", short]) == 0
    assert (
        "alpha/fable → beta/fable  You've hit your session limit · resets 12pm"
        in capsys.readouterr().out
    )
    assert main(["rescues", short, "--clear"]) == 0
    assert (
        capsys.readouterr().out.strip()
        == f"cleared 1 rescue row for {short}; its slot record is untouched"
    )


def test_an_unknown_session_is_named(machine_floor: Floor, capsys):
    assert main(["stop", "nope0000"]) == 1
    assert "no session 'nope0000'" in capsys.readouterr().err
