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
from domain.triage import TriageResult
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import (
    SOURCE,
    number_of,
    open_readings,
    read_the_rail_until,
    reading_for,
    tick,
    turn,
    verify,
    write_defect,
)
from tests.api.test_doors import detail, git, reconcile
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
    for _ in range(20):
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        if len(machine_floor.state()["launch_log"]) == before:
            return
        on = reading_for(machine_floor)
        assert on is not None, machine_floor.state()["launch_log"][-1]
        assert (
            main(["triage", "proj", str(on), "his", "the record selects neither of the two"]) == 0
        )
    raise AssertionError("the rail never went quiet")


def on_a_quiet_rail(
    client: TestClient, machine_floor: Floor, repo: Path, stem: str, title: str, head: str, body: str
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
    assert main(["triage", "proj", str(defect), "now", "the plan says so"]) == 1
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
            ]
        )
        == 1
    )
    assert "resolved nowhere" in capsys.readouterr().err
    assert (
        main(["triage", "proj", str(defect), "now", "the plan says so", "--source", SOURCE]) == 1
    )
    assert "which way it moves the product" in capsys.readouterr().err


def test_the_verb_refuses_a_result_with_no_reading_open(
    client: TestClient, defect: int, capsys
):
    assert main(["triage", "proj", str(defect), "his", "it is a product call for you"]) == 1
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
    assert detail(client, defect)["doors"]["answer"]["why"] == "No live session to answer."
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
    assert door["offered"] is True and "A reading says this decision is yours" in door["why"]

    ruled = answer(client, defect, RULING)
    assert ruled.status_code == 200, ruled.text
    assert "the board opens a lane that rewrites the mark" in ruled.json()["said"]
    history = detail(client, defect)["history"]
    assert history[0]["kind"] == "answered" and history[0]["actor"] == "owner"
    assert history[0]["detail"] == f"Ruled: {RULING}"
    assert store.answers("proj")[defect].detail == f"Ruled: {RULING}"
    assert detail(client, defect)["doors"]["answer"]["offered"] is False, "never asked twice"
    assert "you ruled on this on" in detail(client, defect)["doors"]["answer"]["why"]

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
    assert "taken off your rail as `now`" in out
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
