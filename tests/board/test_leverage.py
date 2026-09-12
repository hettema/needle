"""The board as the focus would arrange it (card #87, item 5): one rule,
one test. A helps-remove plan into Up next by likelihood then cost; a
does-not-address card out of Up next with a readable wake trigger; a
Backlog defect never into Up next; Executed and Decision moment ordered
but never moved; protects after helps-remove; ties keep his rank; an
unticked move not proposed again until its ground changes; a paused or
missing focus orders nothing."""

from datetime import UTC, datetime, timedelta

from board.leverage import Judged, arrange, wake_line
from board.moves import GroupLayout
from board.signals import parse_watch
from domain.card import Place
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.focus import CardLeverage, Decline, Leverage, LeverageState, Likelihood
from domain.gate import Gate
from domain.meaning import Meaning, say

NOW = datetime(2026, 9, 9, tzinfo=UTC)
FOCUS = "f0cu5"


def _read(leverage: Leverage, likelihood: Likelihood | None = None) -> CardLeverage:
    return CardLeverage(
        state=LeverageState.READ,
        leverage=leverage,
        likelihood=likelihood,
        words="why",
        sentence=say(Meaning.QUIET, f"it {leverage.value}"),
        hold=None,
        read_at=NOW,
    )


def _unread() -> CardLeverage:
    return CardLeverage(
        state=LeverageState.UNREAD,
        leverage=None,
        likelihood=None,
        words=None,
        sentence=say(Meaning.QUIET, "unread"),
        hold=None,
        read_at=None,
    )


def _card(
    number: int,
    column: Column,
    position: int,
    *,
    leverage: CardLeverage | None = None,
    gate: Gate | None = Gate.HIGH,
    kind: DocumentKind = DocumentKind.PLAN,
    suggestion_kind: SuggestionKind | None = None,
    group: str | None = None,
    unblocks: int = 0,
    owner_signal: bool = False,
    last_read: datetime | None = None,
) -> Judged:
    return Judged(
        number=number,
        place=Place(column=column, group=group, position=position),
        gate=gate,
        kind=kind,
        suggestion_kind=suggestion_kind,
        document_fingerprint=f"doc{number}",
        leverage=leverage,
        unblocks=unblocks,
        owner_signal=owner_signal,
        last_read=last_read,
    )


def _layout(judged: dict[int, Judged]) -> list[GroupLayout]:
    groups: dict[tuple[Column, str | None], list[int]] = {}
    for card in sorted(judged.values(), key=lambda c: c.place.position):
        groups.setdefault((card.place.column, card.place.group), []).append(card.number)
    return [
        GroupLayout(column=column, name=name, numbers=numbers)
        for (column, name), numbers in groups.items()
    ]


def _arrange(judged: dict[int, Judged], **changes):
    fields = dict(
        focus_fingerprint=FOCUS,
        declines=[],
        wake="WATCH: wake when the focus is checked again — session x by 2026-10-15",
        available=True,
        why=None,
    )
    fields.update(changes)
    return arrange(_layout(judged), judged, **fields)


def _column(arrangement, column: Column) -> list[int]:
    found = next(c for c in arrangement.columns if c.column == column)
    return [n for g in found.groups for n in g.numbers]


def test_a_planned_card_that_helps_remove_the_limit_is_shown_in_up_next_by_likelihood_then_cost():
    judged = {
        1: _card(1, Column.UP_NEXT, 0, leverage=_read(Leverage.PROTECTS)),
        2: _card(
            2,
            Column.PLANNED,
            0,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.MEDIUM),
            gate=Gate.LOW,
        ),
        3: _card(
            3,
            Column.PLANNED,
            1,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH),
            gate=Gate.XHIGH,
        ),
        4: _card(
            4,
            Column.PLANNED,
            2,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH),
            gate=Gate.LOW,
        ),
        5: _card(5, Column.PLANNED, 3, leverage=_read(Leverage.DOES_NOT_ADDRESS)),
    }
    arranged = _arrange(judged)
    assert arranged.available
    assert _column(arranged, Column.UP_NEXT) == [4, 3, 2, 1], (
        "high likelihood first, the cheaper of two highs first, then medium, then protects"
    )
    assert _column(arranged, Column.PLANNED) == [5]
    moves = {m.number: m for m in arranged.moves}
    assert set(moves) == {2, 3, 4}
    assert moves[4].to_place == Place(column=Column.UP_NEXT, group=None, position=0)
    assert moves[3].to_place.position == 1 and moves[2].to_place.position == 2
    assert moves[4].from_place == Place(column=Column.PLANNED, group=None, position=2)
    assert moves[4].why.startswith("helps remove this limit, high likelihood")
    assert moves[4].wake is None


