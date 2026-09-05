"""Assembling what the page receives from what the store holds and the corpus says.

Everything a card shows beyond its stored place and rows is derived here, at
read time, from the document: its state (five, always one), its gate, its
essence. Deriving rather than copying is what keeps the board true to the
file with nobody syncing anything.
"""

from datetime import datetime, timedelta

from board.evidence import placement_from, standing_for
from board.handouts import handouts_for
from board.lane import STARTABLE_COLUMNS, ago, first_line, last_line, nothing_read
from board.moves import GroupLayout
from board.reconcile import carried_stems, ref
from board.signals import is_due, past_due, read_or_decline
from board.verdicts import read_or_decline as read_verdict_or_decline
from domain.audit import AuditEntry
from domain.board import (
    CLAIM_MEANING,
    Attention,
    BoardState,
    CardDetail,
    CardState,
    CardSummary,
    Claim,
    ClaimCount,
    ColumnView,
    EssenceSource,
    FaceDoor,
    FaceDoorName,
    FoldedCard,
    GroupView,
    Loop,
    LoopState,
    MachineState,
    Meaning,
    OwnerAsk,
    TrunkState,
)
from domain.card import Actor, Card, CardOrigin
from domain.column import COLUMN_DEFINITIONS, DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex, CorpusSummary
from domain.dial import Dial, DialState
from domain.document import (
    Document,
    DocumentKind,
    DocumentRef,
    DocumentState,
    FixMark,
    SuggestionKind,
)
from domain.evidence import EvidenceState, Standing
from domain.gate import Gate
from domain.hook import HeardMark
from domain.lane import HANDS_ON, Doors, Lane, LaneSnapshot, LaneState, StartState
from domain.project import Project
from domain.row import ROW_HALF, Row, RowHalf, RowKind
from domain.signal import Reading, Signal, SignalKind, WindowlessSession
from domain.verdict import Verdict, VerdictLine
from domain.watercooler import WatercoolerLine

NEW_FOR = timedelta(days=1)

UNPLANNED_OUTSIDE: frozenset[Column] = frozenset({Column.DONE, Column.NOT_NOW})
"""A suggestion parked or shipped is not on the unplanned pile."""

SHIPPED: frozenset[Column] = frozenset({Column.EXECUTED, Column.DONE})
"""Built and archived: the card carries its loop, and a lane that ended is
the normal end of its work, not a death."""

CLAIM_WORDS: dict[Claim, tuple[str, str]] = {
    Claim.VERDICT: ("verdict to accept", "verdicts to accept"),
    Claim.LANE_ASKING: ("lane asking you", "lanes asking you"),
    Claim.SIGNAL_ASKING: ("signal for you to read", "signals for you to read"),
    Claim.DECISION: ("card in Decision moment", "cards in Decision moment"),
    Claim.LANE_ENDED: ("lane died", "lanes died"),
    Claim.DOUBTED: ("status doubted", "statuses doubted"),
    Claim.SIGNAL_OVERDUE: ("signal past due, unread", "signals past due, unread"),
    Claim.DOCUMENT_GONE: ("document nowhere", "documents nowhere"),
    Claim.COLLIDING: ("lane colliding", "lanes colliding"),
    Claim.DOCUMENT_WITHOUT_CARD: ("document with no card", "documents with no card"),
    Claim.NO_REVIEW: ("shipped with no review record", "shipped with no review record"),
    Claim.LANE_WORKING: ("lane working", "lanes working"),
    Claim.CONVERSATION: ("conversation", "conversations"),
    Claim.SIGNAL_READING: ("signal being read", "signals being read"),
    Claim.PLANNING: ("defect being planned", "defects being planned"),
}
"""Each claim's words, singular and plural: the head's breakdown (plan 27, item 1)."""

NO_DIAL = DialState(
    dial=Dial(on=False, lanes=1, changed_at=None, first_on_at=None),
    running=0,
    held=0,
    full=None,
    quiet=True,
)
"""The dial before the store has been asked: off, as a board never told otherwise is."""

