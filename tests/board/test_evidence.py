"""Every machine-placed status names its evidence and doubts itself when it is
gone (plan 04, item 1): the predicate behind each machine column, asked again
on every read, pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.evidence import DOUBT, evidence_of, missing_fact, placement_from, standing_for
from board.lane import lane_for
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card, Place
from domain.column import Column
from domain.evidence import Evidence, EvidenceState
from domain.row import Row, RowKind
from domain.signal import Reading
from tests.board.test_lane import card, facts, session

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def placed(
    actor: Actor,
    to: Column,
    *,
    evidence: Evidence | None = None,
    kind: AuditKind = AuditKind.MOVED,
    id: int = 1,
) -> AuditEntry:
    return AuditEntry(
        id=id,
        at=NOW - timedelta(hours=1),
        actor=actor,
        kind=kind,
        card_number=7,
        from_place=None,
        to_place=Place(column=to, group=None, position=0),
        detail="placed",
        evidence=evidence,
    )


def reading(delivered: bool | None, words: str = "read") -> Reading:
    return Reading(
        id=1, card_number=7, at=NOW, delivered=delivered, words=words, actor=Actor.MACHINE
    )


def test_the_placement_is_the_newest_move_else_the_birth():
    born = placed(Actor.IMPORT, Column.EXECUTED, kind=AuditKind.BORN, id=1)
    row = AuditEntry(
        id=2,
        at=NOW,
        actor=Actor.SESSION,
        kind=AuditKind.ROW,
        card_number=7,
        from_place=None,
        to_place=None,
        detail="WATCH written: x",
    )
    moved = placed(Actor.MACHINE, Column.EXECUTING, evidence=Evidence.HANDS_ON, id=3)
    assert placement_from([row, born]) is born
    assert placement_from([moved, row, born]) is moved
    assert placement_from([]) is None


def test_the_owners_placement_is_trusted_and_never_tested():
    executing = card(column=Column.EXECUTING)
    standing = standing_for(executing, placed(Actor.OWNER, Column.EXECUTING), None, None, read=True)
    assert standing.state == EvidenceState.TRUSTED and standing.evidence is None
    assert evidence_of(executing, placed(Actor.OWNER, Column.EXECUTING)) == (Actor.OWNER, None)


def test_a_machine_placement_is_re_tested_against_the_predicate_it_named():
    executing = card(column=Column.EXECUTING)
    hands = placed(Actor.MACHINE, Column.EXECUTING, evidence=Evidence.HANDS_ON)
    live = lane_for(executing, facts(sessions=[session()]))
    assert standing_for(executing, hands, live, None, read=True).state == EvidenceState.HELD
    dead = lane_for(
        executing,
        facts(
            sessions=[session(pid=None)],
            deaths={
                "aaaa0001-0000-4000-8000-000000000000": "the journal says: Killed process 4242"
            },
        ),
    )
    doubted = standing_for(executing, hands, dead, None, read=True)
    assert doubted.state == EvidenceState.DOUBTED
    assert doubted.words == (
        DOUBT + "no live session has hands on its worktree (the journal says: Killed process 4242)"
    )
    nothing = lane_for(executing, facts(worktrees={}))
    assert "no lane exists for it" in (
        standing_for(executing, hands, nothing, None, read=True).words or ""
    )
    assert standing_for(executing, hands, None, None, read=True).state == EvidenceState.DOUBTED


def test_executed_rests_on_the_archive_the_delivered_row_and_a_readable_signal():
    landed = placed(Actor.MACHINE, Column.EXECUTED, evidence=Evidence.CLOSE_LANDED)
    whole = card(
        column=Column.EXECUTED,
        archived=True,
        rows=[
            Row(kind=RowKind.DELIVERED, text="d"),
            Row(kind=RowKind.WATCH, text="x — owner by 2026-09-30"),
        ],
    )
    assert missing_fact(Evidence.CLOSE_LANDED, whole, None, None) is None
    live_plan = card(column=Column.EXECUTED, rows=whole.rows)
    assert missing_fact(Evidence.CLOSE_LANDED, live_plan, None, None) == (
        "its plan is not archived (docs/plans/p.md is live)"
    )
    bare = card(column=Column.EXECUTED, archived=True)
    words = missing_fact(Evidence.CLOSE_LANDED, bare, None, None) or ""
    assert "no DELIVERED row is written" in words and "names no signal the board can read" in words
    note = Card(**{**bare.model_dump(), "link": None})
    assert "no plan or suggestion is written behind it" in (
        missing_fact(Evidence.CLOSE_LANDED, note, None, None) or ""
    )
    assert standing_for(whole, landed, None, None, read=True).state == EvidenceState.HELD


def test_done_and_decision_moment_rest_on_the_last_reading():
    assert missing_fact(Evidence.SIGNAL_DELIVERED, card(), None, reading(True)) is None
    assert missing_fact(Evidence.SIGNAL_DELIVERED, card(), None, None) == (
        "no reading of its signal has been made"
    )
    assert missing_fact(Evidence.SIGNAL_DELIVERED, card(), None, reading(False, "404")) == (
        "the last reading did not say delivered: 404"
    )
    assert missing_fact(Evidence.SIGNAL_FAILED, card(), None, reading(None)) is None
    assert "says delivered" in (
        missing_fact(Evidence.SIGNAL_FAILED, card(), None, reading(True, "ok")) or ""
    )


def test_a_lane_that_ended_is_doubted_the_moment_hands_are_on_it_again():
    back = card(column=Column.UP_NEXT)
    ended = placed(Actor.MACHINE, Column.UP_NEXT, evidence=Evidence.LANE_ENDED)
    quiet = lane_for(back, facts(sessions=[session(pid=None)]))
    assert standing_for(back, ended, quiet, None, read=True).state == EvidenceState.HELD
    busy = lane_for(back, facts(sessions=[session()]))
    assert "hands on it again" in (standing_for(back, ended, busy, None, read=True).words or "")


def test_the_imports_placements_are_evidence_unknown_until_the_first_read_then_tested():
    """0.1's word is not evidence: card #223 sat in Executing on it. Executing
    and Executed are tested by their column's predicate; Done and Decision
    moment were the owner's moves in 0.1's grammar and are trusted."""
    executed = card(column=Column.EXECUTED, archived=True)
    born = placed(Actor.IMPORT, Column.EXECUTED, kind=AuditKind.BORN)
    before = standing_for(executed, born, None, None, read=False)
    assert before.state == EvidenceState.UNKNOWN and before.evidence == Evidence.CLOSE_LANDED
    assert before.words == "imported from Needle 0.1; evidence unknown until the first read"
    after = standing_for(executed, born, lane_for(executed, facts(worktrees={})), None, read=True)
    assert after.state == EvidenceState.DOUBTED and "no DELIVERED row" in (after.words or "")
    done = card(column=Column.DONE, archived=True)
    trusted = standing_for(
        done, placed(Actor.IMPORT, Column.DONE, kind=AuditKind.BORN), None, None, read=True
    )
    assert trusted.state == EvidenceState.TRUSTED and trusted.actor == Actor.IMPORT
    ruling = card(column=Column.DECISION_MOMENT)
    assert (
        standing_for(
            ruling,
            placed(Actor.IMPORT, Column.DECISION_MOMENT, kind=AuditKind.BORN),
            None,
            None,
            read=True,
        ).state
        == EvidenceState.TRUSTED
    )


def test_a_sessions_close_into_executed_rests_on_the_same_predicate_as_the_machines():
    closed = card(
        column=Column.EXECUTED,
        archived=True,
        rows=[
            Row(kind=RowKind.DELIVERED, text="d"),
            Row(kind=RowKind.WATCH, text="x — file docs/plans/done/p.md by 2026-09-30"),
        ],
    )
    by_session = placed(Actor.SESSION, Column.EXECUTED)
    assert evidence_of(closed, by_session) == (Actor.SESSION, Evidence.CLOSE_LANDED)
    assert standing_for(closed, by_session, None, None, read=True).state == EvidenceState.HELD
    elsewhere = placed(Actor.SESSION, Column.DECISION_MOMENT)
    assert evidence_of(card(column=Column.DECISION_MOMENT), elsewhere) == (Actor.SESSION, None)


def test_a_machine_row_written_before_the_predicate_was_recorded_is_tested_by_its_column():
    """The rows the board wrote before plan 04 name no evidence; the column says
    what they rest on, so the first read after the fold tests them too."""
    executing = card(column=Column.EXECUTING)
    unnamed = placed(Actor.MACHINE, Column.EXECUTING)
    assert evidence_of(executing, unnamed) == (Actor.MACHINE, Evidence.HANDS_ON)
    before = standing_for(executing, unnamed, None, None, read=False)
    assert before.state == EvidenceState.UNKNOWN
    assert before.words == "not tested yet: the loop has not read the machine"


def test_nothing_governs_a_planned_card():
    planned = card(column=Column.PLANNED)
    assert evidence_of(planned, placed(Actor.CORPUS, Column.PLANNED, kind=AuditKind.BORN)) == (
        Actor.CORPUS,
        None,
    )
    assert standing_for(planned, None, None, None, read=True).state == EvidenceState.TRUSTED
