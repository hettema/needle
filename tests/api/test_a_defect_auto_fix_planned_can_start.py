"""A defect auto-fix planned can start, whatever machine wrote the plan and
whatever the title read (card #151), on the floor.

What is held here:

- item 1, the settle is measured and never clocked: a planning session whose
  plan reaches origin from somewhere that is not the board's checkout is read
  in by the beat's own levelling and starts, where before the board waited
  two minutes for a watcher that only ever fires on a commit already in its
  own checkout; a session that pushed nothing is ended only after a levelling
  that ran after its turn answered level, and the card's history says so; the
  fetch happens once per turn's end and not once a beat; a checkout the level
  cannot move leaves the lane planning with the level's own words on the card,
  and when the hour ends it the card says the level never ran;
- item 2, a plan that arrives after the board gave up re-opens the card;
- item 3, a planning session is told which words failed, and a reading that
  refuses the plan's title is handed back to the session that wrote it until
  its hour runs out — except on a card whose face is not its plan's title,
  which no rewrite can fix (ruling 8);
- item 4, `needle fixes --stranded` counts what the dial left behind.

What opened the card: Hello Revenue #453 on 2026-09-15, the first card the
switch took, whose plan was pushed from the rented machine and whose Start its
own title closed.
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from api.cli import main
from domain.card import CardOrigin
from domain.signal import SessionWork
from infrastructure.schema import CardRow
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import (
    SOURCE,
    TIDE,
    TIDE_PATH,
    board,
    detail,
    number_of,
    read_the_rail_until,
    tick,
    turn,
    verify,
)
from tests.api.test_doors import column_of, git, reconcile
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

STEM = "2026-09-05-the-quay-clock-is-the-offices"
PLAIN = "The quay clock is the office's"
JARGON = "A planning lane's fix stage is machine ended"
"""A title the cold reading refuses: it names the machinery and not what he
gets, and every word of it is in docs/vocabulary.md."""


def plan_text(title: str, suggestion_path: str) -> str:
    return (
        f"# {title}\n\n**Status:** PENDING\n**Written:** 2026-09-05, by the dial's planning "
        f"session\n**Effort gate:** medium — one edit and a check\n**Carries:** {suggestion_path}\n"
        "**Class:** a boot check refuses a clock that disagrees with the office\n\n"
        "## Intent\n\nThe display reads the office's clock.\n\n"
        "### 1. The clock\n\nDone means: the display never keeps its own.\n"
    )


def push_a_plan(
    repo: Path, tmp_path: Path, suggestion_path: str, stem: str, title: str, *, name: str = "away"
) -> Path:
    """What a planning session that runs anywhere but the board's own machine
    does: the plan committed in its own clone of the project and pushed to
    origin. The board's checkout is one commit behind and its corpus watcher
    has seen nothing — which is the whole of what this card fixes."""
    clone = tmp_path / name
    if not clone.exists():
        git(tmp_path, "clone", "-q", str(repo.parent / "origin.git"), str(clone))
        git(clone, "checkout", "-q", "develop")
    (clone / "docs" / "plans" / f"{stem}.md").write_text(
        plan_text(title, suggestion_path), encoding="utf-8"
    )
    done = clone / "docs" / "slice-suggestions" / "done" / Path(suggestion_path).name
    done.parent.mkdir(exist_ok=True)
    text = (clone / suggestion_path).read_text(encoding="utf-8").split("\n")
    text.insert(2, f"**Carried by:** docs/plans/{stem}.md")
    done.write_text("\n".join(text), encoding="utf-8")
    (clone / suggestion_path).unlink(missing_ok=True)
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", f"plan by the dial: {title}")
    git(clone, "push", "-q", "origin", "develop")
    return clone


def a_planning_session(client: TestClient, machine_floor: Floor, number: int) -> dict:
    """The dial's planning session for this card, whose turn ends without it
    writing anything into the board's own checkout."""
    machine_floor.script_launches({"then": "done", "after": 0.4})
    tick(client)
    time.sleep(1.2)
    return machine_floor.state()["launch_log"][-1]