def test_a_card_in_up_next_that_does_not_address_the_limit_goes_to_not_now_with_a_readable_wake():
    judged = {
        1: _card(1, Column.UP_NEXT, 0, leverage=_read(Leverage.DOES_NOT_ADDRESS)),
        2: _card(2, Column.UP_NEXT, 1, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.LOW)),
        3: _card(3, Column.NOT_NOW, 0, leverage=_read(Leverage.PROTECTS)),
    }
    arranged = _arrange(judged)
    assert _column(arranged, Column.UP_NEXT) == [2]
    assert _column(arranged, Column.NOT_NOW) == [3, 1]
    move = next(m for m in arranged.moves if m.number == 1)
    assert move.to_place.column == Column.NOT_NOW and move.wake is not None
    signal = parse_watch(move.wake)
    assert signal.kind.value == "session" and signal.due.isoformat() == "2026-10-15"
    line = wake_line("the diagnosis is read again", "session harbourmaster by 2026-10-15")
    assert (
        line == "WATCH: wake when the diagnosis is read again — session harbourmaster by 2026-10-15"
    )
    assert parse_watch(line).what == "WATCH: wake when the diagnosis is read again"


def test_a_defect_that_helps_remove_the_limit_is_never_moved_into_up_next():
    judged = {
        1: _card(
            1,
            Column.DEFECTS,
            0,
            kind=DocumentKind.SUGGESTION,
            suggestion_kind=SuggestionKind.DEFECT,
            gate=None,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH),
        ),
        2: _card(
            2,
            Column.DEFECTS,
            1,
            kind=DocumentKind.SUGGESTION,
            suggestion_kind=SuggestionKind.DEFECT,
            gate=None,
            leverage=_read(Leverage.PROTECTS),
        ),
        3: _card(3, Column.UP_NEXT, 0, leverage=_read(Leverage.PROTECTS)),
    }
    arranged = _arrange(judged)
    assert arranged.moves == []
    assert _column(arranged, Column.DEFECTS) == [1, 2] and _column(arranged, Column.UP_NEXT) == [3]
    defects = next(c for c in arranged.columns if c.column == Column.DEFECTS).groups[0]
    assert defects.name is None


def test_a_parked_plan_that_helps_remove_the_limit_comes_forward_and_a_parked_defect_to_defects():
    judged = {
        1: _card(1, Column.NOT_NOW, 0, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH)),
        2: _card(
            2,
            Column.NOT_NOW,
            1,
            kind=DocumentKind.SUGGESTION,
            suggestion_kind=SuggestionKind.DEFECT,
            gate=None,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.LOW),
        ),
        3: _card(3, Column.UP_NEXT, 0, leverage=_read(Leverage.PROTECTS)),
    }
    arranged = _arrange(judged)
    assert _column(arranged, Column.UP_NEXT) == [1, 3]
    defects = next(c for c in arranged.columns if c.column == Column.DEFECTS)
    assert defects.groups == [
        defects.groups[0].__class__(name=None, numbers=[2])
    ], "a Defects column with no group gets one for the defect that returns"
    assert {m.number: m.to_place.column for m in arranged.moves} == {
        1: Column.UP_NEXT,
        2: Column.DEFECTS,
    }


