"""Auto-fix stops at the line the owner drew and leaves the rest filed
(card #149), on the floor.

What is held here:
- item 1, the setting: a line per board on the row that keeps its switch,
  kept through a reopen, audited with the board, the actor and the line,
  a change of the number naming no board; `needle dial` prints each
  board's line beside its switch and refuses a word that is no rung by
  naming them;
- item 2, the beat — the class-closer: with four verified defects one per
  band and the line at harm outside, the beat plans the harm-outside card
  and no other across three more beats with room under the number;
  `needle fixes` names the fact for the three; the line moved to lies
  takes the lies card; a card below the line whose document is read again
  into a graver band is taken; a plan written above the line and the line
  then moved below it holds, counted as held, and starts by itself when
  the line moves back; `needle fixes all --below-the-line --count` is 0
  after all of it;
- item 3, the head and the face: the Defects head line counts the filed
  apart from the fixing, the three faces end with the line's sentence and
  the harm-outside face does not, the routing word stays "triaged now",
  and `needle defects` prints the same head line.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.cli import main
from domain.card import Actor
from domain.triage import Band
from infrastructure import clock
from infrastructure.schema import DialRow
from infrastructure.store import Store, StoreRefusal
from tests.api import test_doors as doors
from tests.api.test_defects_column import FOUR, column, four_verified
from tests.api.test_dial import (
    SOURCE,
    board,
    column_of,
    grade,
    land_plan,
    read_the_rail_until,
    second_board,
    tick,
    turn,
)
from tests.api.test_doors import detail, reconcile
from tests.api.test_the_triage_seat import edit
from tests.api.test_title import face_of
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

BELOW_HARM = "below this board's line at harm outside"
FILED_SENTENCE = (
    "Filed below this board's line at harm outside; taken the moment you move the line "
    "or a fresh reading grades it graver."
)


def draw(client: TestClient, line: str, slug: str = "proj") -> dict:
    """Move one board's line from its page: the same route as the switch."""
    response = client.post("/api/dial", json={"project": slug, "line": line})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_line_is_one_per_board_audited_like_the_switch(
    client: TestClient, store: Store, repo: Path, tmp_path: Path, capsys
):
    second_board(client, store, repo, tmp_path)
    # Every board is born taking every defect: the last rung, where
    # auto-fix reached before the line existed (ruling 3).
    assert board(client)["dial"]["dial"]["line"] == "nothing"
    assert board(client, "two")["dial"]["dial"]["line"] == "nothing"
    state = draw(client, "lies", slug="two")
    assert state["dial"]["line"] == "lies"
    assert board(client)["dial"]["dial"]["line"] == "nothing", "the other board's is its own"
    reopened = Store(store.path)
    try:
        assert reopened.dial("two").line is Band.LIES
        assert reopened.dial("proj").line is Band.NOTHING
    finally:
        reopened.close()
    # The audit row names the board, the actor and the line, and turns no
    # switch; a change of the number still names no board and no line; a
    # turn of the switch carries the line as it stands.
    turn(client, lanes=3)
    turn(client, on=True, slug="two")
    changes = [(c.project, c.on, c.lanes, c.line, c.actor) for c in store.dial_changes()]
    assert changes == [
        ("two", None, 1, Band.LIES, Actor.OWNER),
        (None, None, 3, None, Actor.OWNER),
        ("two", True, 3, Band.LIES, Actor.OWNER),
    ]
    # The same rung again writes nothing, and the last rung on a board with
    # no row writes nothing: off with every defect is how a board is born.
    rows = len(store.dial_changes())
    draw(client, "lies", slug="two")
    draw(client, "nothing")
    assert len(store.dial_changes()) == rows
    with Store(store.path)._session() as session:
        assert [r.project_slug for r in session.scalars(select(DialRow))] == [None, "two"]
    # A word that is no rung is refused at the route, and a line with no
    # board at the store.
    assert client.post("/api/dial", json={"project": "two", "line": "elsewhere"}).status_code == 422
    with pytest.raises(StoreRefusal, match="A line is one board's"):
        store.turn_dial(project=None, line=Band.LIES, actor=Actor.OWNER, at=clock.now())
    # The terminal: each board's line beside its switch, one phrase (ruling 4).
    assert main(["dial"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "proj: auto-fix off, takes every defect"
    assert out[1].startswith("two: auto-fix on, stops at lies; changed ")
    assert main(["dial", "two", "--line", "elsewhere"]) == 1
    err = capsys.readouterr().err
    assert "harm outside, lies, loses, costs, looks, or every defect" in err
    assert main(["dial", "--line", "lies"]) == 1
    assert "needle dial <slug> --line" in capsys.readouterr().err
    assert main(["dial", "proj", "--line", "Harm Outside"]) == 0
    assert capsys.readouterr().out.startswith("proj: auto-fix off, stops at harm outside; changed ")
    assert main(["dial", "two", "--line", "every defect"]) == 0
    capsys.readouterr()
    assert store.dial("two").line is Band.NOTHING and store.dial("proj").line is Band.HARM_OUTSIDE
    assert [(c.project, c.line) for c in store.dial_changes()][-2:] == [
        ("proj", Band.HARM_OUTSIDE),
        ("two", Band.NOTHING),
    ]
    assert store.dial_changes()[-1].actor is Actor.OWNER


def lanes_of(store: Store) -> list[tuple[int, str]]:
    return [(f.card_number, f.stage.value) for f in store.fix_lanes("proj")]


def test_the_beat_takes_only_a_verified_defect_at_or_above_its_boards_line(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """Items 2 and 3 — the class-closer: a beat that plans a defect below
    its board's line fails here."""
    numbers = four_verified(client, machine_floor, repo, capsys)
    # FOUR's order: a looks, a lies, a loses reaching money, a costs.
    looks, lies, harm, costs = numbers
    paths = {
        n: f"docs/slice-suggestions/{stem}.md"
        for n, (stem, _, _) in zip(numbers, FOUR, strict=True)
    }
    draw(client, "harm outside")
    turn(client, on=True, lanes=4)
    # Item 3, before the beat moves anything: the head splits the verified
    # by the line, the three faces end with the line's sentence, the
    # harm-outside face does not, and the routing word is untouched.
    defects = column(client, "Defects")
    parked = defects["count"] - 4  # the fixture's own, read as `his` on the way
    head = (
        f"{parked} yours · 0 nobody has read yet · 0 waiting on a signal · "
        "1 fixing themselves · 3 filed below the line"
    )
    assert defects["line"] == head
    for number in (looks, lies, costs):
        face = face_of(client, number)
        assert face["state"]["detail"].endswith(FILED_SENTENCE), face["state"]["detail"]
        assert face["routing"]["state"] == "triaged now"
        assert detail(client, number)["summary"]["state"]["detail"].endswith(FILED_SENTENCE)
    # The face's sentence is the Defects column's, and the board keeps a
    # graded defect there: a hand move out is refused by the document
    # (card #100, item 1), which is why the gate in the face is a tie to
    # the beat's own column rather than a fix for a reachable face. The
    # gate itself is held pure, in tests/board/test_the_line.py.
    refused = client.post(
        f"/api/projects/proj/cards/{looks}/move",
        json={"to": {"column": "Backlog", "group": None, "position": 0}},
    )
    assert refused.status_code == 409, refused.text
    assert "Kind: defect" in refused.text
    above = face_of(client, harm)["state"]["detail"]
    assert "below this board's line" not in above and above.endswith(
        "Create plan writes one when you want it planned."
    )
    assert main(["defects", "proj"]) == 0
    assert (
        capsys.readouterr().out.splitlines()[0] == f"proj: {defects['count']} in Defects — {head}"
    )
    # The switch is the operative reason when it is off: a board that runs
    # nothing says so, rather than naming a line whose moving would start
    # nothing. Same order as a held plan's note at Start.
    turn(client, on=False)
    off_rows = {
        w["card_number"]: w["why"] for w in client.get("/api/fixes?slug=proj").json()["waiting"]
    }
    assert off_rows[looks] == "this board's switch is off"
    assert off_rows[harm] == "this board's switch is off"
    turn(client, on=True)
    # Item 2: the harm-outside card is planned and no other, beat after
    # beat, with room for three more under the number.
    tick(client)
    assert lanes_of(store) == [(harm, "planning")]
    for _ in range(3):
        tick(client)
    assert lanes_of(store) == [(harm, "planning")]
    waiting = {
        w["card_number"]: w["why"] for w in client.get("/api/fixes?slug=proj").json()["waiting"]
    }
    assert waiting[looks] == waiting[lies] == waiting[costs] == BELOW_HARM
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("proj: auto-fix on, stops at harm outside, first on ")
    assert "its card was at or above its board's line" in out
    # The line moved to lies: the lies card is planned on the next beat.
    draw(client, "lies")
    tick(client)
    assert lanes_of(store) == [(harm, "planning"), (lies, "planning")]
    # A card below the line whose document is changed and read again into
    # a graver band is planned on the beat after the reading lands.
    edit(repo, paths[costs], "The fix.", "The fix, before the invoice goes out.")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert face_of(client, costs)["grade"] is None
    read_the_rail_until(client, machine_floor, costs)
    argv = ["triage", "proj", str(costs), "now", "the berth plan says every berth is billed once"]
    argv += ["--title", "passes", "--source", SOURCE, "--direction", "no direction"]
    assert main(argv + grade("money", "loses", "once-seen")) == 0
    reconcile(client)
    tick(client)
    assert lanes_of(store) == [(harm, "planning"), (lies, "planning"), (costs, "planning")]
    # A plan written above the line, and the line then moved below it,
    # holds at Start (ruling 5): no Start, counted as held, the reason on
    # the record — and it starts by itself when the line moves back.
    land_plan(repo, paths[lies], "2026-09-15-the-ledger-says-what-it-shows", FOUR[1][1])
    client.app.state.loops.live.rescan("proj")
    assert column_of(client, lies) == "Planned"
    draw(client, "harm outside")
    tick(client)
    # (A launch may still happen on this beat — the seat reads the new
    # plan's title — so the evidence is the card's place, never a count.)
    assert column_of(client, lies) == "Planned", "no Start while the card is below the line"
    lane = next(f for f in store.fix_lanes("proj") if f.card_number == lies)
    assert (lane.stage.value, lane.note) == ("planned", BELOW_HARM)
    assert board(client)["dial"]["held"] == 1
    assert any(h["detail"] == f"Start waits: {BELOW_HARM}" for h in detail(client, lies)["history"])
    capsys.readouterr()
    assert main(["fixes", "proj"]) == 0
    assert BELOW_HARM in capsys.readouterr().out
    draw(client, "lies")
    tick(client)
    assert column_of(client, lies) == "Executing"
    # No fix lane began below its board's line: the Loop's count.
    capsys.readouterr()
    assert main(["fixes", "all", "--below-the-line", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"
    assert main(["fixes", "all", "--below-the-line"]) == 0
    assert "no fix lane began below its board's line" in capsys.readouterr().out
    assert main(["fixes", "all", "--count"]) == 1
    assert "--below-the-line" in capsys.readouterr().err
    report = client.get("/api/fixes?slug=proj").json()
    assert [(lane["card_number"], lane["below_the_line"]) for lane in report["lanes"]] == [
        (harm, False),
        (lies, False),
        (costs, False),
    ]
    # With the line back at the last rung the head reads as it did before
    # the line existed: no "filed" count at all.
    draw(client, "nothing")
    assert column(client, "Defects")["line"].endswith("fixing themselves")
    # The Loop's counter fires. Everything above shows it reading 0 because
    # the beat never plans below the line, which leaves 0 indistinguishable
    # from a number that cannot move (the cold read of card #149, finding
    # 3). So: the line at harm outside, and a fix lane opened straight in
    # the store on a card below it — the second path to Start the Loop
    # exists to catch, since the beat itself will not do this.
    draw(client, "harm outside")
    looks_reading = store.triage("proj", looks)
    assert looks_reading is not None and looks_reading.grade is not None
    store.open_fix_lane("proj", looks, clock.now(), decision=looks_reading.decision)
    capsys.readouterr()
    assert main(["fixes", "all", "--below-the-line", "--count"]) == 0
    assert capsys.readouterr().out == "1\n", "the counter reads the lane the beat would not open"
    assert main(["fixes", "proj", "--below-the-line"]) == 0
    assert "its card was BELOW its board's line when planning began" in capsys.readouterr().out
    # A lane with no band was never checked and never says it was: the third
    # value, which every lane on the real store has (finding 1).
    store.open_fix_lane("proj", costs, clock.now(), decision=None)
    capsys.readouterr()
    assert main(["fixes", "all", "--below-the-line", "--count"]) == 0
    assert capsys.readouterr().out == "1\n", "a lane with no band is not one the Loop counts"
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert "no band to compare against its board's line" in out
    lanes = client.get("/api/fixes?slug=proj").json()["lanes"]
    assert [lane["below_the_line"] for lane in lanes][-2:] == [True, None]