def end_the_turn(launch: dict) -> None:
    """The registry says this session's turn is over, exactly as the fake's
    own `done` fate writes it: the process stays where it is, the state is
    done, and the stamp moves. What the beat settles against."""
    path = Path(launch["config_dir"]) / "jobs" / launch["short"] / "state.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    blob["state"] = "done"
    blob["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps(blob), encoding="utf-8")


def make_imported(store: Store, number: int) -> None:
    """The card as one that came over from the first board. Such a card keeps
    its own title whatever document takes it over (`board/reconcile.py`, the
    retitle guard), which is the state ruling 8 is about. No verb writes an
    origin, so the row is written here."""
    with store._session() as session, session.begin():  # noqa: SLF001 — no verb writes an origin
        row = session.scalars(
            select(CardRow).where(CardRow.project_slug == "proj", CardRow.number == number)
        ).one()
        row.origin = CardOrigin.IMPORTED.value


def resumes(machine_floor: Floor) -> list[dict]:
    """Every launch that carried a session on rather than starting a fresh
    one: what the board does when it hands a title's refusal back. Counted
    instead of the whole log, because the same beat may open a reading of
    another card and that is not this card's business."""
    return [
        launch for launch in machine_floor.state()["launch_log"] if "--resume" in launch["argv"]
    ]


def history_of(client: TestClient, number: int) -> list[str]:
    return [h["detail"] for h in detail(client, number)["history"]]


# ── item 1: the settle is a levelling, not a clock ─────────────────────


def test_a_plan_pushed_from_elsewhere_is_read_in_by_the_beat_and_the_card_starts(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    assert store.fix_lanes("proj")[0].stage.value == "planning"

    # The plan reaches origin, and nothing puts it in the board's checkout.
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, PLAIN)
    assert not (repo / "docs" / "plans" / f"{STEM}.md").exists(), "the board has not seen it"

    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "started", (
        "the beat levels its own copy at the turn's end and reads the plan in",
        lane.note,
        history_of(client, tide)[:3],
    )
    assert column_of(client, tide) == "Executing"
    assert (repo / "docs" / "plans" / f"{STEM}.md").exists(), "the beat's own level brought it"
    assert any("The plan landed" in line for line in history_of(client, tide))


def test_the_fetch_is_once_per_turns_end_and_never_once_a_beat(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    """Ruling 3: the beat levels its own copy at a turn's end, and a beat
    that has nothing new to settle costs no fetch. The board levels every
    project once as it starts, so what is measured here is the movement of
    that stamp, not its presence."""
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    # Its turn is still running: nothing to settle, so nothing is fetched.
    machine_floor.script_launches({"then": "work"})
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "planning"
    before = store.trunk("proj").read_at
    tick(client)
    tick(client)
    assert store.trunk("proj").read_at == before, "a working session settles nothing"

    # Its turn ends: one level settles it, and no beat after it fetches again.
    end_the_turn(machine_floor.state()["launch_log"][-1])
    tick(client)
    settled = store.trunk("proj").read_at
    assert settled is not None and settled != before, (
        "the turn ended, so the beat levelled the board's own copy"
    )
    tick(client)
    assert store.trunk("proj").read_at == settled, "one fetch per turn's end, not one a beat"


def test_a_turn_whose_end_is_not_stamped_yet_settles_nothing_and_fetches_nothing(
    client: TestClient, machine_floor: Floor, store: Store
):
    """The registry stamps a turn's end; until it has, there is nothing to
    measure a levelling against. Answering "level now" there would fetch on
    every beat rather than once per turn's end, which is what ruling 3
    refuses — so an unstamped session settles nothing at all."""
    live = client.app.state.loops.live.projects["proj"]
    dial = client.app.state.dial
    before = store.trunk("proj").read_at

    class Unstamped:
        updated_at = None

    assert dial._levelled_after(live, Unstamped()) is None
    assert store.trunk("proj").read_at == before, "nothing was fetched"


def test_a_session_that_pushed_nothing_is_ended_only_after_a_level_that_found_nothing(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "ended" and lane.note is not None
    assert "levelled its own copy" in lane.note and "the corpus says nothing" in lane.note
    assert store.trunk("proj").read_at is not None
    assert lane.note in history_of(client, tide)


def test_a_checkout_the_level_cannot_move_holds_the_lane_and_the_hour_says_so(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path, monkeypatch
):
    """A board whose own checkout is dirty and behind cannot read a plan in.
    The lane waits within the planning hour with the level's own words on the
    card, once and not once a beat; when the hour ends it, the card says the
    level never ran rather than that the session wrote nothing."""
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, PLAIN)
    # Uncommitted work in a tracked file of the board's own checkout:
    # `git.level` will not move such a checkout, and answers level False
    # because it is behind. Untracked files would not do — the level ignores
    # those — which is the difference between a checkout it declines to move
    # and one it simply has not been asked about.
    source = repo / SOURCE
    source.write_text(source.read_text(encoding="utf-8") + "\nthe owner's own edit\n", "utf-8")

    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "planning", "the level did not run, so nothing is concluded"
    held = [line for line in history_of(client, tide) if line.startswith("The board could not")]
    assert len(held) == 1 and "uncommitted work" in held[0]
    tick(client)
    assert (
        len([line for line in history_of(client, tide) if line.startswith("The board could not")])
        == 1
    ), "said once per spell, not once a beat"

    # The hour runs out: the card says the level never ran.
    monkeypatch.setattr("api.dial.PLANNING_SECONDS", 0.5)
    time.sleep(0.6)
    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "ended" and lane.note is not None
    assert "was never levelled" in lane.note and "uncommitted work" in lane.note


# ── item 2: a plan that arrives after the board gave up ────────────────


def test_a_plan_that_arrives_after_the_board_gave_up_re_opens_the_card(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "ended", "the board gave up on it"

    # The plan lands afterwards — from anywhere; here in the board's own
    # checkout, so this holds with no levelling in play at all.
    (repo / "docs" / "plans" / f"{STEM}.md").write_text(
        plan_text(PLAIN, TIDE_PATH), encoding="utf-8"
    )
    done = repo / "docs" / "slice-suggestions" / "done" / Path(TIDE_PATH).name
    done.parent.mkdir(exist_ok=True)
    text = (repo / TIDE_PATH).read_text(encoding="utf-8").split("\n")
    text.insert(2, f"**Carried by:** docs/plans/{STEM}.md")
    done.write_text("\n".join(text), encoding="utf-8")
    (repo / TIDE_PATH).unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the plan, late")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "started", (lane.note, history_of(client, tide)[:3])
    assert column_of(client, tide) == "Executing"
    assert any("after the planning session was called ended" in h for h in history_of(client, tide))
    # It is still a card the dial took once: no second planning session.
    opened = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == opened
    assert len(store.fix_lanes("proj")) == 1, "not planned a second time"


def test_the_beat_brings_back_one_card_a_beat_and_never_past_the_number(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    """A backlog of ended lanes whose plans arrived later does not become a
    burst of lanes in one beat. Seven cards on Hello Revenue stood in exactly
    this shape the day the re-open was written, and a dial set to one means
    one — the rest come back on the beats after, each judged on the room and
    the number as they stand then."""
    from domain.dial import FixStage

    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    tick(client)
    first = store.fix_lanes("proj")[0]
    assert first.stage.value == "ended"

    # Two more cards in the same state: a lane the dial ran and gave up on,
    # planted on cards that already carry a plan of their own.
    others = [
        c.number
        for c in store.cards("proj")
        if c.link is not None and c.link.kind.value == "plan" and c.number != tide
    ][:2]
    assert len(others) == 2, "the fixture carries plan cards to lend this test"
    for number in others:
        planted = store.open_fix_lane("proj", number, first.planning_started_at)
        store.stage_fix_lane(
            planted.id, FixStage.ENDED, first.planning_started_at, note="the board gave up"
        )

    # The first card's own plan lands too, so three lanes could come back.
    (repo / "docs" / "plans" / f"{STEM}.md").write_text(
        plan_text(PLAIN, TIDE_PATH), encoding="utf-8"
    )
    done = repo / "docs" / "slice-suggestions" / "done" / Path(TIDE_PATH).name
    done.parent.mkdir(exist_ok=True)
    text = (repo / TIDE_PATH).read_text(encoding="utf-8").split("\n")
    text.insert(2, f"**Carried by:** docs/plans/{STEM}.md")
    done.write_text("\n".join(text), encoding="utf-8")
    (repo / TIDE_PATH).unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the plans, late")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    ended_before = sum(1 for f in store.fix_lanes("proj") if f.stage == FixStage.ENDED)
    assert ended_before == 3, "three lanes stand ended with a plan on their card"
    tick(client)
    stages = [f.stage.value for f in store.fix_lanes("proj")]
    assert stages.count("ended") >= 2, (stages, "at most one comes back in a beat")
    assert sum(1 for s in stages if s in ("planned", "started")) <= 1, (
        stages,
        "a dial set to one never puts a second lane into execution in one beat",
    )


def test_a_lane_that_ran_and_ended_on_its_own_work_is_never_re_opened(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    """Only a lane that ended before it was ever planned comes back. One that
    reached Planned and ran is the owner's from here, whatever its card says."""
    from domain.dial import FixStage

    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    tick(client)
    fix = store.fix_lanes("proj")[0]
    # Give it the stamps of a lane that was planned and started, then ended.
    store.stage_fix_lane(fix.id, FixStage.PLANNED, fix.planning_started_at)
    store.stage_fix_lane(fix.id, FixStage.STARTED, fix.planning_started_at)
    store.stage_fix_lane(fix.id, FixStage.ENDED, fix.planning_started_at, note="ended by its work")
    (repo / "docs" / "plans" / f"{STEM}.md").write_text(
        plan_text(PLAIN, TIDE_PATH), encoding="utf-8"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "a plan beside it")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "ended", "it ran; it is the owner's"


# ── item 4: the count ──────────────────────────────────────────────────


def test_needle_fixes_stranded_counts_what_the_dial_left_and_the_beat_repairs_it(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "ended"
    capsys.readouterr()
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "0\n", "an ended lane whose card has no plan is not stranded"

    # Its plan lands: until a beat runs, the card is on his desk with a plan.
    (repo / "docs" / "plans" / f"{STEM}.md").write_text(
        plan_text(PLAIN, TIDE_PATH), encoding="utf-8"
    )
    done = repo / "docs" / "slice-suggestions" / "done" / Path(TIDE_PATH).name
    done.parent.mkdir(exist_ok=True)
    text = (repo / TIDE_PATH).read_text(encoding="utf-8").split("\n")
    text.insert(2, f"**Carried by:** docs/plans/{STEM}.md")
    done.write_text("\n".join(text), encoding="utf-8")
    (repo / TIDE_PATH).unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the plan, late")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    capsys.readouterr()
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "1\n"
    assert main(["fixes", "proj", "--stranded"]) == 0
    said = capsys.readouterr().out
    assert "left on your desk by the dial: the beat ended it without a plan" in said

    # A beat repairs exactly this shape, and the count goes back to zero.
    tick(client)
    capsys.readouterr()
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"


def test_the_count_names_the_selector_so_the_loops_own_command_runs(
    client: TestClient, machine_floor: Floor, capsys
):
    """`--count` with no selector is refused, and `--stranded` is one: the
    Loop at the foot of this card's plan runs `--stranded --count`."""
    assert main(["fixes", "all", "--count"]) == 1
    assert "--stranded" in capsys.readouterr().err
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "0\n"


# ── item 3: the writer is told which words failed, and keeps the reading ──


FAILED_WORDS = "lane,machine ended,fix stage"
REFUSAL = "it names the machinery and not what he gets"


def verify_with_a_failing_title(client: TestClient, machine_floor: Floor, number: int) -> dict:
    """The defect's own reading: its mark verified `now`, and its title
    refused — the state Hello Revenue #453 was in when the dial took it."""
    from tests.api.test_dial import GRADE
    from tests.api.test_dial import SOURCE as MARK_SOURCE

    opened = read_the_rail_until(client, machine_floor, number)
    assert (
        main(
            [
                "triage",
                "proj",
                str(number),
                "now",
                "the tide table plan names the harbour clock as the reference",
                "--source",
                MARK_SOURCE,
                "--direction",
                "no direction",
                "--title",
                REFUSAL,
                "--failed",
                FAILED_WORDS,
                *GRADE,
            ]
        )
        == 0
    )
    reconcile(client)
    return opened


def read_the_title(client: TestClient, machine_floor: Floor, number: int, *argv: str) -> dict:
    """Open the seat's reading of this card's title and land the verdict."""
    opened = read_the_rail_until(client, machine_floor, number)
    assert main(["triage", "proj", str(number), *argv]) == 0
    reconcile(client)
    return opened


def test_the_planning_brief_opens_with_the_words_that_failed_and_his_test(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify_with_a_failing_title(client, machine_floor, tide)
    machine_floor.script_launches({"then": "work"})
    tick(client)
    brief = machine_floor.state()["launch_log"][-1]["argv"][-1]
    assert brief.startswith("A cold reading with no share of your context could not place")
    assert REFUSAL in brief
    assert "The words that failed: lane, machine ended, fix stage." in brief
    assert "could he place it against every other card without opening it?" in brief
    assert "docs/vocabulary.md" in brief
    # The plan's own brief still follows it whole.
    assert "A plan to write for a defect the dial took" in brief
    assert "Five rules" in brief


def test_a_title_the_reading_refuses_goes_back_to_its_writer_until_a_reading_passes(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path
):
    """The whole of item 3: the plan lands with a title that fails, the seat
    reads it, the board hands the refusal back to the session that wrote it,
    and the card starts when a reading of the title that writer then wrote
    passes. One session of this card's lives at a time, so the reading always
    has room beside the lane under a number of one."""
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify_with_a_failing_title(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, JARGON)

    # The plan lands and Start waits on the title, as it does for any card.
    tick(client)
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "planned", lane.note
    assert column_of(client, tide) == "Planned"
    assert store.open_windowless_sessions("proj", SessionWork.PLANNING).get(tide) is None, (
        "no writer is kept alive while the reading it waits on has to open"
    )

    # The seat reads the plan's title — it has room, because the lane holds
    # no process — and refuses it.
    read_the_title(
        client, machine_floor, tide, "--title", "still the machinery", "--failed", "fix stage"
    )
    before = len(resumes(machine_floor))

    tick(client)
    assert len(resumes(machine_floor)) == before + 1, "the refusal was handed back"
    resumed = resumes(machine_floor)[-1]
    assert "--resume" in resumed["argv"], "the same colleague, not a fresh one"
    prompt = resumed["argv"][-1]
    assert prompt.startswith("The plan you wrote for #")
    assert "still the machinery" in prompt and "Rewrite the title" in prompt
    assert "`**Carries:**` line stays exactly as it is" in prompt
    assert "inside the hour your session began with" in prompt
    record = store.open_windowless_sessions("proj", SessionWork.PLANNING)[tide]
    assert record.session_id == resumed["session_id"], "the record follows the writer that lives"
    assert any("handed back to the session that wrote it" in h for h in history_of(client, tide))
    # A live writer counts against the number, however closed its Start is.
    assert board(client)["dial"]["running"] >= 1
    assert board(client)["dial"]["held"] == 0, "held means no process (ruling 7)"

    # The same refusal is never handed back twice.
    once = len(resumes(machine_floor))
    tick(client)
    assert len(resumes(machine_floor)) == once, "said once, not once a beat"

    # The writer rewrites the title and its turn ends: its record closes and
    # the seat reads the title it now stands behind.
    plan = repo / "docs" / "plans" / f"{STEM}.md"
    plan.write_text(plan.read_text(encoding="utf-8").replace(JARGON, PLAIN, 1), encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the title, rewritten")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    end_the_turn(resumed)
    tick(client)
    assert store.open_windowless_sessions("proj", SessionWork.PLANNING).get(tide) is None, (
        "its turn ended, so the writer is stopped and the title is read"
    )

    read_the_title(client, machine_floor, tide, "--title", "passes")
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "started", history_of(client, tide)[:3]
    assert column_of(client, tide) == "Executing"


def test_when_the_hour_runs_out_the_title_is_the_owners_and_the_lane_stays_planned(
    client: TestClient,
    machine_floor: Floor,
    repo: Path,
    store: Store,
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify_with_a_failing_title(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, JARGON)
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "planned"
    read_the_title(
        client, machine_floor, tide, "--title", "still the machinery", "--failed", "fix stage"
    )

    # The dial's hour is spent: nothing is handed back, and the card stands
    # Planned — never ended — so his own rewrite starts it (ruling 5).
    monkeypatch.setattr("api.dial.PLANNING_SECONDS", 0.0)
    before = len(resumes(machine_floor))
    tick(client)
    assert len(resumes(machine_floor)) == before, "the hour is spent: nothing is handed back"
    lane = store.fix_lanes("proj")[0]
    assert lane.stage.value == "planned"
    assert column_of(client, tide) == "Planned"
    # The card says the dial is finished with it, once, rather than leaving
    # its Start showing advice addressed to a writer that has gone.
    spent = [h for h in history_of(client, tide) if h.startswith("The dial has spent its hour")]
    assert len(spent) == 1 and "the title is yours to rewrite" in spent[0]
    tick(client)
    assert (
        len([h for h in history_of(client, tide) if h.startswith("The dial has spent its hour")])
        == 1
    ), "said once per spell, not once a beat"
    # And the Loop counts it: this is item 4's second shape.
    capsys.readouterr()
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "1\n"
    assert main(["fixes", "proj", "--stranded"]) == 0
    assert "the dial has spent its hour rewriting it" in capsys.readouterr().out

    # His rewrite, and a reading that passes, start it on the next beat with
    # nothing else touched.
    monkeypatch.setattr("api.dial.PLANNING_SECONDS", 3600.0)
    plan = repo / "docs" / "plans" / f"{STEM}.md"
    plan.write_text(plan.read_text(encoding="utf-8").replace(JARGON, PLAIN, 1), encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "his own title")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    read_the_title(client, machine_floor, tide, "--title", "passes")
    tick(client)
    assert store.fix_lanes("proj")[0].stage.value == "started"
    capsys.readouterr()
    assert main(["fixes", "all", "--stranded", "--count"]) == 0
    assert capsys.readouterr().out == "0\n", "a started card is nobody's strand"


def test_a_rewrite_never_buys_a_second_hour(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path, monkeypatch
):
    """Ruling 1: the hour bounds the rewrites together. A refusal arriving
    late in the hour is handed back, and the writer it resumes is held to
    what is left of the lane's hour — never to a fresh one of its own."""
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify_with_a_failing_title(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, JARGON)
    tick(client)
    read_the_title(
        client, machine_floor, tide, "--title", "still the machinery", "--failed", "fix stage"
    )
    tick(client)
    record = store.open_windowless_sessions("proj", SessionWork.PLANNING)[tide]
    fix = store.fix_lanes("proj")[0]
    assert record.started_at > fix.planning_started_at, "the writer was resumed later than the lane"

    # The lane's hour is up, though this record opened moments ago. The
    # writer is stopped on its own hour, not given a second one.
    monkeypatch.setattr("api.dial.PLANNING_SECONDS", 0.0)
    tick(client)
    assert store.open_windowless_sessions("proj", SessionWork.PLANNING).get(tide) is None, (
        "the record is held to what was left of the lane's hour"
    )
    assert store.fix_lanes("proj")[0].stage.value == "planned"


def test_a_card_whose_face_is_not_its_plans_title_is_his_at_once(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path
):
    """Ruling 8: the reading judges the card's face and the writer rewrites
    the document. Where the two cannot meet — an imported card, whose title
    the corpus read never rewrites (#150) — no rewrite can pass, so the card
    is the owner's at once instead of spending its hour."""
    turn(client, on=True, lanes=1)
    tide = number_of(client, TIDE)
    verify_with_a_failing_title(client, machine_floor, tide)
    a_planning_session(client, machine_floor, tide)
    push_a_plan(repo, tmp_path, TIDE_PATH, STEM, JARGON)
    make_imported(store, tide)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    tick(client)
    assert store.card("proj", tide).title == TIDE, "the face keeps the suggestion's title"
    read_the_title(
        client, machine_floor, tide, "--title", "the face says something else", "--failed", "lane"
    )
    before = len(resumes(machine_floor))
    tick(client)
    assert len(resumes(machine_floor)) == before, "nothing is handed back"
    assert store.open_windowless_sessions("proj", SessionWork.PLANNING).get(tide) is None
    said = [h for h in history_of(client, tide) if h.startswith("This card's face")]
    assert len(said) == 1 and "the title is yours to rewrite" in said[0]
    tick(client)
    assert len([h for h in history_of(client, tide) if h.startswith("This card's face")]) == 1
    assert store.fix_lanes("proj")[0].stage.value == "planned"