WAITING_ON_YOU: frozenset[LaneState] = frozenset(
    {LaneState.ASKING, LaneState.STOPPED, LaneState.BLOCKED}
)
"""A lane that stopped, asked, or hit a prompt: the Answer door is the way on."""

OPEN_TO_SEE = "open to see"


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


def trigger_signal(document: Document | None) -> tuple[Signal | None, str | None]:
    """The signal a defect's `Fix: when` trigger names (plan 11, item 5), or
    why it names none; (None, None) for a document that carries no trigger."""
    if document is None or document.fix is None or document.fix.mark != FixMark.WHEN:
        return None, None
    if document.fix.trigger is None:
        return None, "the Fix: when line names no trigger"
    return read_or_decline(document.fix.trigger)


def is_trigger_card(card: Card, document: Document | None) -> bool:
    """A Backlog card behind a live suggestion whose `Fix: when` trigger the
    signal loop reads as it reads an Executed card's WATCH row."""
    return (
        card.place.column == Column.BACKLOG
        and document is not None
        and not document.archived
        and document.kind == DocumentKind.SUGGESTION
        and document.fix is not None
        and document.fix.mark == FixMark.WHEN
    )


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


def asks_owner(signal: Signal | None, last: Reading | None, now: datetime) -> bool:
    """A signal only the owner can read, at or past its due time; or one a
    session read and could not tell."""
    if signal is None:
        return False
    if signal.kind == SignalKind.OWNER:
        return now.date() >= signal.due and (last is None or last.delivered is None)
    return asked_evidence(signal, last) is not None


