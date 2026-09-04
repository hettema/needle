"""Assembling what the page receives from what the store holds and the corpus says.

Everything a card shows beyond its stored place and rows is derived here, at
read time, from the document: its state (five, always one), its gate, its
essence. Deriving rather than copying is what keeps the board true to the
file with nobody syncing anything.
"""

from datetime import datetime, timedelta

from board.evidence import placement_from, standing_for
from board.lane import STARTABLE_COLUMNS, nothing_read
from board.moves import GroupLayout
from board.reconcile import carried_stems, ref
from board.signals import is_due, past_due, read_or_decline
from board.verdicts import read_or_decline as read_verdict_or_decline
from domain.audit import AuditEntry
from domain.board import (
    Attention,
    BoardState,
    CardDetail,
    CardSummary,
    ColumnView,
    EssenceSource,
    FoldedCard,
    GroupView,
    MachineState,
    OwnerAsk,
    TrunkState,
)
from domain.card import Actor, Card, CardOrigin
from domain.column import COLUMN_DEFINITIONS, DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex, CorpusSummary
from domain.document import Document, DocumentKind, DocumentRef, DocumentState, SuggestionKind
from domain.evidence import EvidenceState
from domain.gate import Gate
from domain.lane import HANDS_ON, Doors, Lane, LaneSnapshot, LaneState
from domain.project import Project
from domain.row import ROW_HALF, Row, RowHalf, RowKind
from domain.signal import Reading, ReadingSession, Signal, SignalKind
from domain.verdict import Verdict, VerdictLine
from domain.watercooler import WatercoolerLine

NEW_FOR = timedelta(days=1)

UNPLANNED_OUTSIDE: frozenset[Column] = frozenset({Column.DONE, Column.NOT_NOW})
"""A suggestion parked or shipped is not on the unplanned pile."""


def document_of(card: Card, index: CorpusIndex) -> Document | None:
    if card.link is None:
        return None
    return index.find(card.link.kind, card.link.stem)


def document_state(card: Card, document: Document | None) -> DocumentState:
    if card.link is None:
        return DocumentState.NOTE
    if document is None:
        return DocumentState.GONE
    if document.archived:
        return DocumentState.ARCHIVED
    return DocumentState(document.kind.value)


def cited_path(card: Card) -> str | None:
    """The path the card cites for its document, whether or not it exists."""
    return card.link.path() if card.link is not None else None


def card_gate(card: Card, document: Document | None) -> Gate | None:
    if document is not None and document.gate is not None:
        return document.gate
    return card.gate


def essence(card: Card, document: Document | None) -> tuple[str | None, EssenceSource | None]:
    serves = next((r.text for r in card.rows if r.kind == RowKind.SERVES), None)
    if serves:
        return serves, EssenceSource.CARD
    if document is not None and document.essence:
        return document.essence, EssenceSource.DOCUMENT
    return None, None


def is_new(card: Card, now: datetime) -> bool:
    return card.origin == CardOrigin.ARRIVED and card.born_at >= now - NEW_FOR


def watch_signal(card: Card) -> tuple[Signal | None, str | None]:
    """The signal the card's WATCH row names, or why it names none."""
    watch = next((r.text for r in card.rows if r.kind == RowKind.WATCH), None)
    return read_or_decline(watch)


def card_verdict(card: Card) -> tuple[Verdict | None, str | None]:
    """The verdict the card's VERDICT row names, or why it names none."""
    text = next((r.text for r in card.rows if r.kind == RowKind.VERDICT), None)
    return read_verdict_or_decline(text)


def verdict_lines(cards: list[Card]) -> list[VerdictLine]:
    """Every card standing on its own that carries a verdict the owner has
    not yet ruled on, by number."""
    lines: list[VerdictLine] = []
    for card in sorted(cards, key=lambda c: c.number):
        if card.folded_into is not None:
            continue
        verdict, _ = card_verdict(card)
        if verdict is not None:
            lines.append(
                VerdictLine(number=card.number, title=card.title, place=card.place, verdict=verdict)
            )
    return lines


