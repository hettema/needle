"""The store's part of the doors and the loops: rows written back, the
machine's moves with their reasons, the Executed guard, and the records of
what sessions push (plan 03, items 2, 3 and 5)."""

from datetime import timedelta
from pathlib import Path

import pytest

from board.import_01 import read_01
from domain.audit import AuditKind
from domain.board import TrunkState
from domain.card import Actor, Place
from domain.column import Column
from domain.evidence import Evidence
from domain.hook import HookKind, HookPosted
from domain.lane import LaneRecord
from domain.project import Project
from domain.row import Row, RowKind
from infrastructure.corpus import scan
from infrastructure.store import Store, StoreRefusal
from tests.conftest import NOW


@pytest.fixture
def board(store: Store, project: Project, card_file_01: dict[str, object]) -> Store:
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    return store


def test_a_row_is_written_with_its_audit_row_and_a_record_row_is_one_per_card(board: Store):
    later = NOW + timedelta(minutes=1)
    card = board.add_row(
        "proj", 253, Row(kind=RowKind.WAITS, text="the deploy"), Actor.SESSION, NOW
    )
    assert [r.kind for r in card.rows][-1] == RowKind.WAITS
    board.add_row("proj", 253, Row(kind=RowKind.DELIVERED, text="first"), Actor.SESSION, NOW)
    card = board.add_row(
        "proj", 253, Row(kind=RowKind.DELIVERED, text="second"), Actor.SESSION, later
    )
    delivered = [r.text for r in card.rows if r.kind == RowKind.DELIVERED]
    assert delivered == ["second"], "DELIVERED is one per card; the second write replaces the first"
    waits = [r.text for r in card.rows if r.kind == RowKind.WAITS]
    board.add_row("proj", 253, Row(kind=RowKind.WAITS, text="another"), Actor.SESSION, later)
    assert (
        len([r for r in board.card("proj", 253).rows if r.kind == RowKind.WAITS]) == len(waits) + 1
    )
    details = [h.detail for h in board.history("proj", 253) if h.kind == AuditKind.ROW]
    assert details[0] == "WAITS written: another"
    assert "DELIVERED rewritten: second — it read: first" in details, (
        "a rewrite keeps the whole previous text in the history"
    )
    assert "DELIVERED written: first" in details
    with pytest.raises(StoreRefusal, match="no card #999"):
        board.add_row("proj", 999, Row(kind=RowKind.WAITS, text="x"), Actor.SESSION, NOW)


def test_a_machine_move_must_say_why_and_name_its_evidence_and_both_are_in_the_history(
    board: Store,
):
    to = Place(column=Column.EXECUTING, group=None, position=0)
    with pytest.raises(StoreRefusal, match="must say why"):
        board.move("proj", 253, to, Actor.MACHINE, NOW)
    with pytest.raises(StoreRefusal, match="must name the evidence"):
        board.move("proj", 253, to, Actor.MACHINE, NOW, detail="hands on: abcd1234 on alpha")
    board.move(
        "proj",
        253,
        to,
        Actor.MACHINE,
        NOW,
        detail="hands on: abcd1234 on alpha",
        evidence=Evidence.HANDS_ON,
    )
    moved = board.history("proj", 253)[0]
    assert moved.actor == Actor.MACHINE and moved.kind == AuditKind.MOVED
    assert moved.detail == "Moved Up next → Executing — hands on: abcd1234 on alpha"
    assert moved.evidence == Evidence.HANDS_ON
    assert board.placements("proj")[253].id == moved.id
    owner = board.move(
        "proj", 253, Place(column=Column.UP_NEXT, group=None, position=0), Actor.OWNER, NOW
    )
    assert owner.place.column == Column.UP_NEXT
    placed = board.placements("proj")[253]
    assert placed.actor == Actor.OWNER and placed.evidence is None


