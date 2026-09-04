"""A session reads the signal (plan 09), on the floor: a `session` signal
due now starts a reading session the card lists and the board never reads
as hands on a tree; its finding, through `needle reading`, moves the card —
delivered to Done, not delivered to Decision moment, cannot tell to the
owner's batch with the session's words; a replacement WATCH row is read on
the next cadence with the original in the history; a reading session that
dies or overruns is recorded and never asks the owner; at most
READINGS_AT_ONCE run at a time, and a finished one is stopped.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import loops as loops_mod
from api.cli import main
from domain.signal import SessionWork
from infrastructure import clock
from tests.api import test_doors as doors
from tests.api.attention import claim_count, yours
from tests.api.test_doors import CARD, archive_plan, column_of, detail, read_signals, reconcile
from tests.floor import Floor

# The fixtures a door test stands on: the repository with an origin, the
# served board over it, and the floor's quick deadlines.
client = doors.client
repo = doors.repo
quick = doors.quick

FAR = "2026-12-31"
SIGNAL = (
    "the meter's rows say so — session the billing ledger through the read-only role: "
    f"metered rows since 2026-09-04, per berth by {FAR} every 1h"
)


def close_with_session_signal(client: TestClient, repo: Path, watch: str = SIGNAL) -> None:
    archive_plan(repo)
    assert (
        main(["close", "proj", str(CARD), "--delivered", "the meter bills", "--watch", watch]) == 0
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert column_of(client, CARD) == "Executed"


def board(client: TestClient) -> dict:
    return client.get("/api/projects/proj/board").json()


def test_a_session_signal_starts_a_reading_the_card_lists_and_delivered_moves_it_to_done(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, monkeypatch
):
    close_with_session_signal(client, repo)
    assert detail(client)["signal"]["kind"] == "session"
    read_signals(client)

    launched = machine_floor.state()["launch_log"][0]
    assert launched["cwd"] == str(repo) and "--worktree" not in launched["argv"]
    assert launched["argv"][launched["argv"].index("-n") + 1] == (
        "reading-card-253-every-metered-kilowatt-is-billed"
    )
    assert launched["argv"][launched["argv"].index("--effort") + 1] == "high"
    brief = launched["argv"][-1]
    assert brief.startswith("A reading of #253's signal, started by the board on Harbourmaster")
    assert "never EnterWorktree" in brief and "needle reading proj 253 cannot-tell" in brief
    assert "the meter's rows say so — the billing ledger through the read-only role" in brief
    assert "What the session that shipped it said the owner now has: the meter bills" in brief
    assert "Ask the owner nothing" in brief

    reading = detail(client)
    assert column_of(client, CARD) == "Executed"
    assert reading["summary"]["reading"]["session_id"] == launched["session_id"]
    assert reading["summary"]["reading"]["slot"] == "alpha"
    assert reading["summary"]["lane_state"] == "none", "a reading is never hands on the tree"
    assert reading["doors"]["signal"]["offered"] is False
    assert reading["history"][0]["detail"].startswith(
        f"Reading started: {launched['short']}, fable on alpha"
    )
    state = board(client)
    assert claim_count(state, "signal reading") == 1 and state["asks"] == []
    assert claim_count(state, "signal asking") == 0

    read_signals(client)
    assert len(machine_floor.state()["launch_log"]) == 1, "one reading per card at a time"

    assert (
        main(
            [
                "reading",
                "proj",
                str(CARD),
                "delivered",
                "select count(*) from metered_rows where read_at >= '2026-09-04': 3, one per berth",
            ]
        )
        == 0
    )
    assert "#253 read as delivered; moved to Done." in capsys.readouterr().out
    assert column_of(client, CARD) == "Done"
    done = detail(client)
    assert done["readings"][0]["actor"] == "session" and done["readings"][0]["delivered"] is True
    assert done["summary"]["reading"] is None
    assert (
        done["history"][0]["actor"] == "machine"
        and "the signal says delivered" in (done["history"][0]["detail"])
    )
    assert claim_count(board(client), "signal reading") == 0

    # The finished reading session is stopped by the loop once its turn is
    # over — on the floor the fake stays "working", so the grace decides.
    monkeypatch.setattr(loops_mod, "READING_STOP_GRACE_SECONDS", 0.0)
    read_signals(client)
    assert [s["short"] for s in machine_floor.state().get("stops", [])] == [launched["short"]]


def test_not_delivered_lands_in_decision_moment_now_and_a_bad_finding_is_refused(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    close_with_session_signal(client, repo)
    read_signals(client)
    assert main(["reading", "proj", str(CARD), "not-delivered", "   "]) == 1
    assert "without its evidence" in capsys.readouterr().err
    assert (
        main(
            ["reading", "proj", str(CARD), "not-delivered", "the ledger has no row since the close"]
        )
        == 0
    )
    assert column_of(client, CARD) == "Decision moment"
    history = detail(client)["history"]
    assert history[0]["detail"].endswith(
        "a session read the signal as not delivered: the meter's rows say so"
    )
    assert history[0]["evidence"] == "signal-failed"
    assert main(["reading", "proj", str(CARD), "delivered", "again"]) == 1
    assert "is in Decision moment" in capsys.readouterr().err


def test_cannot_tell_asks_the_owner_with_the_sessions_words_and_his_click_answers(
    client: TestClient, machine_floor: Floor, repo: Path
):
    close_with_session_signal(client, repo)
    read_signals(client)
    words = "no metered row since the close; the next meter read is Friday's, which decides it"
    assert main(["reading", "proj", str(CARD), "cannot-tell", words]) == 0
    assert column_of(client, CARD) == "Executed"
    assert detail(client)["history"][0]["detail"].startswith(f"Signal read as cannot tell: {words}")
    state = board(client)
    assert claim_count(state, "signal asking") == 1 and yours(state) >= 1
    assert state["asks"] == [
        {
            "number": CARD,
            "title": "Every metered kilowatt is billed",
            "what": "the meter's rows say so",
            "due": FAR,
            "kind": "session",
            "evidence": words,
        }
    ]
    reconcile(client)
    asked = detail(client)
    assert asked["doors"]["signal"]["offered"]
    assert (
        asked["doors"]["signal"]["why"]
        == f"A session read this signal and could not tell — {words}"
    )
    answered = client.post(f"/api/projects/proj/cards/{CARD}/signal", json={"delivered": True})
    assert answered.status_code == 200, answered.text
    assert column_of(client, CARD) == "Done"
    assert detail(client)["readings"][0]["actor"] == "owner"


def test_a_replacement_watch_row_is_read_on_the_next_cadence_with_the_original_in_the_history(
    client: TestClient, machine_floor: Floor, repo: Path, monkeypatch
):
    close_with_session_signal(client, repo)
    read_signals(client)
    replacement = (
        "wall-clock per berth is under the 16 Aug baseline — session the meter ledger's "
        f"read_seconds per berth against 2026-08-16's, per read by {FAR} every 2d"
    )
    assert (
        main(
            [
                "reading",
                "proj",
                str(CARD),
                "cannot-tell",
                "an hour per read ignores how many berths a read covers; per berth is readable",
                "--watch",
                replacement,
            ]
        )
        == 0
    )
    after = detail(client)
    assert after["signal"]["target"].startswith("the meter ledger's read_seconds per berth")
    assert after["signal"]["every_hours"] == 48
    assert [r["text"] for r in after["record"] if r["kind"] == "WATCH"] == [replacement]
    rewritten = next(h for h in after["history"] if h["detail"].startswith("WATCH rewritten"))
    assert "it read: the meter's rows say so — session the billing ledger" in rewritten["detail"]
    assert column_of(client, CARD) == "Executed"

    read_signals(client)
    assert len(machine_floor.state()["launch_log"]) == 1, "not due again yet"
    later = datetime.now(UTC) + timedelta(days=2, minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    read_signals(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == 2 and "per berth against 2026-08-16's" in log[1]["argv"][-1]


def test_a_reading_that_dies_or_overruns_is_recorded_and_never_asks_the_owner(
    client: TestClient, machine_floor: Floor, repo: Path, monkeypatch
):
    close_with_session_signal(client, repo)
    machine_floor.script_launches({"then": "vanish", "after": 1.5})
    read_signals(client)
    launched = machine_floor.state()["launch_log"][0]
    assert detail(client)["summary"]["reading"] is not None
    import time

    time.sleep(2.5)
    read_signals(client)
    gone = detail(client)
    assert gone["summary"]["reading"] is None
    assert gone["readings"][0]["actor"] == "machine" and gone["readings"][0]["delivered"] is None
    assert gone["readings"][0]["words"].startswith("the reading session ended without a finding")
    assert column_of(client, CARD) == "Executed", "not yet due: the next cadence reads again"
    assert board(client)["asks"] == [], "a machine's unreadable is not the owner's question"
    assert len(machine_floor.state()["launch_log"]) == 1, "the cadence waits"

    # A reading still without a finding past READING_SECONDS is stopped.
    later = datetime.now(UTC) + timedelta(hours=2)
    monkeypatch.setattr(clock, "now", lambda: later)
    read_signals(client)
    second = machine_floor.state()["launch_log"][1]
    assert second["short"] != launched["short"]
    monkeypatch.setattr(loops_mod, "READING_SECONDS", 0.0)
    read_signals(client)
    stopped = detail(client)
    assert stopped["summary"]["reading"] is None
    assert "without a finding and was stopped" in stopped["readings"][0]["words"]
    assert [s["short"] for s in machine_floor.state()["stops"]] == [second["short"]]


def test_a_reading_that_hits_a_limit_is_moved_like_a_lane_and_the_record_follows(
    client: TestClient, machine_floor: Floor, repo: Path
):
    close_with_session_signal(client, repo)
    machine_floor.script_launches(
        {"then": "wall", "after": 1.5, "reason": "You've reached your Fable limit."},
        {"then": "work"},
    )
    read_signals(client)
    first = machine_floor.state()["launch_log"][0]
    import time

    time.sleep(2.5)
    read_signals(client)
    log = machine_floor.state()["launch_log"]
    assert (
        len(log) == 2
        and log[1]["argv"][log[1]["argv"].index("--resume") + 1] == (first["session_id"])
    )
    moved = detail(client)
    assert moved["summary"]["reading"]["session_id"] == log[1]["session_id"]
    assert moved["summary"]["reading"]["slot"] == "beta"
    assert moved["history"][0]["detail"].startswith("Reading moved: hit a limit on alpha")
    assert column_of(client, CARD) == "Executed" and moved["readings"] == []


def test_at_most_readings_at_once_run_and_the_rest_wait_for_the_next_tick(
    client: TestClient, machine_floor: Floor, repo: Path, monkeypatch
):
    close_with_session_signal(client, repo)
    monkeypatch.setattr(loops_mod, "READINGS_AT_ONCE", 1)
    store = client.app.state.loops.live.store
    # Another card's reading, alive on beta: this very process stands in for it.
    other_id = machine_floor.write_job("beta", "bbbb0001", cwd=str(repo), name="reading-card-174")
    machine_floor.write_process("beta", other_id, os.getpid(), cwd=str(repo))
    other = store.open_windowless_session(
        "proj", 174, SessionWork.READING, other_id, "beta", datetime.now(UTC)
    )
    read_signals(client)
    assert machine_floor.state()["launch_log"] == [], "another card's reading holds the one slot"
    store.end_windowless_session(other.id, datetime.now(UTC))
    read_signals(client)
    assert len(machine_floor.state()["launch_log"]) == 1


def test_a_reading_that_cannot_start_is_a_machine_reading_and_the_card_says_why(
    client: TestClient, machine_floor: Floor, repo: Path
):
    close_with_session_signal(client, repo)
    machine_floor.refuse_best("every subscription is spent until 18:00")
    read_signals(client)
    failed = detail(client)
    assert failed["summary"]["reading"] is None
    assert failed["readings"][0]["words"].startswith("the reading session could not start:")
    assert "spent until 18:00" in failed["readings"][0]["words"]
    assert column_of(client, CARD) == "Executed" and board(client)["asks"] == []


@pytest.mark.parametrize(
    "text",
    [
        "did its session land — session by 2026-12-31",
        "x — session the ledger",
    ],
)
def test_a_session_row_needs_a_target_and_a_due_date(text: str, capsys):
    from board.signals import read_or_decline

    signal, why = read_or_decline(text)
    assert signal is None and ("no target" in why or "no due date" in why)
