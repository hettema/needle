"""The store's part of the doors and the loops: rows written back, the
machine's moves with their reasons, the Executed guard, and the records of
what sessions push (plan 03, items 2, 3 and 5)."""

from datetime import timedelta
from pathlib import Path

import pytest

from board.import_01 import read_01
from board.reconcile import Born, Effects
from domain.audit import AuditKind
from domain.board import TrunkState
from domain.card import Actor, CardOrigin, Place
from domain.column import Column
from domain.document import DocumentKind, DocumentRef
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


def test_a_ruling_on_a_verdict_is_one_act_the_row_the_move_and_the_owners_name(board: Store):
    """Accepting moves the card by the machine with the verdict's reason on the
    history row and the owner named; overturning keeps it with his word; a
    verdict that stays on a doubted card re-places it by his hand (plan 05)."""
    verdict = "superseded — a later plan carries it → Not now"
    board.add_row("proj", 228, Row(kind=RowKind.VERDICT, text=verdict), Actor.SESSION, NOW)
    with pytest.raises(StoreRefusal, match="carries no verdict"):
        board.rule_on_verdict(
            "proj", 253, NOW, accepted=True, word=None, to=None, replace=False, said="x"
        )
    card = board.rule_on_verdict(
        "proj",
        228,
        NOW + timedelta(minutes=1),
        accepted=True,
        word=None,
        to=Place(column=Column.NOT_NOW, group=None, position=0),
        replace=False,
        said="accepted the verdict: superseded — a later plan carries it",
    )
    assert card.place.column == Column.NOT_NOW
    assert [r.kind for r in card.rows if r.kind in (RowKind.VERDICT, RowKind.RULED)] == [
        RowKind.RULED
    ]
    assert next(r.text for r in card.rows if r.kind == RowKind.RULED) == f"accepted: {verdict}"
    history = board.history("proj", 228)
    moved = next(h for h in history if h.kind == AuditKind.MOVED)
    assert moved.actor == Actor.OWNER and moved.evidence is None
    assert moved.detail.endswith("— accepted the verdict: superseded — a later plan carries it")
    assert any(
        h.kind == AuditKind.ROW and h.detail == f"VERDICT accepted: {verdict}" for h in history
    )

    stays = "live and open — waits on a client → stays"
    board.add_row("proj", 241, Row(kind=RowKind.VERDICT, text=stays), Actor.SESSION, NOW)
    card = board.rule_on_verdict(
        "proj",
        241,
        NOW,
        accepted=False,
        word="not a client wait, a design wait",
        to=None,
        replace=False,
        said="overturned the verdict: not a client wait, a design wait",
    )
    assert card.place.column == Column.UP_NEXT
    ruled = next(r.text for r in card.rows if r.kind == RowKind.RULED)
    assert ruled == f"overturned: not a client wait, a design wait — the verdict read: {stays}"
    assert not any(h.kind == AuditKind.MOVED for h in board.history("proj", 241))

    doubted = "doubted — no lane exists for it → stays"
    board.add_row("proj", 259, Row(kind=RowKind.VERDICT, text=doubted), Actor.MACHINE, NOW)
    before = board.card("proj", 259)
    assert before is not None
    card = board.rule_on_verdict(
        "proj",
        259,
        NOW,
        accepted=True,
        word=None,
        to=None,
        replace=True,
        said="accepted the verdict: doubted — no lane exists for it",
    )
    assert card.place == before.place
    kept = board.placements("proj")[259]
    assert kept.actor == Actor.OWNER and kept.from_place == kept.to_place == before.place
    assert kept.detail.startswith("Kept in Executing — accepted the verdict")


# ── plan 07: the watercooler, and a conversation about no card yet ─────


def test_the_watercooler_keeps_every_line_in_order_and_a_discussion_may_be_about_no_card(
    board: Store,
):
    later = NOW + timedelta(minutes=3)
    said = board.say("proj", 253, Actor.SESSION, NOW, "  touching engine/metering.py; leave it  ")
    assert said.card_number == 253 and said.text == "touching engine/metering.py; leave it"
    board.say("proj", None, Actor.MACHINE, later, "#253 folded over #241's edits in engine/x.py")
    lines = board.watercooler("proj")
    assert [(ln.card_number, ln.actor) for ln in lines] == [
        (253, Actor.SESSION),
        (None, Actor.MACHINE),
    ]
    assert [ln.text for ln in board.watercooler("proj", limit=1)] == [
        "#253 folded over #241's edits in engine/x.py"
    ]
    with pytest.raises(StoreRefusal, match="must say something"):
        board.say("proj", 253, Actor.SESSION, NOW, "   ")
    with pytest.raises(StoreRefusal, match="no card #999"):
        board.say("proj", 999, Actor.SESSION, NOW, "x")
    with pytest.raises(StoreRefusal, match='No project "nope"'):
        board.say("nope", None, Actor.MACHINE, NOW, "x")

    idea = board.record_discussion(
        "proj", None, "a1b2c3d4-0000-4000-8000-000000000000", "alpha", NOW
    )
    assert idea.card_number is None
    assert [d.card_number for d in board.discussions("proj")] == [None]


def test_a_document_naming_its_conversation_is_born_from_it(board: Store):
    board.record_discussion("proj", None, "a1b2c3d4-0000-4000-8000-000000000000", "beta", NOW)

    def born(stem: str, found_by: str | None) -> Effects:
        return Effects(
            renamed=[],
            relinked=[],
            archived=[],
            born=[
                Born(
                    document=DocumentRef(
                        kind=DocumentKind.SUGGESTION,
                        stem=stem,
                        path=f"docs/slice-suggestions/{stem}.md",
                        title=stem,
                    ),
                    column=Column.BACKLOG,
                    found_by=found_by,
                )
            ],
        )

    later = NOW + timedelta(hours=2)
    from_idea = board.apply_effects(
        "proj",
        born(
            "from-the-door",
            "the owner, from the board's Idea door on 2026-09-03 (conversation a1b2c3d4)",
        ),
        origin=CardOrigin.ARRIVED,
        at=later,
    )[0]
    assert board.history("proj", from_idea)[0].detail == (
        "Born from docs/slice-suggestions/from-the-door.md, after registration. Born from a "
        "conversation on 2026-09-03 (a1b2c3d4 on beta, from the Idea door)."
    )
    by_hand = board.apply_effects(
        "proj", born("by-hand", "the owner, 2026-09-03"), origin=CardOrigin.ARRIVED, at=later
    )[0]
    assert board.history("proj", by_hand)[0].detail == (
        "Born from docs/slice-suggestions/by-hand.md, after registration."
    )
    unknown = board.apply_effects(
        "proj",
        born("unknown", "a review (conversation deadbeef)"),
        origin=CardOrigin.ARRIVED,
        at=later,
    )[0]
    assert "conversation" not in board.history("proj", unknown)[0].detail, (
        "a conversation the board never opened is not claimed"
    )
