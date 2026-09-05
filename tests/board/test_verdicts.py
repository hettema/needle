"""The VERDICT row's grammar, and the classes the board's own facts settle
(plan 05, item 1)."""

from datetime import UTC, date, datetime

import pytest

from board.verdicts import (
    GRAMMAR,
    STALE_PLAN_DAYS,
    VerdictUnreadable,
    machine_verdict,
    parse_verdict,
    read_or_decline,
    render_verdict,
)
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.document import Document, DocumentKind
from domain.evidence import Evidence, EvidenceState, Standing
from domain.row import Row, RowKind
from domain.signal import Reading, Signal, SignalKind
from domain.verdict import EvidenceClass, Verdict

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def test_the_seven_classes_parse_with_their_evidence_and_landing():
    verdict = parse_verdict(
        "built under another name — docs/plans/done/2026-06-11-01-platform-foundation-"
        "generalization.md closes it by name → Done"
    )
    assert verdict.evidence_class == EvidenceClass.BUILT_UNDER_ANOTHER_NAME
    assert verdict.evidence.startswith("docs/plans/done/2026-06-11-01")
    assert verdict.to == Column.DONE
    stays = parse_verdict("live and open — waits on a signed online-shop client -> stays")
    assert stays.evidence_class == EvidenceClass.LIVE_AND_OPEN and stays.to is None
    parked = parse_verdict("Superseded: card #263 carries the same intent as a plan → Not now")
    assert parked.evidence_class == EvidenceClass.SUPERSEDED and parked.to == Column.NOT_NOW
    # The evidence may carry arrows and dashes of its own; the last arrow is the landing.
    nested = parse_verdict("doubted — the lane ended → no worktree on disk → Decision moment")
    assert nested.evidence == "the lane ended → no worktree on disk"
    assert nested.to == Column.DECISION_MOMENT


def test_what_is_missing_is_named_with_the_grammar():
    with pytest.raises(VerdictUnreadable, match="names no class") as no_class:
        parse_verdict("probably done — looks shipped → Done")
    assert GRAMMAR in str(no_class.value)
    with pytest.raises(VerdictUnreadable, match="names no landing"):
        parse_verdict("superseded — by a later plan")
    with pytest.raises(VerdictUnreadable, match="no column and not `stays`"):
        parse_verdict("superseded — by a later plan → Elsewhere")
    with pytest.raises(VerdictUnreadable, match="carries no evidence"):
        parse_verdict("superseded → Not now")
    with pytest.raises(VerdictUnreadable, match="live and open stays"):
        parse_verdict("live and open — no reason → Done")
    verdict, why = read_or_decline(None)
    assert verdict is None and why == "no VERDICT row is written"


def test_the_rendered_row_reads_back_as_the_same_verdict():
    for verdict in (
        Verdict(
            evidence_class=EvidenceClass.STALE_PLAN, evidence="80 days", to=Column.DECISION_MOMENT
        ),
        Verdict(evidence_class=EvidenceClass.LIVE_AND_OPEN, evidence="waits on #144", to=None),
    ):
        assert parse_verdict(render_verdict(verdict)) == verdict


def _card(
    column: Column, *, archived: bool, rows: list[Row], born: date = date(2026, 9, 3)
) -> Card:
    return Card(
        number=1,
        project="p",
        place=Place(column=column, group=None, position=0),
        title="A card",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="A card", archived=archived),
        origin=CardOrigin.IMPORTED,
        born_at=datetime(born.year, born.month, born.day, tzinfo=UTC),
        rows=rows,
    )


def _plan(day: date, *, archived: bool = False) -> Document:
    return Document(
        kind=DocumentKind.PLAN,
        stem="p1",
        path=f"docs/plans/{'done/' if archived else ''}p1.md",
        archived=archived,
        title="A card",
        date=day,
        status=None,
        status_word=None,
        gate=None,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=None,
        suggestion_kind=None,
        cites=[],
        handouts=[],
        items=[],
        head_fields=[],
        intent_heading=None,
        intent="",
        essence=None,
        read_at=NOW,
    )


HELD = Standing(
    actor=Actor.MACHINE, evidence=Evidence.CLOSE_LANDED, state=EvidenceState.HELD, words=None
)
TRUSTED = Standing(actor=Actor.OWNER, evidence=None, state=EvidenceState.TRUSTED, words=None)
DELIVERED = Row(kind=RowKind.DELIVERED, text="shipped")
OWNER_SIGNAL = Signal(
    what="Did it land?",
    kind=SignalKind.OWNER,
    target="Did it land?",
    expect=None,
    due=date(2026, 9, 11),
    every_hours=24,
)