def test_executed_needs_a_watch_row_naming_a_signal_whoever_moves_the_card(board: Store):
    to = Place(column=Column.EXECUTED, group=None, position=0)
    with pytest.raises(StoreRefusal, match="cannot enter Executed: no WATCH row names a signal"):
        board.move("proj", 253, to, Actor.OWNER, NOW)
    board.add_row(
        "proj", 253, Row(kind=RowKind.WATCH, text="what reality has to confirm"), Actor.SESSION, NOW
    )
    with pytest.raises(StoreRefusal, match="names no reader"):
        board.move(
            "proj",
            253,
            to,
            Actor.MACHINE,
            NOW,
            detail="the close landed",
            evidence=Evidence.CLOSE_LANDED,
        )
    board.add_row(
        "proj",
        253,
        Row(kind=RowKind.WATCH, text="the invoice arrived — owner by 2026-09-30"),
        Actor.SESSION,
        NOW,
    )
    card = board.move(
        "proj",
        253,
        to,
        Actor.MACHINE,
        NOW,
        detail="the close landed",
        evidence=Evidence.CLOSE_LANDED,
    )
    assert card.place.column == Column.EXECUTED


def test_a_note_is_an_audit_row_that_moves_nothing(board: Store):
    board.note("proj", 253, AuditKind.STARTED, Actor.OWNER, NOW, "Started abcd1234 on alpha")
    entry = board.history("proj", 253)[0]
    assert entry.kind == AuditKind.STARTED and entry.from_place is None and entry.to_place is None
    assert board.card("proj", 253).place.column == Column.UP_NEXT
    with pytest.raises(StoreRefusal, match="must say something"):
        board.note("proj", 253, AuditKind.STARTED, Actor.OWNER, NOW, "")


def test_hook_events_are_kept_as_posted_and_attributed_as_told(board: Store):
    posted = HookPosted(
        kind=HookKind.STOP,
        session_id="aaaa0001-0000-4000-8000-000000000000",
        cwd="/srv/p/.claude/worktrees/card-253-x",
        at=NOW,
        source=None,
        message="Which one?",
        reason=None,
        error=None,
        transcript_path="/t.jsonl",
    )
    elsewhere = posted.model_copy(
        update={"cwd": "/elsewhere", "session_id": "bbbb0001-0000-4000-8000-000000000000"}
    )
    recorded = board.record_hook_events([(posted, "proj", 253), (elsewhere, None, None)])
    assert [(e.project, e.card_number) for e in recorded] == [("proj", 253), (None, None)]
    assert [e.message for e in board.hook_events("proj", 253)] == ["Which one?"]
    assert board.hook_events("proj") == board.hook_events("proj", 253)
    assert len(board.hook_events_of_session("bbbb0001-0000-4000-8000-000000000000")) == 1


def test_discussions_lanes_readings_and_the_trunk_round_trip(board: Store):
    talk = board.record_discussion(
        "proj", 253, "dddd0001-0000-4000-8000-000000000000", "alpha", NOW
    )
    assert board.discussions("proj") == [talk]

    record = LaneRecord(
        project="proj",
        card_number=253,
        name="card-253-x",
        path="/srv/p/.claude/worktrees/card-253-x",
        branch="card-253-x",
        birth=None,
        tip=None,
        first_seen=NOW,
        last_seen=NOW,
        gone_at=None,
        folded_at=None,
        trunk_synced_at=None,
        main_synced_at=None,
    )
    board.record_lane(record)
    board.record_lane(record.model_copy(update={"tip": "abc", "folded_at": NOW}))
    kept = board.lane("proj", 253)
    assert kept is not None and kept.tip == "abc" and kept.folded_at == NOW
    assert [r.card_number for r in board.lanes("proj")] == [253]
    board.forget_lane("proj", 253)
    assert board.lane("proj", 253) is None

    reading = board.record_reading("proj", 253, NOW, False, "answered 503", Actor.MACHINE)
    board.record_reading("proj", 253, NOW + timedelta(hours=1), True, "answered 200", Actor.MACHINE)
    assert [r.delivered for r in board.readings("proj", 253)] == [True, False]
    assert board.last_readings("proj")[253].delivered is True and reading.delivered is False
    assert board.history("proj", 253)[0].detail == "Signal read as delivered: answered 200"

    assert board.trunk("proj") == TrunkState(level=None, behind=0, note=None, read_at=None)
    board.record_trunk("proj", TrunkState(level=False, behind=3, note="dirty", read_at=NOW))
    assert board.trunk("proj").behind == 3 and board.trunk("proj").note == "dirty"