def folded_under(cards: list[Card]) -> dict[int, list[FoldedCard]]:
    """Each card's folded cards, by the leader's number (plan 06, item 5)."""
    out: dict[int, list[FoldedCard]] = {}
    for card in sorted(cards, key=lambda c: c.number):
        if card.folded_into is None:
            continue
        out.setdefault(card.folded_into, []).append(
            FoldedCard(number=card.number, title=card.title, document_path=cited_path(card))
        )
    return out


def asked_evidence(signal: Signal | None, last: Reading | None) -> str | None:
    """A reading session's cannot-tell, in its words: what the owner is
    asked with (plan 09, item 4). A machine's unreadable — a reading session
    that ended without a finding — is not a question for him."""
    if (
        signal is not None
        and signal.kind == SignalKind.SESSION
        and last is not None
        and last.delivered is None
        and last.actor == Actor.SESSION
    ):
        return last.words
    return None


def signal_asks_owner(
    card: Card, signal: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """An Executed card whose signal only the owner can read, at or past its
    due time; or one a session read and could not tell."""
    if card.place.column != Column.EXECUTED or signal is None:
        return False
    if signal.kind == SignalKind.OWNER:
        return now.date() >= signal.due and (last is None or last.delivered is None)
    return asked_evidence(signal, last) is not None


def signal_overdue(card: Card, signal: Signal | None, last: Reading | None, now: datetime) -> bool:
    """An Executed card past its due time with nothing delivered."""
    return (
        card.place.column == Column.EXECUTED
        and signal is not None
        and past_due(signal, now)
        and (last is None or not last.delivered)
    )


def signal_wants_reading(
    card: Card, signal: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """A board-readable signal whose cadence asks for a reading now."""
    return (
        card.place.column == Column.EXECUTED
        and signal is not None
        and signal.kind != SignalKind.OWNER
        and (last is None or not last.delivered)
        and is_due(signal, last_read=last.at if last else None, now=now)
    )


def summarize(
    card: Card,
    index: CorpusIndex,
    now: datetime,
    lane: Lane | None = None,
    *,
    doors: Doors | None = None,
    placement: AuditEntry | None = None,
    last: Reading | None = None,
    read: bool = False,
    folded: list[FoldedCard] | None = None,
    reading: ReadingSession | None = None,
) -> CardSummary:
    """`doors` is the card's doors as the loop last read them; the collapsed
    face shows the Start door's verdict and Plan from them (plan 06).
    `reading` is the session reading the card's signal right now (plan 09)."""
    document = document_of(card, index)
    text, source = essence(card, document)
    state = document_state(card, document)
    path = document.path if document is not None else cited_path(card)
    startable = card.place.column in STARTABLE_COLUMNS and card.folded_into is None
    return CardSummary(
        number=card.number,
        title=card.title,
        essence=text,
        essence_source=source,
        gate=card_gate(card, document),
        tags=card.tags,
        document_state=state,
        document_path=path,
        kind=document.suggestion_kind if document is not None else None,
        readiness=doors.readiness if doors is not None and startable else None,
        start=doors.start if doors is not None and startable else None,
        plan=doors.plan if doors is not None and state == DocumentState.SUGGESTION else None,
        folded=folded or [],
        points=sum(1 for r in card.rows if r.kind != RowKind.SERVES),
        is_new=is_new(card, now),
        age_date=document.date if document is not None and document.date else card.born_at.date(),
        place=card.place,
        lane_state=lane.state if lane is not None else LaneState.NONE,
        lane_sentence=lane.sentence if lane is not None and lane.sentence else None,
        colliding=lane.colliding if lane is not None and lane.state in HANDS_ON else None,
        standing=standing_for(card, placement, lane, last, read=read),
        reading=reading,
    )


def split_rows(rows: list[Row]) -> tuple[list[Row], list[Row]]:
    brief = [r for r in rows if ROW_HALF[r.kind] == RowHalf.BRIEF]
    record = [r for r in rows if ROW_HALF[r.kind] == RowHalf.RECORD]
    return brief, record


def documents_without_card(index: CorpusIndex, cards: list[Card]) -> list[DocumentRef]:
    """Live documents no card stands for. A suggestion a plan's head cites
    is carried by that plan's card and is not one of them."""
    linked = {(c.link.kind, c.link.stem) for c in cards if c.link}
    carried = carried_stems(index)
    return [
        ref(d)
        for d in index.live()
        if (d.kind, d.stem) not in linked
        and not (d.kind == DocumentKind.SUGGESTION and d.stem in carried)
    ]


def corpus_summary(index: CorpusIndex, *, watching: bool, watch_note: str | None) -> CorpusSummary:
    live = index.live()
    return CorpusSummary(
        live_plans=sum(1 for d in live if d.kind == DocumentKind.PLAN),
        live_suggestions=sum(1 for d in live if d.kind == DocumentKind.SUGGESTION),
        archived=len(index.archived()),
        watching=watching,
        watch_note=watch_note,
        read_at=index.read_at,
    )


def assemble_board(
    *,
    project: Project,
    layout: list[GroupLayout],
    cards: list[Card],
    index: CorpusIndex,
    version: int,
    watching: bool,
    watch_note: str | None,
    now: datetime,
    snapshot: LaneSnapshot | None = None,
    readings: dict[int, Reading] | None = None,
    trunk: TrunkState | None = None,
    machine: MachineState | None = None,
    placements: dict[int, AuditEntry] | None = None,
    watercooler: list[WatercoolerLine] | None = None,
    reading_sessions: dict[int, ReadingSession] | None = None,
) -> BoardState:
    """`snapshot`, `readings`, `trunk` and `machine` are what the loop has
    read; before its first read they are absent and the board says so.
    `placements` is each card's placing audit row, what a read re-tests;
    `watercooler` the project's lines, newest last; `reading_sessions` the
    reading in flight on each card (plan 09)."""
    readings = readings or {}
    reading_sessions = reading_sessions or {}
    watercooler = watercooler or []
    placements = placements or {}
    trunk = trunk or TrunkState(level=None, behind=0, note=None, read_at=None)
    machine = machine or MachineState(missing=[])
    by_number = {c.number: c for c in cards}
    standing = [c for c in cards if c.folded_into is None]
    lanes = snapshot.lanes if snapshot is not None else {}
    doors = snapshot.doors if snapshot is not None else {}
    folded = folded_under(cards)

    def doors_of(card: Card) -> Doors:
        found = doors.get(card.number)
        return found if found is not None else nothing_read(card, project.path, now)[1]

    summaries = {
        n: summarize(
            c,
            index,
            now,
            lanes.get(n),
            doors=doors_of(c),
            placement=placements.get(n),
            last=readings.get(n),
            read=snapshot is not None,
            folded=folded.get(n),
            reading=reading_sessions.get(n),
        )
        for n, c in by_number.items()
    }
    signals = {n: watch_signal(c)[0] for n, c in by_number.items()}

    columns: list[ColumnView] = []
    for definition in COLUMN_DEFINITIONS:
        groups = [
            GroupView(
                name=g.name,
                cards=[summaries[n] for n in g.numbers],
                rail=definition.column == Column.BACKLOG and g.name == DEFECTS_RAIL,
            )
            for g in layout
            if g.column == definition.column
        ]
        if not groups:
            groups = [GroupView(name=None, cards=[], rail=False)]
        columns.append(
            ColumnView(
                definition=definition,
                groups=groups,
                count=sum(len(g.cards) for g in groups),
            )
        )

    def count(column: Column) -> int:
        return sum(1 for c in standing if c.place.column == column)

    def unplanned(kind: SuggestionKind) -> int:
        return sum(
            1
            for c in standing
            if c.place.column not in UNPLANNED_OUTSIDE
            and summaries[c.number].document_state == DocumentState.SUGGESTION
            and summaries[c.number].kind == kind
        )

    without_card = documents_without_card(index, cards)
    asking_lanes = sum(1 for lane in lanes.values() if lane.state == LaneState.ASKING)
    asks = [
        OwnerAsk(
            number=n,
            title=c.title,
            what=signals[n].what,
            due=signals[n].due,
            kind=signals[n].kind,
            evidence=asked_evidence(signals[n], readings.get(n)),
        )
        for n, c in sorted(by_number.items())
        if signal_asks_owner(c, signals[n], readings.get(n), now) and signals[n] is not None
    ]
    verdicts = verdict_lines(cards)
    conversations = snapshot.conversations if snapshot is not None else []
    shown = [summaries[c.number] for c in standing]
    attention = Attention(
        asking_you=count(Column.DECISION_MOMENT) + asking_lanes + len(asks),
        in_flight=count(Column.EXECUTING),
        colliding=sum(1 for s in shown if s.colliding is not None),
        in_discussion=len(conversations),
        lanes_ended=sum(
            1
            for n, lane in lanes.items()
            if lane.state == LaneState.ENDED
            and n in by_number
            and by_number[n].folded_into is None
            and by_number[n].place.column not in {Column.EXECUTED, Column.DONE, Column.NOT_NOW}
        ),
        signals_due=sum(
            1 for n, c in by_number.items() if signal_overdue(c, signals[n], readings.get(n), now)
        ),
        signals_asking=len(asks),
        signals_reading=sum(1 for c in standing if c.number in reading_sessions),
        doubted=sum(1 for s in shown if s.standing.state == EvidenceState.DOUBTED),
        verdicts_unread=len(verdicts),
        unplanned_defects=unplanned(SuggestionKind.DEFECT),
        unplanned_ideas=unplanned(SuggestionKind.IDEA),
        arrived_today=sum(1 for s in shown if s.is_new),
        documents_gone=sum(1 for s in shown if s.document_state == DocumentState.GONE),
        documents_without_card=len(without_card),
    )
    return BoardState(
        project=project,
        version=version,
        generated_at=now,
        corpus=corpus_summary(index, watching=watching, watch_note=watch_note),
        attention=attention,
        trunk=trunk,
        machine=machine,
        columns=columns,
        documents_without_card=without_card,
        asks=asks,
        verdicts=verdicts,
        conversations=conversations,
        watercooler=watercooler,
    )


def assemble_detail(
    card: Card,
    index: CorpusIndex,
    history: list[AuditEntry],
    now: datetime,
    *,
    lane: Lane | None,
    doors: Doors,
    readings: list[Reading],
    read: bool = False,
    watercooler: list[WatercoolerLine] | None = None,
    folded: list[FoldedCard] | None = None,
    reading: ReadingSession | None = None,
) -> CardDetail:
    """`readings` newest first; `read` is whether the loop has read the
    machine; `folded` the cards folded under this one; `reading` the
    session reading its signal right now."""
    document = document_of(card, index)
    brief, record = split_rows(card.rows)
    own = cited_path(card)
    signal, signal_note = watch_signal(card)
    verdict, verdict_note = card_verdict(card)
    return CardDetail(
        card=card,
        summary=summarize(
            card,
            index,
            now,
            lane,
            doors=doors,
            placement=placement_from(history),
            last=readings[0] if readings else None,
            read=read,
            folded=folded,
            reading=reading,
        ),
        brief=brief,
        record=record,
        document=document,
        other_citations=[c for c in card.citations if c != own],
        history=history,
        lane=lane,
        doors=doors,
        signal=signal,
        signal_note=signal_note,
        readings=readings,
        verdict=verdict,
        verdict_note=verdict_note,
        watercooler=watercooler or [],
    )
