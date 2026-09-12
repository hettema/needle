"""Defects get their own column and the gravest are fixed first (card #100),
on the floor.

What is held here:

- item 1, the column: a suggestion saying defect is a card in Defects and
  one saying idea is in Backlog; changing a document's kind moves its card
  on the next read; a hand move against the document is refused with the
  file named; every project on the board shows the column;
- item 2, the grade: a defect's reading without a grade is refused and the
  card stays unread; a graded defect shows its word and its why on its
  face; a changed document is read again and the grade follows the new
  text; a document that describes no failure is graded as nothing;
- item 3, the order: with four verified defects the beat plans the loses
  reaching money first, then the lies, then the costs, then the looks; the
  page shows the column in that order with the unread last under their
  count and the head line's four counts right; `needle defects` prints the
  same order and the Loop's count;
- item 4, readings with auto-fix off: a beat opens a reading and never
  plans one, and the head reads the readings live against the number.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import (
    acts,
    board,
    column_of,
    grade,
    land_on_the_way,
    number_of,
    open_readings,
    read_the_rail_until,
    reading_for,
    tick,
    turn,
    verify,
    write_defect,
)
from tests.api.test_doors import detail, reconcile
from tests.api.test_the_triage_seat import edit, park_the_rail
from tests.api.test_title import face_of
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick


def column(client: TestClient, name: str, slug: str = "proj") -> dict:
    return next(c for c in board(client, slug)["columns"] if c["definition"]["column"] == name)


def numbers_in(column_view: dict) -> list[int]:
    return [c["number"] for g in column_view["groups"] for c in g["cards"]]


# ── item 1: the column ─────────────────────────────────────────────────


def test_a_defect_reads_in_defects_an_idea_in_backlog_and_the_document_moves_the_card(
    client: TestClient, repo: Path, capsys
):
    defects = column(client, "Defects")
    assert defects["definition"]["furled_on_laptop"] is True
    assert [c["definition"]["column"] for c in board(client)["columns"]][:2] == [
        "Defects",
        "Backlog",
    ]
    assert defects["count"] > 0 and all(
        c["kind"] == "defect" for g in defects["groups"] for c in g["cards"]
    )
    assert not any(
        c["kind"] == "defect" for g in column(client, "Backlog")["groups"] for c in g["cards"]
    )
    assert defects["line"] is not None and "nobody has read yet" in defects["line"]
    assert column(client, "Backlog")["line"] is None

    path = write_defect(
        repo, "2026-09-05-the-fuel-pump-counts-in-gallons", "The fuel pump counts in gallons", "x"
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The fuel pump counts in gallons")
    assert column_of(client, number) == "Defects"
    # The document's word moves the card on the next read, both ways.
    edit(repo, path, "**Kind:** defect", "**Kind:** idea")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert column_of(client, number) == "Backlog"
    edit(repo, path, "**Kind:** idea", "**Kind:** defect")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert column_of(client, number) == "Defects"
    # A hand move against the document is refused with the file named; a
    # move inside the column is refused because its order is the board's.
    against = client.post(
        f"/api/projects/proj/cards/{number}/move",
        json={"to": {"column": "Backlog", "group": None, "position": 0}},
    )
    assert against.status_code == 409, against.text
    assert "Kind: defect" in against.text and path in against.text
    inside = client.post(
        f"/api/projects/proj/cards/{number}/move",
        json={"to": {"column": "Defects", "group": None, "position": 0}},
    )
    assert inside.status_code == 409, inside.text
    assert "gravest first" in inside.text
    assert column_of(client, number) == "Defects"


# ── item 2: the grade ──────────────────────────────────────────────────


def test_a_defects_reading_without_a_grade_is_refused_and_a_graded_one_shows_its_word(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    path = write_defect(
        repo,
        "2026-09-05-the-slip-totals-the-wrong-column",
        "The slip totals the wrong column",
        "**Fix:** now — the tariff plan says the slip's total is the sum of its lines",
        "A skipper is billed for a berth he did not take, and pays it.",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The slip totals the wrong column")
    assert face_of(client, number)["state"]["word"] == "no plan yet"
    opened = read_the_rail_until(client, machine_floor, number)
    brief = opened["argv"][-1]
    assert "how bad is it?" in brief and "--reaches" in brief and "`lies`" in brief
    capsys.readouterr()
    without = [
        "triage",
        "proj",
        str(number),
        "his",
        "the record selects neither",
        "--title",
        "passes",
    ]
    assert main(without) == 1
    said = capsys.readouterr().err
    assert "grades it in the same command" in said and "--breaks nothing" in said
    assert detail(client, number)["summary"]["routing"]["state"] == "needs triage"
    assert detail(client, number)["summary"]["triaging"] is not None, "the reading is still open"
    # Half a grade does not hold either.
    half = without + ["--breaks", "lies", "the skipper pays a false total"]
    assert main(half) == 1
    assert "missing" in capsys.readouterr().err
    # The whole grade lands with the result, and the face carries the word and the why.
    whole = without + grade("client", "lies", "sometimes")
    assert main(whole) == 0
    said = capsys.readouterr().out
    assert "graded: it shows something false as true, reaching a client or the public" in said
    record = store.triages("proj", number)[-1]
    assert record.grade is not None and record.grade.breaks.value == "lies"
    assert record.grade.reach_words == "the document says it reaches client"
    row = next(r for r in detail(client, number)["record"] if r["kind"] == "TRIAGED")
    assert "graded: shows something false as true" in row["text"]
    face = face_of(client, number)
    assert face["state"]["word"] == "lies"
    assert face["state"]["detail"].startswith(
        "Nothing for you: a second reading graded it: it shows something false as true, "
        "reaching a client or the public, sometimes. The document says it lies; "
    )
    assert face["grade"]["breaks"] == "lies" and face["grade"]["often"] == "sometimes"
    assert detail(client, number)["summary"]["grade"]["reach"] == "client"
    # A changed document is read again: the grade is gone from the face
    # until a fresh reading grades the new text.
    edit(repo, path, "and pays it.", "and pays it twice.")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    face = face_of(client, number)
    assert face["grade"] is None and face["state"]["word"] == "no plan yet"
    assert face["routing"]["state"] == "stale"
    read_the_rail_until(client, machine_floor, number)
    capsys.readouterr()
    assert main(without + grade("money", "loses", "once-seen")) == 0
    assert face_of(client, number)["state"]["word"] == "loses"


def test_a_document_that_describes_no_failure_is_graded_as_nothing(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    write_defect(
        repo,
        "2026-09-05-the-quay-shows-the-weather",
        "The quay shows the weather",
        "**Fix:** his — whether the quay shows the forecast is his call on what the board is for",
        "It would be nice if the quay display showed tomorrow's weather.",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The quay shows the weather")
    read_the_rail_until(client, machine_floor, number)
    capsys.readouterr()
    argv = ["triage", "proj", str(number), "his", "the record selects nothing", "--title", "passes"]
    assert (
        main(argv + ["--breaks", "nothing", "it asks for a forecast and says nothing is wrong"])
        == 0
    )
    assert "graded: an idea in a defect's clothing" in capsys.readouterr().out
    record = store.triages("proj", number)[-1]
    assert record.grade is not None and record.grade.breaks.value == "nothing"
    assert record.grade.reach is None and record.grade.often is None
    face = face_of(client, number)
    assert face["state"]["word"] == "nothing"
    assert "it describes no failure" in face["state"]["detail"]
    # Nothing with a reach does not hold.
    assert main(argv + ["--breaks", "nothing", "x", "--reaches", "you", "y"]) == 1
    assert "names no reach" in capsys.readouterr().err


# ── item 3: the order ──────────────────────────────────────────────────

FOUR = [
    (
        "2026-09-05-the-quay-font-is-crooked",
        "The quay font is crooked",
        ("client", "looks", "every-time"),
    ),
    (
        "2026-09-05-the-night-log-reports-a-check-it-skipped",
        "The night log reports a check it skipped",
        ("session", "lies", "every-time"),
    ),
    (
        "2026-09-05-a-paid-berth-is-let-again-for-free",
        "A paid berth is let again for free",
        ("money", "loses", "once-seen"),
    ),
    (
        "2026-09-05-the-morning-list-is-printed-by-hand",
        "The morning list is printed by hand",
        ("you", "costs", "sometimes"),
    ),
]
"""The plan's four (item 3, done means): a looks reaching a client, a lies
reaching a session every time, a loses reaching money once seen, a costs
reaching you — written in this order, so age alone would take the looks
first."""

GRAVEST_FIRST = [2, 1, 3, 0]
"""The loses reaching money (harm outside), then the lies, then the costs,
then the looks."""


def four_verified(client: TestClient, machine_floor: Floor, repo: Path, capsys) -> list[int]:
    """The plan's four, verified and graded with auto-fix off (item 4: the
    readings run either way, and with it on the first verified `now` would
    be planned before the next could be read under a number of one)."""
    turn(client, lanes=1)
    assert board(client)["dial"]["dial"]["on"] is False
    park_the_rail(client, machine_floor)
    numbers: list[int] = []
    for stem, title, _ in FOUR:
        write_defect(
            repo,
            stem,
            title,
            "**Fix:** now — the berth plan says every berth is let once and billed",
        )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    numbers = [number_of(client, title) for _stem, title, _grade in FOUR]
    # The readings walk the column oldest first, and the four were born in
    # one read: each is verified in its turn, so none is read on the way to
    # another and landed `his` there.
    for number, (_stem, _title, (reaches, breaks, often)) in sorted(
        zip(numbers, FOUR, strict=True), key=lambda pair: pair[0]
    ):
        verify(client, machine_floor, number, graded=grade(reaches, breaks, often))
    capsys.readouterr()
    return numbers


def test_the_column_the_beat_and_the_verb_read_one_order_gravest_first(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    numbers = four_verified(client, machine_floor, repo, capsys)
    expected = [numbers[i] for i in GRAVEST_FIRST]
    # The page: the graded four first in the board's order, then the unread
    # under their count; the head line's four counts from the routing.
    defects = column(client, "Defects")
    shown = numbers_in(defects)
    # The fixture's own defects, read `his` on the way with the mildest grade
    # (a cost to a session), sort among the four by the same scale — above
    # the looks, below the costs reaching you — so the four are read in
    # their relative order.
    assert [n for n in shown if n in numbers] == expected
    assert shown[:3] == expected[:3]
    groups = defects["groups"]
    assert (
        groups[0]["name"] is None and [c["number"] for c in groups[0]["cards"]][:3] == expected[:3]
    )
    unread = [c for c in groups[0]["cards"] if c["grade"] is None]
    assert unread == [], "every graded card is above the line"
    if len(groups) > 1:
        assert groups[1]["machine"] is True and groups[1]["name"].endswith("nobody has read yet")
        assert all(c["grade"] is None for c in groups[1]["cards"])
    parked = defects["count"] - 4  # the fixture's own, read as `his` on the way
    assert defects["line"] == (
        f"{parked} yours · 0 nobody has read yet · 0 waiting on a signal · 4 fixing themselves"
    )
    # The verb prints the same order and the Loop's count.
    assert main(["defects", "proj"]) == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip().startswith("#")]
    printed = [int(line.split()[0][1:]) for line in lines]
    assert printed == shown, "the verb prints the page's order"
    assert "harm outside; loses work, data or money" in lines[0] and "triaged now" in lines[0]
    assert "lies; shows something false as true, reaching a session, every time" in lines[1]
    assert main(["defects", "all", "--lies", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert main(["defects", "all", "--lies", "--on", "--unplanned-over", "7d", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "0", "graded today, not seven days ago"
    assert main(["defects", "all", "--unplanned-over", "weekly"]) == 1
    # The beat: the loses reaching money is planned first, then the lies,
    # then the costs, then the looks — one a beat, with room for four.
    waiting = [w["card_number"] for w in client.get("/api/fixes?slug=proj").json()["waiting"]]
    assert waiting == shown, "`needle fixes` waits in the page's order too"
    turn(client, on=True, lanes=4)
    taken: list[int] = []
    for _ in range(4):
        tick(client)
        launch = machine_floor.state()["launch_log"][-1]
        named = launch["argv"][launch["argv"].index("-n") + 1]
        assert named.startswith("planning-card-"), named
        taken.append(int(named.split("-")[2]))
    assert taken == expected


# ── item 4: readings with auto-fix off ─────────────────────────────────


def test_readings_run_with_auto_fix_off_and_nothing_is_planned(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    assert board(client)["dial"]["dial"]["on"] is False
    write_defect(
        repo,
        "2026-09-05-the-gate-log-drops-the-last-boat",
        "The gate log drops the last boat",
        "**Fix:** now — the gate plan says every boat through the gate is logged",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The gate log drops the last boat")
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == before + 1, "a reading opened, switch off"
    assert acts(machine_floor) == 0, "nothing planned while every switch is off"
    head = board(client)["dial"]
    assert head["triaging"] == 1 and head["running"] == 1, "the head reads the reading live"
    assert head["dial"]["on"] is False
    # Under the number: one reading at a time while the number is one.
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == before + 1
    # The readings walk the column oldest first; our defect is read in its
    # turn, verified `now`, and still nothing is planned while the switch is off.
    verify(client, machine_floor, number)
    assert detail(client, number)["summary"]["routing"]["state"] == "triaged now"
    for _ in range(3):
        tick(client)
        on = reading_for(machine_floor)
        if on is not None and on in open_readings(client):
            land_on_the_way(client, on)
    assert acts(machine_floor) == 0
    assert store.fix_lanes("proj") == []
    assert column_of(client, number) == "Defects"
    # The switch on: the verified defect is planned on the next beat.
    turn(client, on=True, lanes=1)
    for _ in range(3):
        tick(client)
        if acts(machine_floor):
            break
        on = reading_for(machine_floor)
        if on is not None and on in open_readings(client):
            land_on_the_way(client, on)
    assert acts(machine_floor) == 1
    assert [f.card_number for f in store.fix_lanes("proj")] == [number]


def test_a_defect_verified_before_the_scale_is_read_again_before_it_is_taken(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """A `now` reading from before card #100 carries no grade, and the
    column has no order for it: the beat opens a reading on it instead of
    planning it, and `needle fixes` says so."""
    from domain.card import Actor
    from domain.triage import Direction, TriageResult
    from infrastructure import clock

    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    write_defect(
        repo,
        "2026-09-05-the-harbour-map-is-a-year-old",
        "The harbour map is a year old",
        "**Fix:** now — the map plan says the printed map is this season's",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    write_defect(
        repo,
        "2026-09-05-the-fuel-log-names-no-boat",
        "The fuel log names no boat",
        "**Fix:** now — the fuel plan says every fill names the boat",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The harbour map is a year old")
    other = number_of(client, "The fuel log names no boat")
    document = detail(client, number)["document"]
    store.record_triage(
        "proj",
        number,
        at=clock.now(),
        actor=Actor.SESSION,
        result=TriageResult.NOW,
        words="the map plan says so",
        decision="0ld0ld0ld0ld0ld0",
        parent=None,
        direction=Direction.NONE,
        source_ref=None,
        source_path=None,
        source_fingerprint=None,
        document_fingerprint=document["fingerprint"],
        session_id=None,
    )
    # A cannot-tell from before the scale is read again too: the grade is
    # from the document alone, whatever the mark's evidence (review finding 5).
    store.record_triage(
        "proj",
        other,
        at=clock.now(),
        actor=Actor.SESSION,
        result=TriageResult.CANNOT_TELL,
        words="the fuel plan is not in the corpus",
        decision="0ld0ld0ld0ld0ld1",
        parent=None,
        direction=None,
        source_ref=None,
        source_path=None,
        source_fingerprint=None,
        document_fingerprint=detail(client, other)["document"]["fingerprint"],
        session_id=None,
    )
    client.app.state.loops.live.bump()
    reconcile(client)
    assert detail(client, number)["summary"]["routing"]["state"] == "triaged now"
    assert detail(client, number)["summary"]["grade"] is None
    waiting = {
        w["card_number"]: w["why"] for w in client.get("/api/fixes?slug=proj").json()["waiting"]
    }
    assert waiting[number] == "verified before the board graded defects; a reading grades it first"
    before = acts(machine_floor)
    tick(client)
    assert acts(machine_floor) == before, "not planned: read again first"
    assert open_readings(client).keys() == {number}, "the beat opened the reading that grades it"
    # Under a number of two the next beat opens the other card's reading,
    # never the same card's again (review finding 1: the beat asks whether a
    # reading is already open before it opens one).
    turn(client, lanes=2)
    launched = len(machine_floor.state()["launch_log"])
    tick(client)
    assert open_readings(client).keys() == {number, other}
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == launched + 1, "one reading per card"
    assert open_readings(client).keys() == {number, other}


def test_the_loops_clock_is_the_first_grade_not_the_latest_reading(
    client: TestClient, repo: Path, store: Store, capsys
):
    """`needle defects --unplanned-over 7d` counts from the first reading
    that graded the card: a re-reading of a touched document never restarts
    the seven days (review finding 9)."""
    from datetime import timedelta

    from domain.card import Actor
    from domain.triage import Breaks, Direction, Grade, Often, Reach, TriageResult
    from infrastructure import clock

    write_defect(
        repo,
        "2026-09-05-the-office-clock-lies-about-noon",
        "The office clock lies about noon",
        "**Fix:** now — the clock plan says the office clock is the harbour's",
    )
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, "The office clock lies about noon")
    fingerprint = detail(client, number)["document"]["fingerprint"]
    lies = Grade(
        breaks=Breaks.LIES,
        breaks_words="noon is shown an hour off",
        reach=Reach.CLIENT,
        reach_words="every skipper reads it",
        often=Often.EVERY_TIME,
        often_words="all day",
    )
    for days_ago, decision in ((8, "f1rstf1rstf1rst0"), (0, "l4testl4testl4t0")):
        store.record_triage(
            "proj",
            number,
            at=clock.now() - timedelta(days=days_ago),
            actor=Actor.SESSION,
            result=TriageResult.NOW,
            words="the clock plan says so",
            decision=decision,
            parent=None,
            direction=Direction.NONE,
            source_ref=None,
            source_path=None,
            source_fingerprint=None,
            document_fingerprint=fingerprint,
            session_id=None,
            grade=lies,
        )
        client.app.state.loops.live.bump()
    # The board is off: --on keeps nothing; without it the card counts from
    # its first grade, eight days ago, though its latest reading is today.
    capsys.readouterr()
    assert main(["defects", "proj", "--lies", "--unplanned-over", "7d", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert main(["defects", "proj", "--lies", "--on", "--unplanned-over", "7d", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "0"