def test_executed_and_decision_moment_are_ordered_but_never_moved():
    judged = {
        1: _card(
            1,
            Column.EXECUTED,
            0,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH),
            last_read=NOW,
        ),
        2: _card(
            2, Column.EXECUTED, 1, leverage=_read(Leverage.DOES_NOT_ADDRESS), owner_signal=True
        ),
        3: _card(3, Column.EXECUTED, 2, leverage=_unread(), last_read=NOW - timedelta(days=3)),
        4: _card(4, Column.EXECUTED, 3, leverage=_unread()),
        5: _card(
            5, Column.DECISION_MOMENT, 0, leverage=_read(Leverage.DOES_NOT_ADDRESS), unblocks=0
        ),
        6: _card(
            6,
            Column.DECISION_MOMENT,
            1,
            leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH),
            unblocks=2,
        ),
        7: _card(7, Column.DECISION_MOMENT, 2, leverage=_unread(), unblocks=2),
        8: _card(8, Column.DONE, 0, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH)),
        9: _card(9, Column.DONE, 1, leverage=_read(Leverage.DOES_NOT_ADDRESS)),
    }
    arranged = _arrange(judged)
    assert arranged.moves == []
    assert _column(arranged, Column.EXECUTED) == [2, 3, 1, 4], (
        "the signal only he can read first, then by read date oldest first, unread last"
    )
    assert _column(arranged, Column.DECISION_MOMENT) == [6, 7, 5], (
        "the ruling that frees the most helps-remove work first, ties by his rank"
    )
    assert _column(arranged, Column.DONE) == [8, 9], "Done keeps his order"


def test_protects_keeps_its_column_after_helps_remove_and_the_rest_keep_their_place_by_rank():
    judged = {
        1: _card(1, Column.UP_NEXT, 0, leverage=_unread()),
        2: _card(2, Column.UP_NEXT, 1, leverage=_read(Leverage.PROTECTS)),
        3: _card(3, Column.UP_NEXT, 2, leverage=_read(Leverage.NEEDS_EVIDENCE)),
        4: _card(4, Column.UP_NEXT, 3, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.LOW)),
        5: _card(5, Column.UP_NEXT, 4, leverage=_read(Leverage.PROTECTS)),
        6: _card(6, Column.UP_NEXT, 5, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.LOW)),
        7: _card(7, Column.UP_NEXT, 6, leverage=None),
    }
    arranged = _arrange(judged)
    assert _column(arranged, Column.UP_NEXT) == [4, 6, 2, 5, 1, 3, 7], (
        "helps-remove ties keep his rank, protects follow in his rank, the rest keep their place"
    )
    assert arranged.moves == []


def test_an_unticked_move_is_not_proposed_again_until_its_ground_changes():
    judged = {
        1: _card(1, Column.PLANNED, 0, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH)),
        2: _card(2, Column.UP_NEXT, 0, leverage=_read(Leverage.PROTECTS)),
    }
    declined = Decline(
        id=1,
        project="p",
        card_number=1,
        focus_fingerprint=FOCUS,
        document_fingerprint="doc1",
        leverage=Leverage.HELPS_REMOVE,
        at=NOW,
    )
    assert _arrange(judged, declines=[declined]).moves == []
    assert _column(_arrange(judged, declines=[declined]), Column.PLANNED) == [1]
    other_focus = declined.model_copy(update={"focus_fingerprint": "other"})
    assert [m.number for m in _arrange(judged, declines=[other_focus]).moves] == [1]
    other_document = declined.model_copy(update={"document_fingerprint": "doc1-edited"})
    assert [m.number for m in _arrange(judged, declines=[other_document]).moves] == [1]
    other_class = declined.model_copy(update={"leverage": Leverage.PROTECTS})
    assert [m.number for m in _arrange(judged, declines=[other_class]).moves] == [1]


def test_an_unavailable_or_paused_order_never_orders():
    judged = {
        1: _card(1, Column.UP_NEXT, 0, leverage=_read(Leverage.DOES_NOT_ADDRESS)),
        2: _card(2, Column.PLANNED, 0, leverage=_read(Leverage.HELPS_REMOVE, Likelihood.HIGH)),
    }
    arranged = _arrange(judged, available=False, why="The results challenge this diagnosis")
    assert not arranged.available and arranged.why == "The results challenge this diagnosis"
    assert arranged.moves == []
    assert _column(arranged, Column.UP_NEXT) == [1] and _column(arranged, Column.PLANNED) == [2]
