"""Defects fix themselves (plan 11), on the floor: a code lane cannot close
without a review record (item 1); the dial is on the head, persists and is
audited (item 3); with it on, the oldest `Fix: now` defect is planned by a
windowless session and, once its plan lands, started by the machine with
*started by the dial* on the card, one at a time under the number (items
4 and 6); `his` and unmarked defects are never started and a planning
session's question leaves the card to the owner (item 4); a `Fix: when`
trigger is read by the signal loop and delivered makes the defect eligible
(item 5); `needle fixes` counts the loop (item 6)."""

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.cli import main
from domain.card import Actor, CardOrigin
from domain.project import Project
from domain.signal import SessionWork
from infrastructure import clock
from infrastructure.live import sweep
from infrastructure.store import Store, StoreRefusal
from tests.api import test_doors as doors
from tests.api.attention import claim_count
from tests.api.test_doors import CARD, archive_plan, column_of, detail, git, read_signals, reconcile
from tests.conftest import NOW
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

TIDE = "The tide clock drifts a minute a day"
TIDE_PATH = "docs/slice-suggestions/2026-09-04-the-tide-clock-drifts-a-minute-a-day.md"


def board(client: TestClient, slug: str = "proj") -> dict:
    return client.get(f"/api/projects/{slug}/board").json()