def test_a_shipped_card_whose_signal_read_delivered_goes_to_done():
    card = _card(Column.EXECUTED, archived=True, rows=[DELIVERED])
    last = Reading(id=1, card_number=1, at=NOW, delivered=True, words="2 of 2", actor=Actor.MACHINE)
    verdict = machine_verdict(
        card,
        HELD,
        _plan(date(2026, 9, 1), archived=True),
        None,
        last,
        ever_had_a_lane=True,
        now=NOW,
    )
    assert verdict is not None
    assert verdict.evidence_class == EvidenceClass.SHIPPED_SIGNAL_READ and verdict.to == Column.DONE
    assert "2 of 2" in verdict.evidence


def test_a_shipped_card_whose_signal_only_the_owner_reads_stays_with_its_question():
    card = _card(Column.EXECUTED, archived=True, rows=[DELIVERED])
    verdict = machine_verdict(card, HELD, None, OWNER_SIGNAL, None, ever_had_a_lane=True, now=NOW)
    assert verdict is not None
    assert verdict.evidence_class == EvidenceClass.SHIPPED_OWNER_ONLY and verdict.to is None
    assert "due 2026-09-11" in verdict.evidence
    # A machine-readable signal still being read is nothing the board can rule on.
    command = OWNER_SIGNAL.model_copy(update={"kind": SignalKind.COMMAND, "target": "ls"})
    not_yet = Reading(
        id=1, card_number=1, at=NOW, delivered=False, words="2 of 3", actor=Actor.MACHINE
    )
    assert (
        machine_verdict(card, HELD, None, command, not_yet, ever_had_a_lane=True, now=NOW) is None
    )


def test_a_doubted_placement_carries_the_missing_fact_and_goes_to_decision_moment():
    card = _card(Column.EXECUTED, archived=False, rows=[DELIVERED])
    doubted = Standing(
        actor=Actor.IMPORT,
        evidence=Evidence.CLOSE_LANDED,
        state=EvidenceState.DOUBTED,
        words="the board doubts this: its plan is not archived (docs/plans/p1.md is live)",
    )
    verdict = machine_verdict(
        card, doubted, _plan(date(2026, 9, 1)), OWNER_SIGNAL, None, ever_had_a_lane=False, now=NOW
    )
    assert verdict is not None
    assert verdict.evidence_class == EvidenceClass.DOUBTED and verdict.to == Column.DECISION_MOMENT
    assert verdict.evidence == "its plan is not archived (docs/plans/p1.md is live)"


def test_a_plan_older_than_the_stated_age_with_no_lane_ever_is_stale():
    old = date(2026, 9, 4).toordinal() - STALE_PLAN_DAYS
    card = _card(Column.PLANNED, archived=False, rows=[])
    verdict = machine_verdict(
        card, TRUSTED, _plan(date.fromordinal(old)), None, None, ever_had_a_lane=False, now=NOW
    )
    assert verdict is not None
    assert (
        verdict.evidence_class == EvidenceClass.STALE_PLAN and verdict.to == Column.DECISION_MOMENT
    )
    assert f"{STALE_PLAN_DAYS} days old" in verdict.evidence and "still true?" in verdict.evidence
    # A day younger, or a lane that once existed, and the corpus decides.
    younger = _plan(date.fromordinal(old + 1))
    assert (
        machine_verdict(card, TRUSTED, younger, None, None, ever_had_a_lane=False, now=NOW) is None
    )
    assert (
        machine_verdict(
            card, TRUSTED, _plan(date.fromordinal(old)), None, None, ever_had_a_lane=True, now=NOW
        )
        is None
    )


def test_a_closed_card_and_a_live_suggestion_get_no_machine_verdict():
    done = _card(Column.DONE, archived=True, rows=[DELIVERED])
    assert (
        machine_verdict(done, HELD, None, OWNER_SIGNAL, None, ever_had_a_lane=True, now=NOW) is None
    )
    backlog = _card(Column.BACKLOG, archived=False, rows=[])
    assert (
        machine_verdict(backlog, TRUSTED, None, None, None, ever_had_a_lane=False, now=NOW) is None
    )
