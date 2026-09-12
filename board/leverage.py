"""The board as the chosen focus would arrange it (card #87, item 5): one
pure function over the cards, their classes and the columns' grammar, so
the page, the verb and the tests read one answer.

The lens proposes across every column; one click of his makes it the
board; one click puts it back (the plan's rulings). What the function
never does: write rank, read the dial, or move anything — it answers with
an `Arrangement`, and the acceptance door applies the moves he ticked
through the same write a drag makes, with his name on each.

The rules, each held by a test in `tests/board/test_leverage.py`:

- every column is ordered; cards move only between Backlog, Planned, Up
  next and Not now. Executed, Done and Decision moment are never
  rearranged — the first two are machine facts, the third his by name —
  but Decision moment is ordered by what each ruling unblocks and
  Executed with the signals only he can read first, then by read date;
- a planned card that helps remove the limit is shown in Up next, ordered
  by likelihood then by effort gate ascending: the gate is the cost and
  time a plan already declares, and likelihood is one word with a reason,
  never a score;
- a card in Up next that does not address the limit is shown in Not now
  with a wake trigger written from the focus's recheck;
- a Backlog defect that helps remove the limit stays where it is with the
  Plan door open, never in Up next: the corpus is the status and a
  suggestion cannot enter execution without a plan;
- protects-progress cards keep their column and order after the
  helps-remove ones; needs-evidence, unread and stale cards keep their
  place; a card with a Sequencing hold shows the hold beside its class,
  because impact and readiness are two facts;
- ties keep his rank; a move he left unticked is not proposed again until
  the focus, the card's document or its class changes.
"""

from datetime import datetime

from pydantic import BaseModel

from board.moves import GroupLayout
from board.reconcile import home_of
from domain.card import Place
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.focus import (
    ArrangedColumn,
    ArrangedGroup,
    Arrangement,
    CardLeverage,
    Decline,
    Leverage,
    LeverageState,
    Likelihood,
    ProposedMove,
)
from domain.gate import Gate

MOVABLE: frozenset[Column] = frozenset(
    {Column.DEFECTS, Column.BACKLOG, Column.PLANNED, Column.UP_NEXT, Column.NOT_NOW}
)
"""The five columns cards move between under the lens."""

FROZEN: frozenset[Column] = frozenset({Column.EXECUTED, Column.DONE, Column.DECISION_MOMENT})
"""Never rearranged by class: two machine facts and the owner's own column."""

_CLASS_RANK: dict[Leverage, int] = {
    Leverage.HELPS_REMOVE: 0,
    Leverage.PROTECTS: 1,
    Leverage.NEEDS_EVIDENCE: 2,
    Leverage.DOES_NOT_ADDRESS: 2,
}
_UNREAD_RANK = 2
"""Needs-evidence, unread, stale and does-not-address cards keep their
place among themselves, after the two classes that order."""

_LIKELIHOOD_RANK: dict[Likelihood, int] = {
    Likelihood.HIGH: 0,
    Likelihood.MEDIUM: 1,
    Likelihood.LOW: 2,
}
_GATE_COST: dict[Gate, int] = {Gate.LOW: 0, Gate.MEDIUM: 1, Gate.HIGH: 2, Gate.XHIGH: 3}


class Judged(BaseModel):
    """One card as the arrangement sees it: where it is, what it is, and
    what the reading said. Built by the board's assembly from the card,
    its document and its doors; the arrangement reads nothing else."""

    number: int
    place: Place
    gate: Gate | None
    kind: DocumentKind | None
    suggestion_kind: SuggestionKind | None
    document_fingerprint: str | None
    leverage: CardLeverage | None
    unblocks: int = 0
    """How many helps-remove cards this card's ruling would free: what
    orders Decision moment."""
    owner_signal: bool = False
    """Its signal is one only the owner can read: what orders Executed first."""
    last_read: datetime | None = None
    """When its signal was last read: what orders Executed after that."""


def _read(judged: Judged) -> CardLeverage | None:
    lv = judged.leverage
    return lv if lv is not None and lv.state == LeverageState.READ else None


def _class_key(judged: Judged, rank: int) -> tuple[int, int, int, int]:
    read = _read(judged)
    if read is None or read.leverage is None:
        return (_UNREAD_RANK, 9, 9, rank)
    if read.leverage == Leverage.HELPS_REMOVE:
        likelihood = _LIKELIHOOD_RANK.get(read.likelihood, 3) if read.likelihood else 3
        cost = _GATE_COST.get(judged.gate, 4) if judged.gate else 4
        return (0, likelihood, cost, rank)
    return (_CLASS_RANK[read.leverage], 9, 9, rank)


def _decision_key(judged: Judged, rank: int) -> tuple[int, int]:
    return (-judged.unblocks, rank)


def _executed_key(judged: Judged, rank: int) -> tuple[int, int, float, int]:
    unread = judged.last_read is None
    when = judged.last_read.timestamp() if judged.last_read is not None else 0.0
    return (0 if judged.owner_signal else 1, 1 if unread else 0, when, rank)


def _destination(judged: Judged) -> tuple[Column, str | None] | None:
    """Where a read card would go, if anywhere: the four rules above."""
    read = _read(judged)
    if read is None or read.leverage is None:
        return None
    column = judged.place.column
    if read.leverage == Leverage.HELPS_REMOVE:
        if column == Column.PLANNED and judged.kind == DocumentKind.PLAN:
            return (Column.UP_NEXT, None)
        if column == Column.NOT_NOW:
            if judged.kind == DocumentKind.PLAN:
                return (Column.UP_NEXT, None)
            if judged.kind == DocumentKind.SUGGESTION:
                return (home_of(judged.suggestion_kind), None)
        return None
    if read.leverage == Leverage.DOES_NOT_ADDRESS and column == Column.UP_NEXT:
        return (Column.NOT_NOW, None)
    return None