def number_of(client: TestClient, title: str) -> int:
    for column in board(client)["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["title"] == title:
                    return card["number"]
    raise AssertionError(f"no card titled {title!r}")


def tick(client: TestClient) -> None:
    client.portal.call(client.app.state.dial.tick)


def turn(
    client: TestClient, *, on: bool | None = None, lanes: int | None = None, slug: str = "proj"
) -> dict:
    """Turn one board's switch, the machine's number, or both, from that
    board's page (card #80); answers that board's head."""
    response = client.post("/api/dial", json={"project": slug, "on": on, "lanes": lanes})
    assert response.status_code == 200, response.text
    return response.json()


SOURCE = "docs/plans/2026-08-28-a-berth-is-never-let-twice.md"
"""A real document in the fixture project: what a reading resolves and
fingerprints. Prose shaped like a path cannot produce `now` (plan 59)."""

GRADE = [
    "--reaches",
    "session",
    "the office's own log is what it touches",
    "--breaks",
    "costs",
    "a step done by hand until it is fixed",
    "--often",
    "sometimes",
    "it bites on the nights the log is read",
]
"""A grade every defect's reading lands with its result (card #100, item 2):
the door refuses one without it. The mildest shape, so a test about one
graver defect can put its own above these."""


def grade(reaches: str, breaks: str, often: str) -> list[str]:
    """A grade in three tokens, with words for each, for a test that orders."""
    return [
        "--reaches",
        reaches,
        f"the document says it reaches {reaches}",
        "--breaks",
        breaks,
        f"the document says it {breaks}",
        "--often",
        often,
        f"the document says {often}",
    ]


def acts(machine_floor: Floor) -> int:
    """How many launches were a planning session or a Start — everything
    but a reading. A reading opens whether or not any board is on (card
    #100, item 4), so a test about what the switch holds counts the acts."""
    return sum(
        1
        for launch in machine_floor.state()["launch_log"]
        if not launch["argv"][launch["argv"].index("-n") + 1].startswith("triage-card-")
    )


def reading_for(machine_floor: Floor) -> int | None:
    """The card the last launch opened a reading of, when it opened one."""
    log = machine_floor.state()["launch_log"]
    if not log:
        return None
    named = log[-1]["argv"][log[-1]["argv"].index("-n") + 1]
    return int(named.split("-")[2]) if named.startswith("triage-card-") else None


def open_readings(client: TestClient, slug: str = "proj") -> dict[int, dict]:
    """The reading in flight on each card, from the board itself."""
    found: dict[int, dict] = {}
    for column in client.get(f"/api/projects/{slug}/board").json()["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["triaging"] is not None:
                    found[card["number"]] = card["triaging"]
    return found


def is_defect(client: TestClient, number: int, slug: str = "proj") -> bool:
    card = client.get(f"/api/projects/{slug}/cards/{number}").json()
    return card["summary"]["kind"] == "defect"


def land_on_the_way(client: TestClient, number: int, slug: str = "proj") -> None:
    """Land the result a reading on the way needs: `his` with a passing
    title on a defect, a passing title alone on a plan or an idea (card
    #74, item 3: every live title is read cold by the same seat)."""
    argv = ["triage", slug, str(number)]
    if is_defect(client, number, slug):
        argv += ["his", "the record does not select between the two shapes this could take"]
        argv += GRADE
    assert main(argv + ["--title", "passes"]) == 0


READINGS_ON_THE_WAY = 80
"""Every live plan and idea on the fixture is read cold too, so the way
to one card is longer than the column (card #74, item 3): a walk across
two copies of the fixture is a tick and a landing per document."""


def read_the_rail_until(
    client: TestClient, machine_floor: Floor, number: int, slug: str = "proj"
) -> dict:
    """The launch of the reading of this card, ticking until the beat opens
    it and landing `his` on every other defect it reads on the way — and a
    passing title on every plan and idea (card #74).

    Every defect on the rail is now read, not only the marked ones — an
    unmarked defect is nobody's until something has looked at it (plan 59,
    item 1) — the rail is read oldest first, and a reading counts against the
    dial's number while it runs. So a test about one card has to clear the
    older ones, exactly as a night on the real board would."""
    for _ in range(READINGS_ON_THE_WAY):
        # Readings open on every project's board, one at a time; a reading
        # on another board is landed too, so the beat reaches this card.
        for other in client.get("/api/projects").json():
            elsewhere = open_readings(client, other["slug"])
            if other["slug"] != slug and elsewhere:
                land_on_the_way(client, next(iter(elsewhere)), other["slug"])
        reading = open_readings(client, slug)
        if number in reading:
            return next(
                launch
                for launch in reversed(machine_floor.state()["launch_log"])
                if launch["session_id"] == reading[number]["session_id"]
            )
        if reading:
            land_on_the_way(client, next(iter(reading)), slug)
            continue
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        if len(machine_floor.state()["launch_log"]) == before:
            # The dial's own timer beats every DIAL_SECONDS under the test
            # client too, and a long walk crosses it: a reading it opened
            # between two steps here is landed on the next step, not a
            # reason to stop.
            if any(
                client.app.state.loops.live.store.windowless_sessions(
                    s, work=SessionWork.TRIAGE, open_only=True
                )
                for s in client.app.state.loops.live.projects
            ):
                continue
            fixes = client.get("/api/fixes").json()
            head = client.get(f"/api/projects/{slug}/board").json()["dial"]
            raise AssertionError(
                f"the beat opened nothing before reaching #{number}: "
                + str([(w["card_number"], w["why"]) for w in fixes["waiting"]])
                + f"; the head says {head}; lanes {fixes['lanes']}"
            )
    raise AssertionError(f"the rail never reached #{number}")


def verify(
    client: TestClient,
    machine_floor: Floor,
    number: int,
    *,
    result: str = "now",
    words: str = "the ledger's own rule selects this outcome",
    source: str | None = SOURCE,
    direction: str | None = "no direction",
    graded: list[str] | None = None,
) -> dict:
    """The reading the dial opens before it plans anything (plan 59, item 3),
    and its result through the one verb. A `now` mark alone no longer moves
    the dial: the beat opens the seat, the reading lands, and only then is
    the defect the machine's."""
    opened = read_the_rail_until(client, machine_floor, number)
    argv = ["triage", "proj", str(number), result, words, "--title", "passes"]
    argv += graded if graded is not None else GRADE
    if source:
        argv += ["--source", source]
    if direction:
        argv += ["--direction", direction]
    assert main(argv) == 0
    # The verb ran in its own process against the shared store; the server's
    # own loop would re-read on its next beat, and here we ask it to now, so
    # the doors a test reads are the doors this result implies.
    reconcile(client)
    return opened


def write_defect(repo: Path, stem: str, title: str, head: str, body: str = "x") -> str:
    path = repo / "docs" / "slice-suggestions" / f"{stem}.md"
    path.write_text(
        f"# {title}\n\n**Kind:** defect\n{head}\n**Found by:** the owner, 2026-09-05.\n\n"
        f"## Observation\n\n{body}\n\n## What would hold it\n\nThe fix.\n",
        encoding="utf-8",
    )
    return f"docs/slice-suggestions/{stem}.md"


def land_plan(
    repo: Path,
    suggestion_path: str,
    stem: str,
    title: str,
    *,
    terrain: str = "",
    sequencing: str | None = None,
) -> str:
    """What the planning session does: the plan carrying the suggestion,
    committed in the project's checkout, the suggestion moved to done/."""
    plan = repo / "docs" / "plans" / f"{stem}.md"
    plan.write_text(
        f"# {title}\n\n**Status:** PENDING\n**Written:** 2026-09-05, by the dial's planning "
        f"session\n**Effort gate:** medium — one edit and a check\n**Carries:** {suggestion_path}\n"
        + (f"**Sequencing:** {sequencing}\n" if sequencing else "")
        + "**Class:** a boot check refuses a clock that disagrees with the office\n\n"
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
        "dial": {
            "project": "proj",
            "on": False,
            "lanes": 1,
            "changed_at": None,
            "first_on_at": None,
        },
        "others_on": [],
        "running": 0,
        "triaging": 0,
        "held": 0,
        "full": None,
        "quiet": True,
    }
    turned = turn(client, on=True, lanes=2)
    assert turned["dial"]["on"] is True and turned["dial"]["lanes"] == 2
    assert turned["dial"]["changed_at"] is not None
    assert turned["dial"]["first_on_at"] == turned["dial"]["changed_at"]
    assert board(client)["dial"]["dial"]["lanes"] == 2
    # Two rows for one act: the number's, naming no board, and the switch's,
    # naming the board it turned (card #80, item 1).
    changes = store.dial_changes()
    assert [(c.actor.value, c.project, c.on, c.lanes) for c in changes] == [
        ("owner", None, None, 2),
        ("owner", "proj", True, 2),
    ]
    # A turn that changes nothing writes nothing; a restart keeps the setting.
    turn(client, on=True, lanes=2)
    assert len(store.dial_changes()) == 2
    reopened = Store(store.path)
    try:
        assert reopened.dial("proj").on is True and reopened.dial("proj").lanes == 2
        assert reopened.defects_at_on(), "the defects were recorded at the first turn to on"
    finally:
        reopened.close()
    off = turn(client, on=False)
    assert off["dial"]["on"] is False and off["dial"]["first_on_at"] is not None
    assert off["dial"]["lanes"] == 2, "the number is the machine's and a switch leaves it"
    assert [(c.project, c.on, c.lanes) for c in store.dial_changes()] == [
        (None, None, 2),
        ("proj", True, 2),
        ("proj", False, 2),
    ]


def second_board(client: TestClient, store: Store, repo: Path, tmp_path: Path) -> Path:
    """A second project on the board, a bare copy of the fixture one."""
    second = tmp_path / "second"
    shutil.copytree(repo, second, ignore=shutil.ignore_patterns(".git"))
    git(second, "init", "-q", "-b", "develop")
    git(second, "add", ".")
    git(second, "commit", "-q", "-m", "founding")
    project = Project(slug="two", name="Second", path=str(second), registered_at=NOW)
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    client.app.state.loops.live.load()
    reconcile(client)
    return second


def test_the_switch_is_one_per_board_and_the_number_is_the_machines(
    client: TestClient, store: Store, repo: Path, tmp_path: Path, capsys
):
    """Card #80, item 1: turning one board on leaves the other off through
    a restart; the number read through either board is the same and one
    turn changes it for both; each head names the other boards that are
    on; a board the store does not know is refused by name."""
    second_board(client, store, repo, tmp_path)
    turn(client, on=True, slug="two")
    assert board(client, "two")["dial"]["dial"]["on"] is True
    assert board(client)["dial"]["dial"]["on"] is False
    assert board(client)["dial"]["others_on"] == ["two"]
    assert board(client, "two")["dial"]["others_on"] == []
    reopened = Store(store.path)
    try:
        assert reopened.dial("two").on is True and reopened.dial("proj").on is False
        assert [r.project for r in reopened.defects_at_on()] == ["two"], (
            "the rail baseline is the board's, recorded at its own first on"
        )
    finally:
        reopened.close()
    # The number: one for the machine, read the same through either board.
    turn(client, lanes=3)
    assert board(client)["dial"]["dial"]["lanes"] == 3
    assert board(client, "two")["dial"]["dial"]["lanes"] == 3
    turn(client, lanes=2, slug="two")
    assert board(client)["dial"]["dial"]["lanes"] == 2
    assert [(c.project, c.on, c.lanes) for c in store.dial_changes()] == [
        ("two", True, 1),
        (None, None, 3),
        (None, None, 2),
    ]
    # Both on: each head names the other.
    turn(client, on=True)
    assert board(client)["dial"]["others_on"] == ["two"]
    assert board(client, "two")["dial"]["others_on"] == ["proj"]
    assert [r.project for r in store.defects_at_on()] == ["two", "proj"]
    # A board the store does not know, and a switch with no board, are refused.
    refused = client.post("/api/dial", json={"project": "nowhere", "on": True})
    assert refused.status_code == 409 and 'No project "nowhere"' in refused.json()["detail"]
    with pytest.raises(StoreRefusal, match="name the board"):
        store.turn_dial(project=None, on=True, actor=Actor.OWNER, at=clock.now())
    # The terminal does the same, audited as the owner's, and prints a line
    # per board (item 3).
    assert main(["dial", "two", "off"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("two: auto-fix off; changed ")
    assert main(["dial"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("proj: auto-fix on; changed ")
    assert out[1].startswith("two: auto-fix off; changed ")
    assert out[2].startswith("2 fix lanes at most across every board; 0 live now")
    assert store.dial_changes()[-1].actor is Actor.OWNER
    assert main(["dial", "on"]) == 1
    assert "needle dial <slug> on" in capsys.readouterr().err
    # Turning off a board that has never been turned writes nothing at all
    # (review finding 3): off is how a board is born.
    rows = len(store.dial_changes())
    assert main(["dial", "two", "off"]) == 0
    capsys.readouterr()
    assert len(store.dial_changes()) == rows
    with Store(store.path)._session() as session:
        from infrastructure.schema import DialRow

        assert [r.project_slug for r in session.scalars(select(DialRow))] == [None, "two", "proj"]


def test_needle_dial_reads_the_number_on_a_board_with_no_project(
    tmp_path: Path, monkeypatch, capsys
):
    """Review finding 2: a fresh board has no page to read the head through,
    and `needle dial` still prints the machine's number."""
    empty = Store(tmp_path / "empty.db")
    try:
        assert empty.dials() == [] and empty.fix_lanes_at_most() == 1
        assert empty.dial("nowhere").on is False
    finally:
        empty.close()
    monkeypatch.setenv("NEEDLE_DB", str(tmp_path / "empty.db"))
    assert main(["dial", "--lanes", "3"]) == 0
    assert capsys.readouterr().out == "no project is on the board; 3 fix lanes at most\n"


def read_every_rail(client: TestClient, machine_floor: Floor, verified: dict[str, int]) -> None:
    """Read every board's rail through the beat, landing `now` on the one
    card named per board and `his` with a passing title elsewhere, until
    nothing is open and the beat opens nothing."""
    for _ in range(2 * READINGS_ON_THE_WAY):
        opened = False
        for other in client.get("/api/projects").json():
            slug = other["slug"]
            for number in list(open_readings(client, slug)):
                opened = True
                if number == verified.get(slug):
                    argv = ["triage", slug, str(number), "now", "the rule selects this outcome"]
                    argv += ["--title", "passes", "--source", SOURCE, "--direction", "no direction"]
                    argv += GRADE
                    assert main(argv) == 0
                else:
                    land_on_the_way(client, number, slug)
        if opened:
            reconcile(client)
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        if len(machine_floor.state()["launch_log"]) == before and not opened:
            return
    raise AssertionError("the rails were never read through")


def test_the_beat_plans_a_defect_only_on_a_board_whose_switch_is_on(
    client: TestClient, machine_floor: Floor, store: Store, repo: Path, tmp_path: Path, capsys
):
    """Card #80, item 2 — the class-closer: with A on and B off and B
    holding the oldest verified `now` defect, the beat plans A's defect and
    nothing on B, while a reading opens on B's unread defects as before
    (ruling 3); with both off nothing is planned; with both on, the next
    verified defect is planned wherever it is. A fix lane whose planning
    began on a board whose switch was off is the class made loud, and
    `needle fixes all --started-off --count` counts exactly that."""
    second_board(client, store, repo, tmp_path)
    tide = number_of(client, TIDE)
    tide_two = next(
        card["number"]
        for column in board(client, "two")["columns"]
        for group in column["groups"]
        for card in group["cards"]
        if card["title"] == TIDE
    )
    turn(client, on=True, slug="two", lanes=2)
    # Only "two" is on. Readings run on both boards regardless — B's rail is
    # read through, its tide verified `now` — and the one planning session
    # the beat opens is on A.
    read_every_rail(client, machine_floor, {"proj": tide, "two": tide_two})
    assert [(f.project, f.card_number, f.stage.value) for f in store.fix_lanes()] == [
        ("two", tide_two, "planning")
    ]
    # B's tide was verified `now` through a reading the beat opened on B
    # while B was off: the seat is never gated by the switch.
    assert store.latest_triages("proj")[tide].result.value == "now"
    waiting = {
        w["card_number"]: w["why"] for w in client.get("/api/fixes?slug=proj").json()["waiting"]
    }
    assert waiting[tide] == "this board's switch is off"
    # Room under the number, B's verified defect the oldest thing on any rail:
    # still nothing on B, beat after beat.
    for _ in range(3):
        tick(client)
    assert [f.project for f in store.fix_lanes()] == ["two"]
    # Both off: nothing is planned, however eligible the column — though a
    # reading may still open, since a reading enters nothing (card #100).
    turn(client, on=False, slug="two")
    taken = acts(machine_floor)
    tick(client)
    assert acts(machine_floor) == taken
    assert [f.project for f in store.fix_lanes()] == ["two"]
    # B on: its verified defect is planned on the next beat.
    turn(client, on=True, slug="proj")
    tick(client)
    assert [(f.project, f.card_number) for f in store.fix_lanes()] == [
        ("two", tide_two),
        ("proj", tide),
    ]
    # Every lane began on a board that was on at that moment: the Loop's count.
    capsys.readouterr()
    assert main(["fixes", "all", "--started-off", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"
    report = client.get("/api/fixes").json()
    assert [(lane["project"], lane["switch_was_on"]) for lane in report["lanes"]] == [
        ("two", True),
        ("proj", True),
    ]
    # The switch is read at the Start as at the planning (review finding 1):
    # B's plan lands, B is turned off, and the beat holds the planned card —
    # no Start, counted as held, the reason on the record — until B is on.
    land_plan(
        repo,
        TIDE_PATH,
        "2026-09-05-the-quay-clock-is-the-offices",
        "The quay clock is the office's",
    )
    client.app.state.loops.live.rescan("proj")
    assert column_of(client, tide) == "Planned"
    turn(client, on=False, slug="proj")
    taken = acts(machine_floor)
    tick(client)
    assert acts(machine_floor) == taken, "no Start while the board is off"
    assert column_of(client, tide) == "Planned"
    lane = next(f for f in store.fix_lanes("proj") if f.card_number == tide)
    assert (lane.stage.value, lane.note) == ("planned", "this board's switch is off")
    assert board(client)["dial"]["held"] == 1
    assert any(
        h["detail"] == "Start waits: this board's switch is off"
        for h in detail(client, tide)["history"]
    )
    turn(client, on=True, slug="proj")
    tick(client)
    assert acts(machine_floor) == taken + 1
    assert column_of(client, tide) == "Executing"
    capsys.readouterr()
    assert main(["fixes", "all", "--started-off", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"
    # `--count` alone is refused rather than ignored (review finding 6).
    assert main(["fixes", "all", "--count"]) == 1
    assert "--started-off" in capsys.readouterr().err


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

    # Off: nothing starts by itself, however eligible the column is (acceptance
    # 5) — a reading may open, since a reading enters nothing (card #100, item 4).
    tick(client)
    assert acts(machine_floor) == 0
    assert main(["fixes", "all"]) == 0
    assert "no fix lane yet" in capsys.readouterr().out

    turn(client, on=True, lanes=1)
    # A mark alone no longer opens the dial: the beat reads the rail first,
    # oldest first, and a reading counts against the number while it runs.
    reading = read_the_rail_until(client, machine_floor, tide)
    capsys.readouterr()
    assert board(client)["dial"]["triaging"] == 1
    assert board(client)["dial"]["running"] == 1, "a live session against the number"
    read_so_far = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == read_so_far, "full while it reads"
    assert detail(client, tide)["summary"]["triaging"]["session_id"] == reading["session_id"]
    brief = reading["argv"][-1]
    assert brief.startswith(f"A reading of #{tide}'s mark on Harbourmaster")
    assert "never EnterWorktree" in brief and "does the source select this outcome?" in brief
    assert "A decision is Dennis's only when the written record" in brief
    assert TIDE_PATH in brief and "--- the document" in brief
    assert (
        main(
            [
                "triage",
                "proj",
                str(tide),
                "now",
                "the tide table plan names the harbour clock as the reference",
                "--source",
                SOURCE,
                "--direction",
                "no direction",
                "--title",
                "passes",
                *GRADE,
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert detail(client, tide)["summary"]["routing"]["state"] == "triaged now"
    tick(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == read_so_far + 1, "one defect per beat, and the number is one"
    planning = log[-1]
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
        f"The dial took it: planning session {planning['short']}, alpha"
    )
    assert opened["history"][0]["actor"] == "machine"
    state = board(client)
    assert claim_count(state, "planning") == 1
    assert state["dial"]["running"] == 1
    assert detail(client, gate_log)["summary"]["planning"] is None

    # The number is full: another beat plans nothing more.
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == read_so_far + 1

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
    assert len(log) == read_so_far + 2, (
        "the plan landed, so the dial started the lane",
        store.fix_lanes("proj"),
    )
    started = log[-1]
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
    # The fix lane carries the decision the reading minted (plan 59, item 6).
    assert store.fix_lanes("proj")[0].decision == store.triages("proj", tide)[0].decision
    # The second defect still waits: the fix lane counts until it folds.
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == read_so_far + 2

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
    verify(client, machine_floor, gate_log)
    capsys.readouterr()
    tick(client)
    next_planning = machine_floor.state()["launch_log"][-1]
    assert next_planning["argv"][next_planning["argv"].index("-n") + 1].startswith(
        f"planning-card-{gate_log}-"
    )
    assert [(f.card_number, f.stage.value) for f in store.fix_lanes("proj")] == [
        (tide, "folded"),
        (gate_log, "planning"),
    ]

    # The loop, counted (item 6).
    report = client.get("/api/fixes").json()
    assert [(s["project"], s["on"]) for s in report["switches"]] == [("proj", True)]
    first = report["lanes"][0]
    assert first["card_number"] == tide and first["stage"] == "folded"
    assert first["switch_was_on"] is True, "planned while its board was on (card #80)"
    assert all(lane["switch_was_on"] for lane in report["lanes"])
    assert first["folded"] is True and first["reviewed"] is False
    assert first["stopped_to_ask"] is False and first["fold_reverted"] is False
    assert first["class_closer"] == "a boot check refuses a clock that disagrees with the office"
    assert report["defects_now"][0]["project"] == "proj"
    assert report["defects_at_first_on"][0]["total"] == 4, (
        "the boat, the tide clock, the slip and the gate log"
    )
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert f"proj #{tide}" in out and "folded; folded; no review record" in out
    assert "class: a boot check refuses" in out
    assert "2 fix lanes, 1 closed: 0 folded with a review record" in out
    assert "defects proj:" in out and "(was 4 at its switch's first on)" in out
    assert "its board was on when planning began" in out
    assert main(["fixes", "all", "--started-off", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"
    # Every defect still on the rail says why the dial leaves it there — and
    # the reason is now the reading's own sentence, not the mark's (plan 59).
    assert "a reading says it is yours" in out
    assert "4 readings of a mark, 2 of them taking the decision off your defects" in out
    assert f"#{gate_log:<4} The gate log loses its last line — the dial is planning it now" in out
    assert [w["why"] for w in report["waiting"] if w["card_number"] == gate_log] == [
        "the dial is planning it now"
    ]


def test_a_held_plan_does_not_count_and_the_memory_floor_stops_the_beat(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """The plan "as many lanes as the machine can hold", item 3: a planned
    card whose Start is closed holds no slot, so the next eligible defect is
    taken; under the floor the beat takes nothing and the head says so with
    the numbers; and the number the owner set is never raised."""
    tide = number_of(client, TIDE)
    live = client.app.state.loops.live
    write_defect(
        repo,
        "2026-09-05-the-gate-log-loses-its-last-line",
        "The gate log loses its last line",
        "**Fix:** now",
    )
    live.rescan("proj")
    reconcile(client)
    gate_log = number_of(client, "The gate log loses its last line")
    turn(client, on=True, lanes=1)
    verify(client, machine_floor, tide)
    capsys.readouterr()
    tick(client)
    planned = len(machine_floor.state()["launch_log"])
    assert reading_for(machine_floor) is None, "the tide clock is being planned"
    # #241's lane is live and editing engine/metering.py, the file the tide
    # plan will name: shared ground, which is never a reason to wait.
    (repo / "engine").mkdir(exist_ok=True)
    (repo / "engine" / "metering.py").write_text("x\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "the meter")
    other = repo / ".claude" / "worktrees" / "card-241-the-deploy"
    git(repo, "worktree", "add", "-q", "-b", "card-241-the-deploy", str(other))
    (other / "engine" / "metering.py").write_text("changed\n")
    session_id = machine_floor.write_job(
        "beta", "beef0241", cwd=str(other), worktree=str(other), name="card-241-the-deploy"
    )
    machine_floor.write_process("beta", session_id, os.getpid(), cwd=str(other))
    # Its plan lands waiting on a card in Executing: the Start door is closed
    # by the plan's own word, and the card holds no slot.
    doors.move(client, 228, "Executing")
    land_plan(
        repo,
        TIDE_PATH,
        "2026-09-05-the-quay-clock-is-the-offices",
        "The quay clock is the office's",
        terrain=" Touches `engine/metering.py`.",
        sequencing="after #228 (the note).",
    )
    live.rescan("proj")
    tick(client)
    assert column_of(client, tide) == "Planned"
    history = detail(client, tide)["history"]
    assert any(
        h["detail"].startswith("Start waits: Nothing for you: this starts by itself once #228")
        for h in history
    )
    # The same beat took the next defect: a held plan holds nothing, so the
    # beat read the gate log's mark, and a beat after its result the planning
    # session it opened is what counts now.
    assert len(machine_floor.state()["launch_log"]) == planned + 1, "the next defect is read"
    verify(client, machine_floor, gate_log)
    capsys.readouterr()
    tick(client)
    taken = len(machine_floor.state()["launch_log"])
    assert machine_floor.state()["launch_log"][-1]["argv"][-1].startswith(
        "A plan to write for a defect the dial took"
    )
    assert [(f.card_number, f.stage.value) for f in store.fix_lanes("proj")] == [
        (tide, "planned"),
        (gate_log, "planning"),
    ]
    state = board(client)["dial"]
    assert (state["running"], state["held"], state["full"]) == (1, 1, None)
    assert main(["dial"]) == 0
    assert "1 fix lane at most across every board; 1 live now, 1 held; the machine is" in (
        capsys.readouterr().out
    )

    # The machine runs short: the beat opens nothing, even with the number
    # allowing it, and the head reads the two numbers.
    doors.move(client, 228, "Done")
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    turn(client, on=True, lanes=3)
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == taken, "nothing opened under the floor"
    assert column_of(client, tide) == "Planned", "the held plan's Start waited on the floor too"
    full = "the machine is full: 2.0 GB available, 5 GB needed"
    assert board(client)["dial"]["full"] == full
    assert any(h["detail"] == f"Start waits: {full}" for h in detail(client, tide)["history"])
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert "a reading says it is yours" in out
    # The terminal reads the machine itself, in its own process. The tide
    # plan's door is open now (#228 shipped), so it counts: the number is
    # what bounds plans written ahead of a full machine.
    assert main(["dial"]) == 0
    out = capsys.readouterr().out
    assert "3 fix lanes at most across every board; 2 live now; the machine is not quiet" in out
    assert f"; {full}" in out
    # Free swap short counts the same, on a machine that has swap.
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=1.0)
    tick(client)
    assert board(client)["dial"]["full"] == "the machine is full: 1.0 GB swap free, 5 GB needed"
    assert len(machine_floor.state()["launch_log"]) == taken
    # Room again: the beat opens the held plan's Start — into shared ground,
    # which the door names and the fold settles (item 1).
    assert detail(client, tide)["doors"]["readiness"]["state"] == "shares"
    machine_floor.set_memory(available_gb=16.0, swap_free_gb=8.0)
    tick(client)
    assert board(client)["dial"]["full"] is None
    assert column_of(client, tide) == "Executing"
    assert len(machine_floor.state()["launch_log"]) == taken + 1
    started_row = next(h for h in detail(client, tide)["history"] if h["kind"] == "started")
    assert (
        "started by the dial; #241's session is editing engine/metering.py"
        in (started_row["detail"])
    )
    assert "SHARED GROUND" in machine_floor.state()["launch_log"][-1]["argv"][-1]
    # The number the owner set is what he set, through all of it.
    assert store.dial("proj").lanes == 3
    # One lane was the number already, so the first turn wrote the switch's
    # row alone; the raise to three is the number's own row.
    assert [(c.project, c.on, c.lanes) for c in store.dial_changes()] == [
        ("proj", True, 1),
        (None, None, 3),
    ]


@pytest.mark.parametrize("worktree_gone", [False, True])
def test_a_lane_that_folded_and_closed_gives_its_memory_back_and_no_other_ending_is_touched(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys, worktree_gone: bool
):
    """The plan "as many lanes as the machine can hold", item 4: once the
    fold is recorded and the close taken, a background session whose turn
    is over is stopped through the runtime and the card says so; before
    either fact it is left alone, and after it has ended it is not stopped
    again. With the worktree removed at the fold (Hello Revenue's way) the
    lane reads ended with the process still resident, and is released the
    same."""
    doors.start(client)
    started = machine_floor.state()["launch_log"][0]
    short = started["short"]
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    state_file = machine_floor.config_dir("alpha") / "jobs" / short / "state.json"

    def turn_over() -> None:
        state = json.loads(state_file.read_text())
        state["state"] = "done"
        state_file.write_text(json.dumps(state))

    # Its turn is over with nothing folded: left as it is.
    turn_over()
    reconcile(client)
    assert machine_floor.state()["stops"] == []
    assert detail(client)["summary"]["lane_state"] == "stopped"
    # Folded, not closed: still its own.
    (worktree / "engine").mkdir(exist_ok=True)
    (worktree / "engine" / "meter.py").write_text("bill = True\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "the meter")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    capsys.readouterr()
    reconcile(client)
    assert machine_floor.state()["stops"] == []
    # Closed: the session goes, the card says why, and the memory is back.
    done = archive_plan(repo)
    (repo / "docs" / "reviews").mkdir(exist_ok=True)
    (repo / "docs" / "reviews" / "2026-09-05-the-meter.md").write_text(
        "# Review\n\n**Reviewer:** Independent test reader\n"
        "**Verification:** Close-door fixture checks passed.\n"
    )
    watch = f"the plan is archived — file {done.relative_to(repo)} by 2026-12-31 every 1h"
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
    capsys.readouterr()
    client.app.state.loops.live.rescan("proj")
    assert column_of(client, CARD) == "Executed"
    if worktree_gone:
        # Hello Revenue's fold removes the worktree: the lane reads ended
        # with the process resident, and its turn over is the registry's word.
        git(repo, "worktree", "remove", "--force", str(worktree))
    turn_over()
    reconcile(client)
    assert [s["short"] for s in machine_floor.state()["stops"]] == [short]
    opened = detail(client)
    assert opened["summary"]["lane_state"] == "ended"
    assert column_of(client, CARD) == "Executed", "the exit rule does not move a closed card"
    stopped = next(h for h in opened["history"] if h["kind"] == "stopped")
    assert stopped["actor"] == "machine"
    assert stopped["detail"] == (
        f"Stopped {short} on alpha: the lane folded and closed, so its session gives its "
        "memory back."
    )
    # The one list keeps the record, as it keeps every ended session's; the
    # process behind it is gone, and that is the memory.
    assert main(["sessions"]) == 0
    listed = next(ln for ln in capsys.readouterr().out.splitlines() if short in ln)
    assert "ended" in listed
    runtime = client.app.state.loops.runtime
    assert all(s.pid is None for s in runtime.sessions() if s.short_id == short)
    # Ended now: not stopped twice.
    reconcile(client)
    assert len(machine_floor.state()["stops"]) == 1


def test_a_suggestion_archived_a_read_before_its_plan_parks_the_card_and_the_plan_unparks_it(
    client: TestClient, repo: Path, store: Store
):
    """The plan "as many lanes as the machine can hold", item 5: the rename
    read one pass before the plan file parks the card (the seam Hello Revenue
    #384 and #386 hit); the plan landing on the next read sends it back to
    Planned with Start offered and the row on the card. In the other order
    nothing is parked. The one-read case is `tests/board/test_reconcile.py`."""
    tide = number_of(client, TIDE)
    live = client.app.state.loops.live

    def carry(suggestion_path: str, stem: str, title: str) -> None:
        plan = repo / "docs" / "plans" / f"{stem}.md"
        plan.write_text(
            f"# {title}\n\n**Status:** PENDING\n**Effort gate:** medium — one edit\n"
            f"**Carries:** {suggestion_path}\n\n## Intent\n\nThe clock.\n\n"
            "### 1. The clock\n\nDone means: it reads right.\n",
            encoding="utf-8",
        )

    def archive(suggestion_path: str, stem: str) -> None:
        done = repo / "docs" / "slice-suggestions" / "done" / Path(suggestion_path).name
        done.parent.mkdir(exist_ok=True)
        lines = (repo / suggestion_path).read_text(encoding="utf-8").split("\n")
        lines.insert(2, f"**Carried by:** docs/plans/{stem}.md")
        done.write_text("\n".join(lines), encoding="utf-8")
        (repo / suggestion_path).unlink()

    def land() -> None:
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "a read")
        live.rescan("proj")
        reconcile(client)

    # The rename first: the board parks the card, as it did on Hello Revenue.
    stem = "2026-09-05-the-quay-clock-is-the-offices"
    archive(TIDE_PATH, stem)
    land()
    assert column_of(client, tide) == "Decision moment"
    parked = detail(client, tide)["history"][0]
    assert parked["kind"] == "moved" and parked["evidence"] == "document-archived"
    # The plan a read later: the machine undoes its own move.
    carry(TIDE_PATH, stem, "The quay clock is the office's")
    land()
    assert column_of(client, tide) == "Planned"
    opened = detail(client, tide)
    assert opened["doors"]["start"]["offered"], opened["doors"]["start"]["why"]
    back = next(h for h in opened["history"] if h["kind"] == "moved")
    assert back["actor"] == "machine" and back["evidence"] == "plan-live"
    assert back["detail"].endswith(
        "parked when its suggestion was archived, but a live plan carries it now "
        f"(docs/plans/{stem}.md): back to Planned"
    )
    assert opened["summary"]["standing"]["state"] == "held"
    reconcile(client)
    assert column_of(client, tide) == "Planned", "and it stays"

    # The other order: the plan first, then the rename — nothing is parked.
    path = write_defect(
        repo,
        "2026-09-05-the-gate-log-loses-its-last-line",
        "The gate log loses its last line",
        "**Fix:** now",
    )
    land()
    gate_log = number_of(client, "The gate log loses its last line")
    other = "2026-09-05-the-gate-log-keeps-every-line"
    carry(path, other, "The gate log keeps every line")
    land()
    assert column_of(client, gate_log) == "Planned"
    archive(path, other)
    land()
    assert column_of(client, gate_log) == "Planned"
    assert all(h["evidence"] != "document-archived" for h in detail(client, gate_log)["history"])


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
    tide = number_of(client, TIDE)
    audit = number_of(client, "The night audit re-reads the whole harbour log")

    # Neither is planned by the mark alone. The unmarked one is nobody's — it
    # is read, not parked on the owner (plan 59, item 1) — and the `his` one
    # is read too; a reading that agrees leaves it his and starts nothing.
    assert detail(client, audit)["summary"]["fix"] is None
    assert detail(client, audit)["document"]["fix_note"] == "no Fix: line"
    assert detail(client, audit)["summary"]["routing"]["state"] == "needs triage"
    assert "nobody's yet" in detail(client, audit)["summary"]["routing"]["why"]
    verify(
        client,
        machine_floor,
        audit,
        result="his",
        words="the record does not say whether the audit reads the night or the week",
        source=None,
        direction=None,
    )
    assert detail(client, audit)["summary"]["routing"]["state"] == "triaged his"
    verify(
        client,
        machine_floor,
        tide,
        result="his",
        words="the record does not select which clock the quay follows",
        source=None,
        direction=None,
    )
    assert detail(client, tide)["summary"]["fix"]["mark"] == "his"
    assert detail(client, tide)["summary"]["routing"]["state"] == "triaged his"
    read_so_far = acts(machine_floor)
    tick(client)
    assert acts(machine_floor) == read_so_far, "no plan for either"

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
    verify(client, machine_floor, number)
    tick(client)
    assert acts(machine_floor) == read_so_far + 1, "read, then planned"
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
    assert acts(machine_floor) == read_so_far + 1, "asked: the owner's from here"
    assert board(client)["dial"]["running"] == 0


def test_a_planning_session_that_dies_ends_the_dials_part_and_the_card_says_why(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    machine_floor.script_launches({"then": "vanish", "after": 1.5})
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "planning"
    import time

    time.sleep(2.5)
    tick(client)
    fix = store.fix_lanes("proj")[0]
    assert fix.stage.value == "ended" and fix.note is not None
    assert fix.note.startswith("the planning session ended without a plan")
    assert detail(client, tide)["history"][0]["detail"] == fix.note
    assert detail(client, tide)["summary"]["planning"] is None
    opened = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == opened, "not taken again"


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
    (repo / "docs" / "reviews" / "2026-09-05-the-meter.md").write_text(
        "# Review\n\n**Reviewer:** Independent test reader\n"
        "**Verification:** Close-door fixture checks passed.\n"
    )
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
    assert column_of(client, number) == "Defects", "a trigger's reading moves nothing"
    turn(client, on=True, lanes=1)
    # The reading verifies the `when` mark; the trigger still governs when.
    verify(
        client,
        machine_floor,
        number,
        result="when",
        words="the tariff page exists — file docs/tariff.md by 2026-12-31 every 1h",
        source=None,
        direction=None,
    )
    assert detail(client, number)["summary"]["routing"]["state"] == "triaged when"
    read_so_far = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == read_so_far, (
        "not delivered: the defect waits"
    )

    (repo / "docs" / "tariff.md").write_text("# Tariff\n", encoding="utf-8")
    read_signals(client)
    assert len(detail(client, number)["readings"]) == 1, "not due again yet"
    later = datetime.now(UTC) + timedelta(hours=1, minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    read_signals(client)
    fired = detail(client, number)
    assert fired["readings"][0]["delivered"] is True
    assert column_of(client, number) == "Defects"
    tick(client)
    log = machine_floor.state()["launch_log"]
    assert len(log) == read_so_far + 1 and log[-1]["argv"][
        log[-1]["argv"].index("-n") + 1
    ].startswith(f"planning-card-{number}-"), "delivered: eligible as a now"


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
    assert column_of(client, number) == "Defects"
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
    assert column_of(client, number) == "Defects"
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
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "proj: auto-fix off",
        "1 fix lane at most across every board; 0 live now; the machine is quiet",
    ]
    assert main(["dial", "proj", "on", "--lanes", "2"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("proj: auto-fix on; changed ") and "first turned on" in out[0]
    assert out[1].startswith(
        "2 fix lanes at most across every board; 0 live now; the machine is quiet"
    )
    assert [(c.actor.value, c.project, c.on, c.lanes) for c in store.dial_changes()] == [
        ("owner", None, None, 2),
        ("owner", "proj", True, 2),
    ]
    assert main(["dial", "--lanes", "0"]) == 0
    assert "0 fix lanes at most across every board" in capsys.readouterr().out
    assert board(client)["dial"]["dial"]["lanes"] == 0
