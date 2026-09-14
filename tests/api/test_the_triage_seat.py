"""A defect's mark is verified before it routes, and an unmarked one is
nobody's yet (plan 59), on the floor.

The measurement that opened the card: eight live `his` defects, the oldest
forty-one days, zero answers ever given, and five of the eight were
execution mislabelled by the session that found them. So the mark alone no
longer routes anything. What is held here:

- item 3, the seat: a reading agrees and the dial takes the card; a reading
  is stricter and closes the dial at once; a reading is looser and
  authorises nothing until a commit; a `cannot tell` routes to nobody; a
  second reading cannot open while one is open; a reading that dies leaves
  the card nobody's with the reason on it; a document edited under a valid
  reading is refused until it is read again;
- item 4, the split: one document holding two decisions is separated by a
  lane that authorises neither half, and both halves come back unread;
- item 5, the door: the owner answers a parked card with no lane, his row
  stands through every failure after it, and a lane writes his ruling into
  the corpus;
- item 6, the record: one decision followed to two fates by one command.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from domain.signal import SessionWork
from domain.triage import TriageResult
from infrastructure import clock
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import (
    GRADE,
    READINGS_ON_THE_WAY,
    SOURCE,
    is_parked,
    land_on_the_way,
    number_of,
    read_the_rail_until,
    reading_for,
    tick,
    turn,
    verify,
    write_defect,
)
from tests.api.test_doors import detail, git, move, reconcile
from tests.api.test_parked_cards import BERTH_FIRST
from tests.api.test_title import PLAIN, card_a_plan, retitle
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

TITLE = "The pontoon lights stay on all night"
STEM = "2026-09-05-the-pontoon-lights-stay-on-all-night"
PATH = f"docs/slice-suggestions/{STEM}.md"


def park_the_rail(client: TestClient, machine_floor: Floor) -> None:
    """Read every defect already on the fixture's rail and land `his` on it,
    so a test about one card is about one card. A beat that opens nothing
    means the rail is quiet. Run before the test's own defect is written, so
    it can never be one of these."""
    for _ in range(READINGS_ON_THE_WAY):
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        if len(machine_floor.state()["launch_log"]) == before:
            return
        on = reading_for(machine_floor)
        assert on is not None, machine_floor.state()["launch_log"][-1]
        land_on_the_way(client, on)
    raise AssertionError("the rail never went quiet")


def on_a_quiet_rail(
    client: TestClient,
    machine_floor: Floor,
    repo: Path,
    stem: str,
    title: str,
    head: str,
    body: str,
) -> int:
    """One defect of our own, alone on a rail whose others have been read and
    left with the owner, with the dial on."""
    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    write_defect(repo, stem, title, head, body)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    return number_of(client, title)


@pytest.fixture
def defect(client: TestClient, machine_floor: Floor, repo: Path, capsys) -> int:
    number = on_a_quiet_rail(
        client,
        machine_floor,
        repo,
        STEM,
        TITLE,
        f"**Fix:** now `{SOURCE}` already says the pontoon sleeps with the harbour",
        "x",
    )
    capsys.readouterr()
    return number


def routing(client: TestClient, number: int) -> dict:
    return detail(client, number)["summary"]["routing"]


def edit(repo: Path, path: str, old: str, new: str) -> None:
    file = repo / path
    text = file.read_text(encoding="utf-8")
    assert old in text, (old, text)
    file.write_text(text.replace(old, new), encoding="utf-8")


# ── item 3: the seat ───────────────────────────────────────────────────


def test_a_reading_that_agrees_lets_the_dial_take_it_and_binds_itself_to_what_it_read(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    assert routing(client, defect)["state"] == "needs triage"
    assert "no reading has verified it" in routing(client, defect)["why"]

    opened = read_the_rail_until(client, machine_floor, defect)
    capsys.readouterr()
    brief = opened["argv"][-1]
    assert brief.startswith(f"A reading of #{defect}'s mark on Harbourmaster")
    assert "you must not go looking for one" in brief, "independence is the brief's first rule"
    assert "A decision is Dennis's only when the written record" in brief
    assert "--- the document" in brief and TITLE in brief
    assert SOURCE in brief, "the source the mark cites, resolved and carried"
    assert "does the source select this outcome?" in brief

    assert (
        main(
            [
                "triage",
                "proj",
                str(defect),
                "now",
                "the berth plan's own rule selects the harbour clock for the pontoon",
                "--source",
                SOURCE,
                "--direction",
                "automation increased",
                "--title",
                "passes",
                *GRADE,
            ]
        )
        == 0
    )
    said = capsys.readouterr().out
    assert "routes as triaged now" in said

    record = store.triages("proj", defect)[0]
    assert record.result == TriageResult.NOW
    assert record.direction is not None and record.direction.value == "automation increased"
    assert record.source_path == SOURCE and record.source_fingerprint is not None
    assert record.document_fingerprint == detail(client, defect)["document"]["fingerprint"]
    assert record.session_id == opened["session_id"]
    assert routing(client, defect)["state"] == "triaged now"

    row = next(r for r in detail(client, defect)["record"] if r["kind"] == "TRIAGED")
    assert record.decision in row["text"] and "automation increased" in row["text"]
    assert detail(client, defect)["summary"]["triaging"] is None, "the verb ended its own record"

    tick(client)
    planned = machine_floor.state()["launch_log"][-1]
    assert planned["argv"][planned["argv"].index("-n") + 1].startswith(f"planning-card-{defect}-")


def test_a_reading_is_stricter_at_once_and_a_looser_one_authorises_nothing(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """The two halves of the one rule the seat exists for."""
    verify(
        client,
        machine_floor,
        defect,
        result="his",
        words="the plan names no clock for the pontoon; both shapes are still open",
        source=None,
        direction=None,
    )
    capsys.readouterr()
    assert routing(client, defect)["state"] == "triaged his"
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == before, "stricter closes the dial at once"

    # The other half: a `now` reading of a document the corpus marks `his`.
    edit(repo, PATH, "**Fix:** now `", "**Fix:** his `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert routing(client, defect)["state"] == "stale", "the text it judged has changed"
    verify(client, machine_floor, defect)
    capsys.readouterr()
    where = routing(client, defect)
    assert where["state"] == "needs triage"
    assert "never routes more freely than the corpus" in where["why"]
    tick(client)
    assert not any(
        launch["argv"][launch["argv"].index("-n") + 1].startswith(f"planning-card-{defect}-")
        for launch in machine_floor.state()["launch_log"]
    ), "a looser row plans nothing"

    # A commit that rewrites the mark citing the reading is what authorises it.
    edit(repo, PATH, "**Fix:** his `", "**Fix:** now `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    verify(client, machine_floor, defect)
    capsys.readouterr()
    assert routing(client, defect)["state"] == "triaged now"


def test_a_card_whose_reading_cannot_move_it_is_never_read_again(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """The loop card #138 was written for. A reading lands `now` on a
    document the corpus marks `his`: the row routes to nobody until a commit
    rewrites the mark, and no reading can write that commit. The seat reads
    one card a beat and takes the oldest unread first, so before this guard
    the same card took every beat forever — 803 readings of two Hello
    Revenue cards in 23 hours, while 140 defects and every parked card
    waited behind them."""
    edit(repo, PATH, "**Fix:** now `", "**Fix:** his `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    verify(client, machine_floor, defect)
    capsys.readouterr()
    where = routing(client, defect)
    assert where["state"] == "needs triage"
    assert "never routes more freely than the corpus" in where["why"]

    for _ in range(3):
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        opened = reading_or_nothing(machine_floor, before)
        assert opened is None or reading_for(machine_floor) != defect, (
            "a reading that cannot change the card's routing is never opened again"
        )

    # What he reads while it waits: when it was read, what it landed, and
    # that a commit is what moves it — on the card and in `needle fixes`.
    today = clock.now().date().isoformat()
    assert f"read on {today}, the reading landed now" in where["why"]
    assert "the board does not read it again until then" in where["why"]
    waiting = client.get("/api/fixes").json()["waiting"]
    assert next(w["why"] for w in waiting if w["card_number"] == defect) == where["why"]
    assert main(["fixes", "proj"]) == 0
    assert f"read on {today}" in capsys.readouterr().out

    # The commit the row waits on moves the document, and the door opens.
    edit(repo, PATH, "**Fix:** his `", "**Fix:** now `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert routing(client, defect)["state"] == "stale", "the text it judged has changed"
    read_the_rail_until(client, machine_floor, defect)


def reading_or_nothing(machine_floor: Floor, before: int) -> dict | None:
    log = machine_floor.state()["launch_log"]
    return log[-1] if len(log) > before else None


def launch_of(machine_floor: Floor, session_id: str | None) -> dict:
    """One beat can do two things — follow what is open and then take the
    next card — so a launch is found by the session it started, never by its
    position in the log."""
    return next(
        launch
        for launch in machine_floor.state()["launch_log"]
        if launch["session_id"] == session_id
    )


def test_a_cannot_tell_routes_to_nobody_and_is_not_read_again(
    client: TestClient, machine_floor: Floor, store: Store, defect: int, capsys
):
    verify(
        client,
        machine_floor,
        defect,
        result="cannot-tell",
        words="the berth plan is silent and the office's own note is not in the corpus",
        source=None,
        direction=None,
    )
    capsys.readouterr()
    where = routing(client, defect)
    assert where["state"] == "cannot tell" and "office's own note" in where["why"]
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert reading_or_nothing(machine_floor, before) is None, (
        "the evidence it named has to arrive before another reading is worth anything"
    )


def test_a_second_reading_cannot_open_while_one_is_open(
    client: TestClient, machine_floor: Floor, store: Store, defect: int, capsys
):
    read_the_rail_until(client, machine_floor, defect)
    capsys.readouterr()
    open_now = store.windowless_sessions("proj", open_only=True)
    assert len([r for r in open_now if r.card_number == defect]) == 1
    with pytest.raises(Exception) as refused:
        store.open_windowless_session(
            "proj", defect, open_now[0].work, "another-session-id", "beta", open_now[0].started_at
        )
    assert "already has a triage session open" in str(refused.value)
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert reading_or_nothing(machine_floor, before) is None


def test_a_reading_that_dies_leaves_the_card_nobodys_with_the_reason_on_it(
    client: TestClient, machine_floor: Floor, store: Store, defect: int, capsys
):
    """A reading never inherits its card to the owner by dying: that is the
    failure the old default made invisible."""
    machine_floor.script_launches({"then": "vanish", "after": 1.5})
    read_the_rail_until(client, machine_floor, defect)
    capsys.readouterr()
    time.sleep(2.5)
    tick(client)
    assert routing(client, defect)["state"] == "needs triage"
    assert any(
        "the card stays nobody's" in h["detail"] and "the board reads it again" in h["detail"]
        for h in detail(client, defect)["history"]
    )


def test_a_document_edited_under_a_valid_reading_is_refused_until_it_is_read_again(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    verify(client, machine_floor, defect)
    capsys.readouterr()
    assert routing(client, defect)["state"] == "triaged now"
    edit(repo, PATH, "## Observation\n\nx", "## Observation\n\nThe lights burn from dusk to dawn")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    where = routing(client, defect)
    assert where["state"] == "stale" and "judged an earlier text" in where["why"]
    waiting = client.get("/api/fixes").json()["waiting"]
    assert [w["why"] for w in waiting if w["card_number"] == defect] == [where["why"]]


def test_a_reading_whose_source_moved_is_stale_though_the_document_did_not(
    client: TestClient, machine_floor: Floor, repo: Path, defect: int, capsys
):
    """Two fingerprints, not one: a mark can be right about a source that
    has since stopped saying what the reading read in it."""
    verify(client, machine_floor, defect)
    capsys.readouterr()
    assert routing(client, defect)["state"] == "triaged now"
    edit(repo, SOURCE, "# ", "# The changed ")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    where = routing(client, defect)
    assert where["state"] == "stale" and "the source the reading relied on" in where["why"]


def test_the_verb_refuses_a_now_with_no_resolvable_source_and_a_now_with_no_direction(
    client: TestClient, machine_floor: Floor, defect: int, capsys
):
    """Prose shaped like a source is not a source: `docs/no-such-plan.md`
    reads exactly like a real path and the verb opens the file."""
    read_the_rail_until(client, machine_floor, defect)
    capsys.readouterr()
    invented = client.post(
        f"/api/projects/proj/cards/{defect}/triage",
        json={"result": "now", "words": "the plan says so", "source": "docs/no-such-plan.md"},
    )
    assert invented.status_code == 404, "no such door: the verb is the session's, not the page's"
    assert main(["triage", "proj", str(defect), "now", "the plan says so", "-t", "passes"]) == 1
    assert "needs a source the board can read" in capsys.readouterr().err
    assert (
        main(
            [
                "triage",
                "proj",
                str(defect),
                "now",
                "the plan says so",
                "--source",
                "docs/no-such-plan.md",
                "--title",
                "passes",
                *GRADE,
            ]
        )
        == 1
    )
    assert "resolved nowhere" in capsys.readouterr().err
    assert (
        main(
            [
                "triage",
                "proj",
                str(defect),
                "now",
                "the plan says so",
                "--source",
                SOURCE,
                "--title",
                "passes",
                *GRADE,
            ]
        )
        == 1
    )
    assert "which way it moves the product" in capsys.readouterr().err


def test_the_verb_refuses_a_result_with_no_reading_open(client: TestClient, defect: int, capsys):
    assert (
        main(["triage", "proj", str(defect), "his", "it is a product call for you", "-t", "passes"])
        == 1
    )
    assert "No triage is open" in capsys.readouterr().err


# ── item 4: a split is applied by a lane that authorises neither half ──


TWO = "The office cannot see a stay that spans a month"
TWO_STEM = "2026-09-05-the-office-cannot-see-a-stay-that-spans-a-month"
TWO_PATH = f"docs/slice-suggestions/{TWO_STEM}.md"
HALF_STEM = "2026-09-05-a-stay-that-spans-a-month-adds-up-on-one-line"
HALF_PATH = f"docs/slice-suggestions/{HALF_STEM}.md"


@pytest.fixture
def two_halves(client: TestClient, machine_floor: Floor, repo: Path, capsys) -> int:
    """One document holding two decisions — the shape of Hello Revenue's
    split of 2026-09-05, which produced card #435: a fix the record settles
    beside a product call it does not, with the settled half waiting behind
    the unsettled one."""
    number = on_a_quiet_rail(
        client,
        machine_floor,
        repo,
        TWO_STEM,
        TWO,
        f"**Fix:** his `{SOURCE}` names neither of the two month views the office could get",
        (
            "1. A stay that spans a month is added twice in the total, which the berth "
            "plan's own arithmetic rule already settles.\n"
            "2. Whether the office sees such a stay by its start month or split across "
            "both, which nothing written selects.\n"
        ),
    )
    capsys.readouterr()
    return number


def play_the_split(repo: Path) -> None:
    """What the split lane does in its worktree: the settled half filed as
    its own suggestion naming where it came from, the original narrowed, one
    commit. The board reads the corpus for this and never the lane's word."""
    (repo / HALF_PATH).write_text(
        "# A stay that spans a month adds up on one line\n\n"
        "**Kind:** defect\n"
        "**Fix:** now the berth plan's arithmetic rule already settles the total\n"
        "**Found by:** the split of the month-view defect, 2026-09-05.\n"
        f"**Split from:** {TWO_PATH}\n\n"
        "## Observation\n\nThe total counts the stay twice.\n",
        encoding="utf-8",
    )
    edit(
        repo,
        TWO_PATH,
        "**Found by:**",
        f"**Split into:** {HALF_PATH}\n**Found by:**",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the split")


def test_a_split_is_separated_by_a_lane_and_both_halves_come_back_unread(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, two_halves: int, capsys
):
    verify(
        client,
        machine_floor,
        two_halves,
        result="split",
        words=(
            "the settled half is the double count, which the berth plan's arithmetic rule "
            "selects; the unsettled half is which month view the office gets, which nothing "
            "written selects"
        ),
        source=SOURCE,
        direction=None,
    )
    capsys.readouterr()
    split = store.triages("proj", two_halves)[0]
    assert split.result == TriageResult.SPLIT
    assert routing(client, two_halves)["state"] == "needs triage"
    assert "authorises neither" in routing(client, two_halves)["why"]

    tick(client)
    lane = store.corpus_lanes("proj", open_only=True)[0]
    assert lane.kind.value == "split" and lane.decision == split.decision and lane.attempt == 1
    opened = launch_of(machine_floor, lane.session_id)
    named = opened["argv"][opened["argv"].index("--worktree") + 1]
    assert named == lane.name and named.startswith(f"split-{two_halves}-")
    assert not named.startswith("card-"), "a corpus lane is never read as the card's own lane"
    brief = opened["argv"][-1]
    assert brief.startswith("A document to separate on Harbourmaster")
    assert "You decide neither." in brief and "59661dcd9" in brief
    assert f"**Split from:** {TWO_PATH}" in brief
    assert detail(client, two_halves)["summary"]["lane_state"] == "none"

    play_the_split(repo)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    tick(client)
    half = number_of(client, "A stay that spans a month adds up on one line")

    rows = {r["kind"]: r["text"] for r in detail(client, two_halves)["record"]}
    assert HALF_PATH in rows["SPLIT"] and split.decision in rows["SPLIT"]
    other = {r["kind"]: r["text"] for r in detail(client, half)["record"]}
    assert TWO_PATH in other["SPLIT"] and split.decision in other["SPLIT"]

    assert routing(client, two_halves)["state"] == "stale", "its text changed under the reading"
    assert routing(client, half)["state"] == "needs triage"
    assert "authorised neither half" in routing(client, half)["why"]
    child = store.triages("proj", half)[0]
    assert child.parent == split.decision, "the two halves are followed from one identity"
    assert store.corpus_lanes("proj", open_only=True) == []


# ── item 5: a genuine his card has a door ──────────────────────────────


def answer(client: TestClient, number: int, text: str) -> dict:
    return client.post(f"/api/projects/proj/cards/{number}/answer", json={"text": text})


RULING = "The pontoon follows the harbour clock; make it a now."


def play_the_ruling(repo: Path, decision: str) -> None:
    edit(repo, PATH, "**Fix:** his `", "**Fix:** now `")
    edit(
        repo,
        PATH,
        "**Kind:** defect",
        "**Kind:** defect\n**Ruled by:** the owner on 2026-09-05, on the card "
        f"(decision {decision})",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the ruling applied")


def test_the_owner_answers_a_parked_card_and_a_lane_writes_his_ruling_into_the_corpus(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """The first `answered` row a parked defect has ever had: before this the
    Answer door read *No live session to answer* and the pile drained at
    zero."""
    edit(repo, PATH, "**Fix:** now `", "**Fix:** his `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert detail(client, defect)["doors"]["answer"]["offered"] is False
    assert detail(client, defect)["doors"]["answer"]["why"] == (
        "Nothing for you: there is no live session to answer."
    )
    assert answer(client, defect, RULING).status_code == 409, "not on his pile until it is read"

    verify(
        client,
        machine_floor,
        defect,
        result="his",
        words="the plan names no clock for the pontoon; both shapes are still open",
        source=None,
        direction=None,
    )
    capsys.readouterr()
    reading = store.triages("proj", defect)[0]
    door = detail(client, defect)["doors"]["answer"]
    assert door["offered"] is True and "A second reading says the decision is yours" in door["why"]

    ruled = answer(client, defect, RULING)
    assert ruled.status_code == 200, ruled.text
    assert "the board opens a lane that rewrites the mark" in ruled.json()["said"]
    history = detail(client, defect)["history"]
    assert history[0]["kind"] == "answered" and history[0]["actor"] == "owner"
    assert history[0]["detail"] == f"Ruled: {RULING}"
    assert store.answers("proj")[defect].detail == f"Ruled: {RULING}"
    assert detail(client, defect)["doors"]["answer"]["offered"] is False, "never asked twice"
    assert "You ruled on this on" in detail(client, defect)["doors"]["answer"]["why"]

    tick(client)
    lane = store.corpus_lanes("proj", open_only=True)[0]
    assert lane.kind.value == "ruling" and lane.decision == reading.decision
    brief = launch_of(machine_floor, lane.session_id)["argv"][-1]
    assert brief.startswith("A ruling to apply on Harbourmaster")
    assert RULING in brief and "Ruled by:" in brief

    play_the_ruling(repo, reading.decision)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    tick(client)
    assert store.corpus_lanes("proj", open_only=True) == []
    assert any(
        h["detail"].startswith("Your ruling is in the corpus")
        for h in detail(client, defect)["history"]
    )
    assert detail(client, defect)["summary"]["fix"]["mark"] == "now"
    assert main(["fixes", "proj"]) == 0
    out = capsys.readouterr().out
    assert f"#{defect}" in out
    # His ruling made the mark; a fresh reading verifies the new text, which
    # is the same rule as any other document that changed.
    assert routing(client, defect)["state"] == "stale"


def test_every_failure_after_his_row_leaves_it_standing_and_the_machine_retries_once(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """The four seams the plan names: the lane failing to launch, the lane
    dying before its commit, the commit landing with the push refused, and a
    restart between the row and the mark. All four are one shape — the
    corpus does not say it — and the row is what survives all of them."""
    edit(repo, PATH, "**Fix:** now `", "**Fix:** his `")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    verify(
        client,
        machine_floor,
        defect,
        result="his",
        words="the plan names no clock for the pontoon; both shapes are still open",
        source=None,
        direction=None,
    )
    capsys.readouterr()
    assert answer(client, defect, RULING).status_code == 200

    # 1. The lane does not launch at all.
    machine_floor.refuse_best("no slot has headroom")
    tick(client)
    lanes = store.corpus_lanes("proj")
    assert len(lanes) == 1 and lanes[0].ended_at is not None
    assert lanes[0].note is not None and "did not start" in lanes[0].note
    assert store.answers("proj")[defect].detail == f"Ruled: {RULING}", "his row stands"

    # 2. The lane launches and dies before writing anything: one retry, and
    # then the card carries the half-state in words rather than looping.
    machine_floor.answer_best("alpha", "fable")
    machine_floor.script_launches({"then": "vanish", "after": 1.5})
    tick(client)
    assert len(store.corpus_lanes("proj")) == 2
    assert store.corpus_lanes("proj")[1].attempt == 2
    time.sleep(2.5)
    tick(client)
    ended = store.corpus_lanes("proj")[1]
    assert ended.ended_at is not None and ended.note is not None
    assert "the corpus does not say it" in ended.note
    said = detail(client, defect)["history"][0]["detail"]
    assert "the board stops trying; the record stands and this card is half-ruled" in said

    # 3. No third lane: the record stands, and he is not asked again.
    tick(client)
    assert len(store.corpus_lanes("proj")) == 2
    assert detail(client, defect)["doors"]["answer"]["offered"] is False
    assert routing(client, defect)["state"] == "triaged his", "his ruling is still the record"

    # 4. A restart between the row and the mark changes nothing: both are in
    # the store, and the corpus is read fresh.
    reopened = Store(store.path)
    try:
        assert reopened.answers("proj")[defect].detail == f"Ruled: {RULING}"
        assert len(reopened.corpus_lanes("proj")) == 2
    finally:
        reopened.close()


# ── item 6: one identity, one direction, one command ───────────────────


def test_one_command_follows_a_split_decision_to_both_fates(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, two_halves: int, capsys
):
    verify(
        client,
        machine_floor,
        two_halves,
        result="split",
        words="the double count is settled by the berth plan; the month view is not",
        source=SOURCE,
        direction=None,
    )
    capsys.readouterr()
    split = store.triages("proj", two_halves)[0]
    tick(client)
    play_the_split(repo)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    tick(client)
    half = number_of(client, "A stay that spans a month adds up on one line")

    verify(
        client,
        machine_floor,
        half,
        words="the berth plan's arithmetic rule settles the total",
        direction="strictness raised",
    )
    capsys.readouterr()
    assert main(["decisions", "proj"]) == 0
    out = capsys.readouterr().out
    assert f"#{two_halves}" in out and f"#{half}" in out
    assert f"(out of {split.decision})" in out, "the two halves come out of one identity"
    assert "direction: strictness raised" in out
    assert "routes as: triaged now" in out, "the extracted half, verified on its own"
    assert "routes as: triaged his" in out, "the residual, still the owner's"
    assert "nothing has been built on it yet" in out
    assert "taken off your defects as `now`" in out
    assert "directions: 1 strictness raised" in out

    assert main(["decisions", "proj", "--first", "1"]) == 0
    first = capsys.readouterr().out
    assert "1 decisions, " in first and f"#{half}" not in first, (
        "the cold audit reads the first N in order, before it sees their outcomes"
    )

    # The fate follows the card, not a second ledger: the dial's fix lane on
    # the settled half carries the decision the reading minted.
    tick(client)
    fix = store.fix_lanes("proj")[-1]
    assert fix.card_number == half
    assert fix.decision == store.triages("proj", half)[-1].decision
    assert main(["decisions", "proj"]) == 0
    assert "the dial's fix lane is planning" in capsys.readouterr().out


# ── card #138, item 2: the fuse behind the guard ───────────────────────


def spend_readings(client: TestClient, store: Store, number: int, times: int = 3) -> str:
    """Three readings the board opened on the card's text as it stands and
    saw end — the exact rows a hole in the seat would leave, whatever the
    readings landed — written straight into the store, since the guard
    refuses to open a second one and the verb refuses a result with no
    grade: the fuse is proved from the state it reads, not from a hole
    manufactured above it."""
    text = client.app.state.loops.live.readings_spent("proj")[number].text
    for i in range(times):
        at = clock.now()
        row = store.open_windowless_session(
            "proj",
            number,
            SessionWork.TRIAGE,
            f"spent-{number}-{i}",
            "alpha",
            at,
            text_fingerprint=text,
        )
        store.end_windowless_session(row.id, at)
    reconcile(client)
    return text


def face_of(client: TestClient, number: int) -> dict:
    board = client.get("/api/projects/proj/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return card
    raise AssertionError(f"#{number} is not on the board")


def readings_of(store: Store, number: int) -> int:
    return len([r for r in store.windowless_sessions("proj") if r.card_number == number])


def test_three_readings_on_one_text_stop_the_board_loudly_and_a_changed_text_starts_it_again(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """The fuse (card #138, item 2): whatever a hole above it does, no card
    is read more than three times on one text, and the card says so where
    the owner looks — its face, the head's count and `needle fixes` — never
    as a bare `needs triage`."""
    spend_readings(client, store, defect)
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert reading_or_nothing(machine_floor, before) is None, "the fuse holds the seat shut"
    assert readings_of(store, defect) == 3

    face = face_of(client, defect)
    assert face["state"]["word"] == "stopped reading" and face["state"]["meaning"] == "broken"
    assert "read this 3 times on this text" in face["state"]["detail"]
    assert "a change to the document or to the source its mark cites" in face["state"]["detail"]
    assert "readings stopped" in face["claims"]
    head = client.get("/api/projects/proj/board").json()["attention"]
    assert any(c["claim"] == "readings stopped" and c["count"] == 1 for c in head["broken"]), head
    waiting = client.get("/api/fixes").json()["waiting"]
    why = next(w["why"] for w in waiting if w["card_number"] == defect)
    assert "read this 3 times on this text" in why and "needs triage" not in why
    assert main(["fixes", "proj"]) == 0
    assert "read this 3 times on this text" in capsys.readouterr().out

    # The document changes: a new text, a new count, and the seat opens.
    edit(repo, PATH, "## Observation\n\nx", "## Observation\n\nThe lights burn from dusk to dawn")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert face_of(client, defect)["state"]["word"] != "stopped reading"
    read_the_rail_until(client, machine_floor, defect)
    assert readings_of(store, defect) == 4


def test_the_fuse_holds_a_title_and_a_parked_card_alike_and_a_new_park_or_title_starts_it_again(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    plan = card_a_plan(client, repo, "proj", "2026-09-14-the-harbour-lights-dim-at-midnight", PLAIN)
    parked = BERTH_FIRST
    assert is_parked(client, parked)
    # The rail's first walk read the parked card once and landed `his` on
    # it; that reading was of the record before his line, a different text.
    parked_before = readings_of(store, parked)
    # His answer is what re-opens a parked card's reading (card #82, ruling
    # 5), so the seat wants it again — and the fuse is what then holds it.
    assert (
        answer(client, parked, "the four rulings stand; one sitting, next week").status_code == 200
    )
    spend_readings(client, store, plan)
    spend_readings(client, store, parked)
    park_the_rail(client, machine_floor)
    assert readings_of(store, plan) == 3, "the title is not read a fourth time"
    assert readings_of(store, parked) == parked_before + 3, (
        "the parked card is not read a fourth time on this record"
    )

    title = face_of(client, plan)
    assert title["state"]["word"] == "stopped reading" and "readings stopped" in title["claims"]
    yours = face_of(client, parked)
    assert yours["state"]["word"] == "your move", "his column stays his"
    assert "since it was parked or you last answered on it" in yours["state"]["detail"]
    assert "parking it again starts them again" in yours["state"]["detail"]
    assert "readings stopped" in yours["claims"]

    # A rewritten title is a new text; a new park is a new count.
    retitle(
        client,
        repo,
        "proj",
        repo / "docs" / "plans" / "2026-09-14-the-harbour-lights-dim-at-midnight.md",
        PLAIN,
        "The harbour lights dim at midnight",
    )
    assert face_of(client, plan)["state"]["word"] != "stopped reading"
    move(client, parked, "Up next")
    move(client, parked, "Decision moment")
    assert "readings stopped" not in face_of(client, parked)["claims"]
    read_the_rail_until(client, machine_floor, plan)
    assert readings_of(store, plan) == 4
    land_on_the_way(client, plan)
    read_the_rail_until(client, machine_floor, parked)
    assert readings_of(store, parked) == parked_before + 4


# ── the independent review's two demonstrated findings, inverted ───────


def test_a_third_reading_that_settles_the_card_is_settled_not_stopped(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, defect: int, capsys
):
    """Finding 1 of #138's review: the fuse's words belong only where the
    fuse is what holds the card. Two readings die, the third lands `his`:
    the card is his, and broken must not paint over yours."""
    text = spend_readings(client, store, defect, times=2)
    store.open_windowless_session(
        "proj",
        defect,
        SessionWork.TRIAGE,
        "third-real",
        "alpha",
        clock.now(),
        text_fingerprint=text,
    )
    assert (
        main(
            [
                "triage",
                "proj",
                str(defect),
                "his",
                "which of the two shapes is his call",
                "--title",
                "passes",
                *GRADE,
            ]
        )
        == 0
    )
    capsys.readouterr()
    reconcile(client)
    count = client.app.state.loops.live.readings_spent("proj")[defect]
    assert count.opened == 3 and count.stopped and not count.wanted
    assert routing(client, defect)["state"] == "triaged his"
    face = face_of(client, defect)
    assert face["state"]["word"] != "stopped reading" and "readings stopped" not in face["claims"]
    waiting = client.get("/api/fixes").json()["waiting"]
    why = next(w["why"] for w in waiting if w["card_number"] == defect)
    assert "nothing settled it" not in why and "a reading says it is yours" in why
    # And the seat still opens nothing on it: the text is spent either way.
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert reading_or_nothing(machine_floor, before) is None


def test_a_parked_readings_landing_does_not_move_the_text_it_was_bound_to(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    """Finding 2 of #138's review: a parked reading writes a TRIAGED row
    when it lands, so the text the seat counts by must leave out the rows
    a landing writes, or every landing would reset its own count."""
    turn(client, on=True, lanes=1)
    park_the_rail(client, machine_floor)
    parked = BERTH_FIRST
    assert is_parked(client, parked)
    landed = [
        s
        for s in store.windowless_sessions("proj")
        if s.card_number == parked and s.ended_at is not None and s.text_fingerprint is not None
    ]
    assert len(landed) == 1, "the rail's walk read the parked card once"
    now = client.app.state.loops.live.readings_spent("proj")[parked]
    assert landed[0].text_fingerprint == now.text, "the landing's own row is not the text"
    assert now.opened == 1 and now.parked and not now.wanted