def signal_asks_owner(
    card: Card, signal: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """An Executed card whose signal asks the owner."""
    return card.place.column == Column.EXECUTED and asks_owner(signal, last, now)


def trigger_asks_owner(
    card: Card, trigger: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """A Backlog defect whose `Fix: when` trigger asks the owner (plan 11,
    item 5): a session read it and could not tell, or only he can read it."""
    return card.place.column == Column.BACKLOG and asks_owner(trigger, last, now)


def signal_overdue(card: Card, signal: Signal | None, last: Reading | None, now: datetime) -> bool:
    """A shipped card past its signal's due time with nothing delivered: the
    loop the board said it would close has not closed (plan 27, item 3)."""
    return (
        card.place.column == Column.EXECUTED
        and signal is not None
        and past_due(signal, now)
        and (last is None or not last.delivered)
    )


def wants_reading(signal: Signal | None, last: Reading | None, now: datetime) -> bool:
    """A board-readable signal whose cadence asks for a reading now."""
    return (
        signal is not None
        and signal.kind != SignalKind.OWNER
        and (last is None or not last.delivered)
        and is_due(signal, last_read=last.at if last else None, now=now)
    )


def signal_wants_reading(
    card: Card, signal: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """An Executed card's signal, due for the board's or a session's reading."""
    return card.place.column == Column.EXECUTED and wants_reading(signal, last, now)


def trigger_wants_reading(
    card: Card, trigger: Signal | None, last: Reading | None, now: datetime
) -> bool:
    """A Backlog defect's `Fix: when` trigger, due for the same readers on
    the same cadence (plan 11, item 5)."""
    return card.place.column == Column.BACKLOG and wants_reading(trigger, last, now)


def _where(lane: Lane) -> str:
    session = lane.session
    if session is None:
        return lane.name
    return f"{session.model.value if session.model else 'fable'} on {session.slot}"


def _cards(numbers: list[int]) -> str:
    return ", ".join(f"#{n}" for n in numbers)


def _due(signal: Signal) -> str:
    return f"{signal.due.day} {signal.due.strftime('%b')}"


def _signal_line(signal: Signal) -> str:
    return f"Signal: {signal.what} — by {_due(signal)}"


def _lane_is_spent(card: Card, lane: Lane) -> bool:
    """A lane with nothing left to say about this card. Its work folded and
    the card shipped on it: what matters now is whether the loop closed, not
    that the session which did the work has since stopped. Without this every
    card reads "stopped · <model> on <slot>" in amber the moment it closes,
    because that is exactly when the session's turn ends — the owner is asked
    to act on work that is already done."""
    return (
        lane.folded
        and card.place.column in SHIPPED
        and lane.state in {LaneState.STOPPED, LaneState.ENDED}
    )


def _lane_died(card: Card, lane: Lane) -> bool:
    """An ended lane that is broken rather than simply finished. A lane that
    folded is done: its worktree is still on disk and Start says so in one
    quiet word ("lane exists"). A lane that ended with nothing folded lost the
    work it was doing, and that is what red is for."""
    return (
        not lane.folded and card.place.column not in SHIPPED and card.place.column != Column.NOT_NOW
    )


def _door(name: FaceDoorName, label: str, why: str, *, primary: bool) -> FaceDoor:
    return FaceDoor(name=name, label=label, why=why, primary=primary)


def _state(
    word: str,
    meaning: Meaning,
    *,
    detail: str | None = None,
    loop: Loop | None = None,
    door: FaceDoor | None = None,
    hint: str | None = None,
) -> CardState:
    # A card carrying a loop has said everything on its line already; an
    # "open ▸" beside it is noise, and at a column's width it is noise that
    # truncates the loop itself. Every card opens on a click regardless.
    return CardState(
        word=word,
        meaning=meaning,
        detail=detail,
        loop=loop,
        door=door,
        hint=None if door is not None or loop is not None else (hint or OPEN_TO_SEE),
    )


def _loop_state(
    card: Card,
    signal: Signal | None,
    signal_note: str | None,
    last: Reading | None,
    reading: WindowlessSession | None,
    now: datetime,
) -> CardState:
    """A shipped card's state is its loop (plan 27, item 3)."""
    owner_only = signal is not None and signal.kind == SignalKind.OWNER
    if card.place.column == Column.DONE or (last is not None and last.delivered):
        read = (
            f" · read {last.at.astimezone().strftime('%H:%M')}, delivered"
            if last is not None and last.delivered
            else ""
        )
        return _state(
            f"loop closed{read}",
            Meaning.PROVEN,
            loop=Loop(state=LoopState.CLOSED, owner_only=owner_only),
        )
    if signal is None:
        return _state("no signal named", Meaning.QUIET, detail=signal_note)
    open_loop = Loop(state=LoopState.OPEN, owner_only=owner_only)
    if reading is not None:
        return _state(
            f"loop open · a session reads it now · {reading.slot}",
            Meaning.LIVE,
            detail=_signal_line(signal),
            loop=open_loop,
        )
    if signal_asks_owner(card, signal, last, now):
        evidence = asked_evidence(signal, last)
        return _state(
            "signal for you to read",
            Meaning.YOURS,
            detail=f"A session read it and could not tell: {evidence}"
            if evidence
            else _signal_line(signal),
            loop=Loop(state=LoopState.OPEN, owner_only=True),
            door=_door(
                FaceDoorName.OPEN,
                "Read",
                "Only you can read this signal; the open card takes your reading.",
                primary=True,
            ),
        )
    who = (
        "you read it"
        if owner_only
        else "a session reads it"
        if signal.kind == SignalKind.SESSION
        else "the board reads it"
    )
    # A signal past its due date with nothing read is the loop failing to
    # close: the card says who reads it and that reader has not. Two things
    # disagree, so it is broken, and it says so on the head as well.
    if past_due(signal, now):
        return _state(
            f"loop open · {_due(signal)} passed, unread",
            Meaning.BROKEN,
            detail=_signal_line(signal),
            loop=open_loop,
        )
    return _state(
        f"loop open · {who} {_due(signal)}",
        Meaning.QUIET,
        detail=_signal_line(signal),
        loop=open_loop,
    )


def state_of(
    card: Card,
    *,
    document_state: DocumentState,
    document_path: str | None,
    doors: Doors,
    lane: Lane | None,
    standing: Standing,
    signal: Signal | None,
    signal_note: str | None,
    last: Reading | None,
    reading: WindowlessSession | None,
    now: datetime,
    trigger: Signal | None = None,
    planning: WindowlessSession | None = None,
) -> CardState:
    """The one function that names a card's state (plan 27, item 2). The
    order is the rule's precedence: broken before yours, yours before live,
    the loop before the queue, the queue before the quiet. A card is in one
    state; the head's claims may count it under several. `trigger` is a
    defect's `Fix: when` signal and `planning` the dial's session writing
    its plan (plan 11)."""
    hands_on = lane is not None and lane.state in HANDS_ON
    if document_state == DocumentState.GONE:
        return _state(
            "document nowhere",
            Meaning.BROKEN,
            detail=f"cites {document_path}, and no such file exists in the project",
        )
    if standing.state == EvidenceState.DOUBTED:
        return _state("doubted", Meaning.BROKEN, detail=standing.words, hint="open to decide")
    if lane is not None and lane.state == LaneState.ENDED and _lane_died(card, lane):
        return _state(
            "lane ended",
            Meaning.BROKEN,
            detail=lane.died or first_line(lane.sentence),
            hint="open to resume",
        )
    if hands_on and lane is not None and lane.colliding is not None and lane.colliding.cards:
        return _state(
            f"colliding with {_cards(lane.colliding.cards)}",
            Meaning.BROKEN,
            detail=lane.colliding.sentence,
        )
    if lane is not None and lane.state in WAITING_ON_YOU and not _lane_is_spent(card, lane):
        answer = (
            _door(FaceDoorName.OPEN, doors.answer.label, doors.answer.why, primary=True)
            if doors.answer.offered
            else None
        )
        if lane.state == LaneState.ASKING:
            question = last_line(lane.question)
            return _state(
                "asking you",
                Meaning.YOURS,
                detail=f"“{question}”" if question else None,
                door=answer,
            )
        if lane.state == LaneState.STOPPED:
            return _state(
                f"stopped · {_where(lane)}",
                Meaning.YOURS,
                detail=first_line(lane.said),
                door=answer,
            )
        return _state(
            f"blocked · {_where(lane)}",
            Meaning.YOURS,
            detail=first_line(lane.session.detail) if lane.session is not None else None,
            door=answer,
        )
    if lane is not None and lane.state == LaneState.MOVING:
        return _state(
            f"moving · {_where(lane)}",
            Meaning.LIVE,
            detail=first_line(lane.sentence),
            door=_door(FaceDoorName.WATCH, doors.watch.label, doors.watch.why, primary=False)
            if doors.watch.offered
            else None,
        )
    if lane is not None and lane.state == LaneState.WORKING:
        # A lane the runtime moved to another subscription says so before it
        # says what it is doing: the move is the fact the owner has not seen.
        doing = first_line(lane.session.detail) if lane.session is not None else None
        return _state(
            f"working · {ago(lane.hands_on_since, now)} · {_where(lane)}",
            Meaning.LIVE,
            detail=lane.moved or doing,
            door=_door(FaceDoorName.WATCH, doors.watch.label, doors.watch.why, primary=False)
            if doors.watch.offered
            else None,
        )
    if card.place.column in SHIPPED:
        return _loop_state(card, signal, signal_note, last, reading, now)
    if card.place.column == Column.DECISION_MOMENT:
        return _state(
            "your move",
            Meaning.YOURS,
            door=_door(
                FaceDoorName.OPEN,
                "Decide",
                "This column is yours: the open card has every door and the record to rule on.",
                primary=True,
            ),
        )
    if card.place.column == Column.NOT_NOW:
        return _state("not now", Meaning.QUIET, hint="open ▸")
    if document_state == DocumentState.SUGGESTION and trigger_asks_owner(card, trigger, last, now):
        evidence = asked_evidence(trigger, last)
        return _state(
            "trigger for you to read",
            Meaning.YOURS,
            detail=f"A session read it and could not tell: {evidence}"
            if evidence
            else f"Trigger: {trigger.what} — by {_due(trigger)}"
            if trigger is not None
            else None,
            door=_door(
                FaceDoorName.OPEN,
                "Read",
                "Only you can read this trigger; the open card takes your reading.",
                primary=True,
            ),
        )
    if document_state == DocumentState.SUGGESTION and planning is not None:
        return _state(
            f"being planned · {planning.slot}",
            Meaning.LIVE,
            detail="The dial took it: a session is writing its plan in the project's checkout.",
        )
    if document_state == DocumentState.SUGGESTION:
        return _state(
            "no plan yet",
            Meaning.QUIET,
            door=_door(FaceDoorName.PLAN, doors.plan.label, doors.plan.why, primary=False)
            if doors.plan.offered
            else None,
        )
    if card.place.column in STARTABLE_COLUMNS and card.folded_into is None:
        readiness = doors.readiness
        if readiness.state == StartState.FREE:
            # The collapsed door is one word: at a column's width, "Start ·
            # fable on alpha" crowds the state word off the line. Where it
            # would run is in the door's own reason, and on the open face.
            return _state(
                "free to start",
                Meaning.PROVEN,
                door=_door(
                    FaceDoorName.START,
                    "Start",
                    f"{doors.start.label} — {doors.start.why}",
                    primary=True,
                ),
            )
        if readiness.state == StartState.SHARES:
            # Shared ground is shown, never waited on (INTENT.md lesson 4):
            # the same door as a free card, and the ground in its reason.
            return _state(
                f"shares ground with {_cards(readiness.cards)}",
                Meaning.PROVEN,
                detail=readiness.why,
                door=_door(
                    FaceDoorName.START,
                    "Start",
                    f"{doors.start.label} — {doors.start.why}",
                    primary=True,
                ),
            )
        if readiness.state == StartState.WAITS:
            return _state(
                "waits on " + ", ".join(w.label for w in readiness.waits),
                Meaning.QUIET,
                detail=readiness.why,
            )
        if readiness.state == StartState.UNREAD:
            return _state("not read yet", Meaning.QUIET, detail=readiness.why)
        if readiness.state == StartState.NOWHERE:
            return _state("nowhere to run", Meaning.QUIET, detail=readiness.why)
        if readiness.state == StartState.TAKEN:
            return _state("lane exists", Meaning.QUIET, detail=readiness.why)
        return _state("no gate", Meaning.QUIET, detail=readiness.why)
    if card.place.column == Column.EXECUTING:
        return _state("no hands on it", Meaning.QUIET)
    if document_state == DocumentState.NOTE:
        return _state("no document", Meaning.QUIET)
    if document_state == DocumentState.ARCHIVED:
        return _state("archived", Meaning.QUIET, hint="open ▸")
    return _state("planned", Meaning.QUIET)


def claims_of(
    card: Card,
    *,
    document_state: DocumentState,
    lane: Lane | None,
    standing: Standing,
    signal: Signal | None,
    last: Reading | None,
    reading: WindowlessSession | None,
    verdict: Verdict | None,
    now: datetime,
    trigger: Signal | None = None,
    planning: WindowlessSession | None = None,
    placement: AuditEntry | None = None,
) -> list[Claim]:
    """Every claim the card makes on the owner's eye, in the head's order.
    A card can carry several; the head counts each. `placement` is the
    audit row that put the card where it is: a shipped card a close placed
    with no REVIEW row is a claim (plan 11, item 1)."""
    claims: list[Claim] = []
    if verdict is not None and card.folded_into is None:
        claims.append(Claim.VERDICT)
    if lane is not None and lane.state in WAITING_ON_YOU and not _lane_is_spent(card, lane):
        claims.append(Claim.LANE_ASKING)
    if signal_asks_owner(card, signal, last, now) or trigger_asks_owner(card, trigger, last, now):
        claims.append(Claim.SIGNAL_ASKING)
    elif signal_overdue(card, signal, last, now):
        claims.append(Claim.SIGNAL_OVERDUE)
    if card.place.column == Column.DECISION_MOMENT:
        claims.append(Claim.DECISION)
    if lane is not None and lane.state == LaneState.ENDED and _lane_died(card, lane):
        claims.append(Claim.LANE_ENDED)
    if standing.state == EvidenceState.DOUBTED:
        claims.append(Claim.DOUBTED)
    if document_state == DocumentState.GONE:
        claims.append(Claim.DOCUMENT_GONE)
    if lane is not None and lane.state in HANDS_ON and lane.colliding is not None:
        claims.append(Claim.COLLIDING)
    if shipped_without_review(card, placement):
        claims.append(Claim.NO_REVIEW)
    if lane is not None and lane.state in {LaneState.WORKING, LaneState.MOVING}:
        claims.append(Claim.LANE_WORKING)
    if reading is not None:
        claims.append(Claim.SIGNAL_READING)
    if planning is not None:
        claims.append(Claim.PLANNING)
    return claims


def shipped_without_review(card: Card, placement: AuditEntry | None) -> bool:
    """A shipped card a close placed — a session's close, or the loop reading
    the close as landed — with no REVIEW row (plan 11, item 1): the close
    refuses a code lane without one, so a shipped card without one came
    through another door, and the head says so. A card the owner placed, or
    0.1's import did, is his word and not counted."""
    if card.place.column not in SHIPPED or card.folded_into is not None:
        return False
    if any(r.kind == RowKind.REVIEW for r in card.rows):
        return False
    return placement is not None and placement.actor in (Actor.SESSION, Actor.MACHINE)


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
    reading: WindowlessSession | None = None,
    planning: WindowlessSession | None = None,
    project_path: str = "",
) -> CardSummary:
    """`doors` is the card's doors as the loop last read them; before its
    first read they are the closed doors of `nothing_read`. The state line and
    the claims are named here from the same facts (plan 27). `reading` is the
    session reading the card's signal right now (plan 09); `planning` the
    dial's session writing its plan (plan 11)."""
    document = document_of(card, index)
    text, source = essence(card, document)
    state = document_state(card, document)
    path = document.path if document is not None else cited_path(card)
    doors = doors if doors is not None else nothing_read(card, project_path, now)[1]
    standing = standing_for(card, placement, lane, last, read=read)
    signal, signal_note = watch_signal(card)
    trigger, _ = trigger_signal(document)
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
        fix=document.fix if document is not None else None,
        state=state_of(
            card,
            document_state=state,
            document_path=path,
            doors=doors,
            lane=lane,
            standing=standing,
            signal=signal,
            signal_note=signal_note,
            last=last,
            reading=reading,
            now=now,
            trigger=trigger,
            planning=planning,
        ),
        claims=claims_of(
            card,
            document_state=state,
            lane=lane,
            standing=standing,
            signal=signal,
            last=last,
            reading=reading,
            verdict=card_verdict(card)[0],
            now=now,
            trigger=trigger,
            planning=planning,
            placement=placement,
        ),
        folded=folded or [],
        is_new=is_new(card, now),
        age_date=document.date if document is not None and document.date else card.born_at.date(),
        place=card.place,
        lane_state=lane.state if lane is not None else LaneState.NONE,
        colliding=lane.colliding if lane is not None and lane.state in HANDS_ON else None,
        progress=lane.progress if lane is not None and lane.state in HANDS_ON else None,
        standing=standing,
        reading=reading,
        planning=planning,
    )


def claim_counts(meaning: Meaning, counts: dict[Claim, int]) -> list[ClaimCount]:
    """The head's breakdown under one word: each claim with a count, in words."""
    return [
        ClaimCount(claim=claim, count=n, label=CLAIM_WORDS[claim][0 if n == 1 else 1])
        for claim in Claim
        if CLAIM_MEANING[claim] == meaning and (n := counts.get(claim, 0)) > 0
    ]


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
    reading_sessions: dict[int, WindowlessSession] | None = None,
    planning_sessions: dict[int, WindowlessSession] | None = None,
    dial: DialState | None = None,
) -> BoardState:
    """`snapshot`, `readings`, `trunk` and `machine` are what the loop has
    read; before its first read they are absent and the board says so.
    `placements` is each card's placing audit row, what a read re-tests;
    `watercooler` the project's lines, newest last; `reading_sessions` the
    reading in flight on each card (plan 09); `planning_sessions` the dial's
    planning session on each card and `dial` the dial itself (plan 11)."""
    readings = readings or {}
    reading_sessions = reading_sessions or {}
    planning_sessions = planning_sessions or {}
    watercooler = watercooler or []
    placements = placements or {}
    trunk = trunk or TrunkState(level=None, behind=0, note=None, read_at=None)
    machine = machine or MachineState(missing=[])
    dial = dial or NO_DIAL
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
            planning=planning_sessions.get(n),
        )
        for n, c in by_number.items()
    }
    signals = {n: watch_signal(c)[0] for n, c in by_number.items()}
    triggers = {n: trigger_signal(document_of(c, index))[0] for n, c in by_number.items()}

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

    def unplanned(kind: SuggestionKind) -> int:
        return sum(
            1
            for c in standing
            if c.place.column not in UNPLANNED_OUTSIDE
            and summaries[c.number].document_state == DocumentState.SUGGESTION
            and summaries[c.number].kind == kind
        )

    without_card = documents_without_card(index, cards)
    asks: list[OwnerAsk] = []
    for n, c in sorted(by_number.items()):
        asked = (
            signals[n]
            if signal_asks_owner(c, signals[n], readings.get(n), now)
            else triggers[n]
            if trigger_asks_owner(c, triggers[n], readings.get(n), now)
            else None
        )
        if asked is None:
            continue
        asks.append(
            OwnerAsk(
                number=n,
                title=c.title,
                what=asked.what,
                due=asked.due,
                kind=asked.kind,
                evidence=asked_evidence(asked, readings.get(n)),
            )
        )
    verdicts = verdict_lines(cards)
    conversations = snapshot.conversations if snapshot is not None else []
    shown = [summaries[c.number] for c in standing]
    counts: dict[Claim, int] = {}
    for summary in shown:
        for claim in summary.claims:
            counts[claim] = counts.get(claim, 0) + 1
    counts[Claim.CONVERSATION] = len(conversations)
    counts[Claim.DOCUMENT_WITHOUT_CARD] = len(without_card)
    attention = Attention(
        yours=claim_counts(Meaning.YOURS, counts),
        broken=claim_counts(Meaning.BROKEN, counts),
        live=claim_counts(Meaning.LIVE, counts),
        unplanned_defects=unplanned(SuggestionKind.DEFECT),
        unplanned_ideas=unplanned(SuggestionKind.IDEA),
        arrived_today=sum(1 for s in shown if s.is_new),
    )
    return BoardState(
        project=project,
        version=version,
        generated_at=now,
        corpus=corpus_summary(index, watching=watching, watch_note=watch_note),
        attention=attention,
        trunk=trunk,
        machine=machine,
        dial=dial,
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
    reading: WindowlessSession | None = None,
    heard: HeardMark | None = None,
    machine: MachineState | None = None,
    planning: WindowlessSession | None = None,
) -> CardDetail:
    """`readings` newest first; `read` is whether the loop has read the
    machine; `folded` the cards folded under this one; `reading` the
    session reading its signal right now; `machine` what the loop read of
    the machine, whose roles the plan's handouts are checked against;
    `planning` the dial's session writing the card's plan (plan 11)."""
    document = document_of(card, index)
    brief, record = split_rows(card.rows)
    own = cited_path(card)
    signal, signal_note = watch_signal(card)
    trigger, trigger_note = trigger_signal(document)
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
            planning=planning,
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
        trigger=trigger,
        trigger_note=trigger_note,
        readings=readings,
        verdict=verdict,
        verdict_note=verdict_note,
        watercooler=watercooler or [],
        heard=heard,
        handouts=handouts_for(document, machine.roles if machine is not None else None, read=read),
    )