def _declined(judged: Judged, focus_fingerprint: str, declines: list[Decline]) -> bool:
    read = _read(judged)
    if read is None or judged.document_fingerprint is None:
        return False
    return any(
        d.card_number == judged.number
        and d.focus_fingerprint == focus_fingerprint
        and d.document_fingerprint == judged.document_fingerprint
        and d.leverage == read.leverage
        for d in declines
    )


def _why(judged: Judged) -> str:
    read = _read(judged)
    assert read is not None and read.leverage is not None
    likelihood = f", {read.likelihood.value} likelihood" if read.likelihood else ""
    return f"{read.leverage.value}{likelihood}: {read.words or ''}".rstrip(": ")


def arrange(
    layout: list[GroupLayout],
    judged: dict[int, Judged],
    *,
    focus_fingerprint: str,
    declines: list[Decline],
    wake: str | None,
    available: bool,
    why: str | None,
) -> Arrangement:
    """The board as the focus would arrange it. With `available` false the
    columns come back in his rank, untouched, and `why` says why; a paused
    order never orders (card #87, item 6)."""
    if not available:
        return Arrangement(
            available=False,
            why=why or "the leverage order is unavailable",
            columns=_as_is(layout),
            moves=[],
        )
    # Where every card ends up: its own column, or the destination a rule names.
    moves: list[ProposedMove] = []
    landing: dict[int, tuple[Column, str | None]] = {}
    for group in layout:
        for number in group.numbers:
            card = judged.get(number)
            if card is None:
                continue
            if card.place.column in MOVABLE and not _declined(card, focus_fingerprint, declines):
                destination = _destination(card)
                if destination is not None:
                    landing[number] = destination
    # The ranks he gave: position across a column's groups, in group order.
    ranks: dict[int, int] = {}
    for column in Column:
        rank = 0
        for group in layout:
            if group.column != column:
                continue
            for number in group.numbers:
                ranks[number] = rank
                rank += 1
    columns: list[ArrangedColumn] = []
    for column in Column:
        groups: list[ArrangedGroup] = []
        for group in layout:
            if group.column != column:
                continue
            members = [n for n in group.numbers if landing.get(n) is None]
            arrivals = [
                n
                for n, (to_column, to_group) in landing.items()
                if to_column == column and to_group == group.name
            ]
            staying = [n for n in members if n in judged]
            unknown = [n for n in members if n not in judged]
            ordered = _ordered(column, staying + arrivals, judged, ranks)
            groups.append(ArrangedGroup(name=group.name, numbers=ordered + unknown))
        # An arrival into a group the column does not have lands in a new
        # unnamed group at the column's end, as the store would make one.
        homeless = [
            n
            for n, (to_column, to_group) in landing.items()
            if to_column == column and not any(g.name == to_group for g in groups)
        ]
        if homeless:
            groups.append(
                ArrangedGroup(
                    name=next(landing[n][1] for n in homeless),
                    numbers=_ordered(column, homeless, judged, ranks),
                )
            )
        columns.append(ArrangedColumn(column=column, groups=groups))
    for number, (to_column, to_group) in landing.items():
        card = judged[number]
        arranged = next(c for c in columns if c.column == to_column)
        group = next(g for g in arranged.groups if g.name == to_group)
        moves.append(
            ProposedMove(
                number=number,
                from_place=card.place,
                to_place=Place(
                    column=to_column, group=to_group, position=group.numbers.index(number)
                ),
                why=_why(card),
                wake=wake if to_column == Column.NOT_NOW else None,
            )
        )
    moves.sort(key=lambda m: (m.to_place.column.value, m.to_place.position))
    return Arrangement(available=True, why=None, columns=columns, moves=moves)


def _ordered(
    column: Column, numbers: list[int], judged: dict[int, Judged], ranks: dict[int, int]
) -> list[int]:
    """One column's cards in the lens's order. His rank is the tie-break
    everywhere; an arrival ranks after the cards already there among its
    equals, since it had no rank here."""

    def rank_of(number: int) -> int:
        card = judged[number]
        return ranks[number] if card.place.column == column else 10_000 + ranks.get(number, 0)

    if column == Column.DONE:
        return sorted(numbers, key=rank_of)
    if column == Column.DECISION_MOMENT:
        return sorted(numbers, key=lambda n: _decision_key(judged[n], rank_of(n)))
    if column == Column.EXECUTED:
        return sorted(numbers, key=lambda n: _executed_key(judged[n], rank_of(n)))
    return sorted(numbers, key=lambda n: _class_key(judged[n], rank_of(n)))


def _as_is(layout: list[GroupLayout]) -> list[ArrangedColumn]:
    columns: list[ArrangedColumn] = []
    for column in Column:
        groups = [
            ArrangedGroup(name=g.name, numbers=list(g.numbers))
            for g in layout
            if g.column == column
        ]
        columns.append(ArrangedColumn(column=column, groups=groups))
    return columns


def wake_line(recheck_what: str | None, recheck_line: str | None) -> str | None:
    """The wake trigger a card parked by the lens carries, in the WATCH
    grammar, written from the focus's recheck line: the card wakes when
    the diagnosis is read again."""
    if recheck_line is None:
        return None
    what = recheck_what or "the focus is checked again"
    return f"WATCH: wake when {what} — {recheck_line}"
