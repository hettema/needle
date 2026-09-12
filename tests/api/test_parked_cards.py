"""A decision parked on the owner leaves his column when the record already
answers it (card #82), on the floor: every card in Decision moment gets one
cold reading behind the defects and the titles, the four results land
where the plan says with the reason on the card's history, a `stale` on a
card carrying a commitment is refused naming it, the owner's move after
the machine's is never undone, his answer is what re-reads the card, and
the reading session cannot close the card while it reads."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from board.brief import COMMITMENT_RULE, THE_RULE, needle_command
from infrastructure import clock
from tests.api import test_doors as doors
from tests.api.test_dial import (
    SOURCE,
    is_parked,
    open_readings,
    read_the_rail_until,
    tick,
)
from tests.api.test_doors import column_of, detail, move, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

BERTH_FIRST = 139
"""Parked with a live plan and an ASK: what `now` can move to Planned."""
BANK = 147
"""Parked with an ASK and no document: what a `stale` may not close."""
COUNCIL = 149
"""Parked with an ASK: what `waiting` sends to Executed."""
PRICING = 219
"""Parked with a DELIVERED and a WATCH the board cannot read (item 3's case)."""
PARKED_IN_ORDER = [BERTH_FIRST, BANK, COUNCIL, PRICING]
BRIEF = Path(__file__).parent / "briefs" / "a-card-parked-on-the-owner.txt"
"""What the cold reading of #139 opens with, as the board built it."""
"""The fixture's four (its fifth is the board's own ask, never a card), as
the beat reads them: same park, oldest number first."""


def triage(number: int, *words: str) -> int:
    return main(["triage", "proj", str(number), *words])


def history(client: TestClient, number: int) -> list[dict]:
    return detail(client, number)["history"]


def face(client: TestClient, number: int) -> str:
    return detail(client, number)["summary"]["state"]["detail"]


def test_every_parked_card_is_read_once_and_the_four_results_land_where_the_plan_says(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    for number in PARKED_IN_ORDER:
        assert is_parked(client, number)

    # ── #139: the brief, the refusals, and `now` to Planned ────────────
    launch = read_the_rail_until(client, machine_floor, BERTH_FIRST)
    brief = launch["argv"][-1]
    assert brief.startswith(f"A cold reading of #{BERTH_FIRST}, a card parked on the owner")
    assert THE_RULE in brief and COMMITMENT_RULE in brief
    assert "The card's history, oldest first" in brief and "born:" in brief
    assert "--- the document (docs/plans/2026-08-18-berth-first-booking.md)" in brief
    assert "a question in your words with no answer (ASK): Four rulings, one sitting." in brief
    assert "never moves the card" in brief and "no `cannot-tell` here" in brief
    # The brief is a fixture the tests read (item 1): the whole text, with
    # the test project's path and the day the reading opened normalised.
    # Regenerate with NEEDLE_WRITE_BRIEFS=1 after a deliberate change.
    shown = (
        brief.replace(str(repo), "<project>")
        .replace(clock.now().date().isoformat(), "<today>")
        .replace(needle_command(), "<needle>")
    )
    if os.environ.get("NEEDLE_WRITE_BRIEFS"):
        BRIEF.write_text(shown, encoding="utf-8")
    assert shown == BRIEF.read_text(encoding="utf-8"), f"the brief changed; see {BRIEF}"
    for fifth in ("when", "split", "cannot-tell"):
        assert triage(BERTH_FIRST, fifth, "x") == 1
        assert "lands one of his, now, stale, waiting" in capsys.readouterr().err
    assert triage(BERTH_FIRST, "his", "which?", "--title", "passes") == 1
    assert "not the title" in capsys.readouterr().err
    assert triage(BERTH_FIRST, "now", "the plan settles it") == 1
    assert "needs a source" in capsys.readouterr().err
    assert triage(BERTH_FIRST, "now", "the plan settles it", "--source", SOURCE) == 1
    assert "which way it moves" in capsys.readouterr().err
    assert (
        triage(
            BERTH_FIRST,
            "now",
            "the plan's four rulings are written in it; execution",
            "--source",
            SOURCE,
            "--direction",
            "no direction",
        )
        == 0
    )
    assert "moved to Planned" in capsys.readouterr().out
    reconcile(client)
    assert column_of(client, BERTH_FIRST) == "Planned"
    moved = next(h for h in history(client, BERTH_FIRST) if h["kind"] == "moved")
    assert moved["actor"] == "machine" and moved["evidence"] == "record-answered"
    assert "a cold reading found the record already answers it:" in moved["detail"]
    assert f"(source `{SOURCE}`)" in moved["detail"]
    opened = detail(client, BERTH_FIRST)
    assert opened["summary"]["standing"]["state"] == "held"
    assert opened["decision"]["result"] == "now" and opened["decision"]["ground"] == "parked"
    assert any(r["kind"] == "TRIAGED" and r["text"].startswith("now") for r in opened["record"])
    assert BERTH_FIRST not in open_readings(client), "read once; not again while it sits there"

    # The owner moves it back: his park is final, the machine never undoes it.
    move(client, BERTH_FIRST, "Decision moment")
    reconcile(client)
    tick(client)
    assert column_of(client, BERTH_FIRST) == "Decision moment"

    # ── #147: a `stale` on an open question is refused, naming it ──────
    read_the_rail_until(client, machine_floor, BANK)
    assert triage(BANK, "stale", "the terminal was replaced") == 1
    refused = capsys.readouterr().err
    assert "leaves Decision moment only when every commitment" in refused
    assert "a question in your words with no answer (ASK): Which account?" in refused
    assert column_of(client, BANK) == "Decision moment"
    assert "unaccounted for" in face(client, BANK) and "Which account?" in face(client, BANK)
    assert face(client, BANK).startswith("Your move")
    assert BANK in open_readings(client), "the reading stays open for `his`"
    assert triage(BANK, "his", "Which account takes the deposits: the old one or the new?") == 0
    assert "stays, with your line" in capsys.readouterr().out
    reconcile(client)
    assert column_of(client, BANK) == "Decision moment"
    assert "Which account takes the deposits: the old one or the new?" in face(client, BANK)
    assert face(client, BANK).startswith("Your move")
    assert BANK not in open_readings(client)
    opened = detail(client, BANK)
    assert opened["doors"]["answer"]["offered"], opened["doors"]["answer"]["why"]
    assert "the decision is yours" in opened["doors"]["answer"]["why"]
    tick(client)
    assert BANK not in open_readings(client), "not read again until parked again or answered"

    # ── #149: `waiting` writes the WATCH row and moves the card ────────
    read_the_rail_until(client, machine_floor, COUNCIL)
    signal = "the season report was read before the council — owner by 2026-12-01"
    assert triage(COUNCIL, "waiting", signal) == 0
    assert "moved to Executed" in capsys.readouterr().out
    reconcile(client)
    assert column_of(client, COUNCIL) == "Executed"
    opened = detail(client, COUNCIL)
    assert any(r["kind"] == "WATCH" and r["text"] == signal for r in opened["record"])
    moved = next(h for h in opened["history"] if h["kind"] == "moved")
    assert moved["actor"] == "machine" and moved["evidence"] == "record-answered"
    assert "a cold reading found it waits for a signal" in moved["detail"]
    assert opened["summary"]["standing"]["state"] == "held"

    # ── #219: the DELIVERED with no signal refuses `stale`; `waiting` moves
    read_the_rail_until(client, machine_floor, PRICING)
    assert triage(PRICING, "stale", "the season is over") == 1
    refused = capsys.readouterr().err
    assert "a DELIVERED with no signal the board can read" in refused
    assert "The read-out, with the two seasons side by side." in refused
    assert column_of(client, PRICING) == "Decision moment"
    assert triage(PRICING, "waiting", "your ruling on the five forks — owner by 2026-12-01") == 0
    capsys.readouterr()
    reconcile(client)
    assert column_of(client, PRICING) == "Executed"
    moved = next(h for h in history(client, PRICING) if h["kind"] == "moved")
    assert "the WATCH it replaced: Your ruling on the five forks." in moved["detail"]

    # ── #139 again, parked by the owner: the result lands, nothing moves ─
    read_the_rail_until(client, machine_floor, BERTH_FIRST)
    assert (
        triage(
            BERTH_FIRST,
            "now",
            "the plan's four rulings are written in it",
            "--source",
            SOURCE,
            "--direction",
            "no direction",
        )
        == 0
    )
    assert "you parked it yourself" in capsys.readouterr().out
    reconcile(client)
    assert column_of(client, BERTH_FIRST) == "Decision moment"
    assert "You parked it yourself" in face(client, BERTH_FIRST)
    said = next(h for h in history(client, BERTH_FIRST) if h["kind"] == "dial")
    assert "you parked the card yourself, so it stays until you move it" in said["detail"]

    # ── the Loop's count: one card came back after a reading moved it ──
    assert main(["decisions", "all", "--returned", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert main(["decisions", "proj"]) == 0
    listed = capsys.readouterr().out
    assert f"#{BERTH_FIRST:<4} parked  now" in listed
    assert "returned to the owner's column" in listed

    # ── his answer is what re-reads #147, and then `stale` may close it ─
    answer = client.post(f"/api/projects/proj/cards/{BANK}/answer", json={"text": "The new one."})
    assert answer.status_code == 200, answer.text
    assert "reads the card again" in answer.json()["said"]
    assert any(h["kind"] == "answered" for h in history(client, BANK))
    read_the_rail_until(client, machine_floor, BANK)
    assert triage(BANK, "stale", "you ruled: the new account; the terminal is wired to it") == 0
    assert "moved to Done" in capsys.readouterr().out
    reconcile(client)
    assert column_of(client, BANK) == "Done"
    assert detail(client, BANK)["summary"]["standing"]["state"] == "held"


def test_a_reading_session_cannot_close_the_card_it_reads(
    client: TestClient, machine_floor: Floor, capsys
):
    read_the_rail_until(client, machine_floor, BERTH_FIRST)
    assert BERTH_FIRST in open_readings(client)
    argv = [
        "close",
        "proj",
        str(BERTH_FIRST),
        "--delivered",
        "x",
        "--watch",
        "y — owner by 2026-12-01",
    ]
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert err.startswith(f"A reading is open on #{BERTH_FIRST}")
    assert "the board moves the card" in err
    assert column_of(client, BERTH_FIRST) == "Decision moment"
