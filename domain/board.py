"""What the page receives: the board assembled, and one card in full."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.audit import AuditEntry
from domain.card import Card, Place
from domain.column import ColumnDefinition
from domain.corpus import CorpusSummary
from domain.document import Document, DocumentRef, DocumentState, SuggestionKind
from domain.evidence import Standing
from domain.gate import Gate
from domain.lane import Collision, Conversation, Door, Doors, Lane, LaneState, Readiness
from domain.project import Project
from domain.row import Row
from domain.signal import Reading, ReadingSession, Signal, SignalKind
from domain.verdict import Verdict, VerdictLine
from domain.watercooler import WatercoolerLine


class EssenceSource(StrEnum):
    CARD = "card"
    """The card's own SERVES row."""
    DOCUMENT = "document"
    """The first sentence of the document's intent, standing in."""


class FoldedCard(BaseModel):
    """A card carried under another: its suggestion is in that card's plan (plan 06, item 5)."""

    number: int
    title: str
    document_path: str | None


class CardSummary(BaseModel):
    """A card at rest: what the column shows."""

    number: int
    title: str
    essence: str | None
    essence_source: EssenceSource | None
    gate: Gate | None
    tags: list[str]
    document_state: DocumentState
    document_path: str | None
    """The cited path, whether or not it exists."""
    kind: SuggestionKind | None
    """A suggestion's kind, from its document; None behind a plan or a note."""
    readiness: Readiness | None
    """Whether the card can start now, in Planned and Up next; None elsewhere (plan 06, item 3)."""
    start: Door | None
    """The Start door, on the collapsed face where it is open; None outside Planned and Up next."""
    plan: Door | None
    """The Plan door, on every suggestion card; None behind a plan or a note (plan 06, item 5)."""
    folded: list[FoldedCard]
    """The cards folded under this one: the suggestions its plan carries."""
    points: int
    """Rows on the card, the essence aside."""
    is_new: bool
    """Arrived within the last day (comp 1, call 1)."""
    age_date: date
    """The document's date, else the day the card was born; the Age lens."""
    place: Place
    lane_state: LaneState
    lane_sentence: str | None
    """What the card says about its lane, when it has one."""
    colliding: Collision | None
    """The lane has drifted into another live lane's files, named (plan 07, item 2)."""
    standing: Standing
    """Who placed the card here, on what evidence, and whether it holds on this read."""
    reading: ReadingSession | None
    """The session reading the card's signal right now, when one runs (plan 09, item 1)."""


class GroupView(BaseModel):
    name: str | None
    cards: list[CardSummary]
    rail: bool
    """Backlog's defects rail: pinned at the column's top, above the idea
    groups, with its own count (plan 06, item 2)."""


class ColumnView(BaseModel):
    definition: ColumnDefinition
    groups: list[GroupView]
    count: int


class Attention(BaseModel):
    """The first inch: does anything need me?"""

    asking_you: int
    """Cards in Decision moment, lanes stopped with a question, and signals only you can read."""
    in_flight: int
    """Lanes with hands on them."""
    colliding: int
    """Live lanes editing a file another live lane is also editing (plan 07, item 2)."""
    in_discussion: int
    """Conversations alive right now: ideas and card discussions (plan 07, item 1)."""
    lanes_ended: int
    """Lanes whose session is gone without a close: Resume or Look is your choice."""
    signals_due: int
    """Executed cards past their signal's due time with nothing delivered yet."""
    signals_asking: int
    """Shipped cards waiting on your reading: a signal only you can read, due
    now, or one a session read and could not tell (plan 04; plan 09, item 4)."""
    signals_reading: int
    """Shipped cards whose signal a session is reading right now (plan 09, item 1)."""
    doubted: int
    """Machine-placed cards whose evidence is gone on this read."""
    verdicts_unread: int
    """Cards carrying a verdict the owner has not yet accepted or overturned (plan 05)."""
    unplanned_defects: int
    """Defects written up as suggestions that no plan carries yet (plan 06, item 2)."""
    unplanned_ideas: int
    """Ideas written up as suggestions that no plan carries yet: the size of the unplanned pile."""
    arrived_today: int
    documents_gone: int
    documents_without_card: int


class OwnerAsk(BaseModel):
    """One shipped card waiting on the owner's reading, in the batched list:
    a signal only he can read, or one a session read and could not tell,
    with the session's words (plan 09, item 4)."""

    number: int
    title: str
    what: str
    """The question, as the WATCH row's `what`."""
    due: date
    kind: SignalKind
    evidence: str | None
    """A session's cannot-tell finding, in its words; None for an owner's own signal."""


class TrunkState(BaseModel):
    """The project's main checkout against `origin/develop`, as the runtime last kept it."""

    level: bool | None
    """True when the checkout is at origin/develop; None when never read."""
    behind: int
    note: str | None
    """Why it could not be levelled, when it could not; shown on the attention rail."""
    read_at: datetime | None


class MachineState(BaseModel):
    """Whether the runtime can reach what it needs on this machine."""

    missing: list[str]
    """Commands the runtime needs and cannot find, by name."""


class BoardState(BaseModel):
    project: Project
    version: int
    """Bumps on every write; the stream carries it so the page knows to refetch."""
    generated_at: datetime
    corpus: CorpusSummary
    attention: Attention
    trunk: TrunkState
    machine: MachineState
    columns: list[ColumnView]
    documents_without_card: list[DocumentRef]
    asks: list[OwnerAsk]
    """Every shipped card waiting on the owner's reading, one click each way per card."""
    verdicts: list[VerdictLine]
    """Every card carrying an unread verdict, for the triage lens (plan 05)."""
    conversations: list[Conversation]
    """Every conversation alive right now, as the rail lists them (plan 07, item 1)."""
    watercooler: list[WatercoolerLine]
    """The project's watercooler, newest last; the page shows its last line on every live card."""


class ProjectFile(BaseModel):
    """A document from the project's docs/, read whole at the moment asked for."""

    path: str
    text: str
    read_at: datetime


class CardDetail(BaseModel):
    """A card opened: the five sections, in their fixed order."""

    card: Card
    summary: CardSummary
    brief: list[Row]
    record: list[Row]
    document: Document | None
    other_citations: list[str]
    history: list[AuditEntry]
    lane: Lane | None
    doors: Doors
    signal: Signal | None
    """The signal the card's WATCH row names, when one parses."""
    signal_note: str | None
    """Why the WATCH row names no signal the board can read, when it does not."""
    readings: list[Reading]
    verdict: Verdict | None
    """The verdict the card's VERDICT row names, when one parses."""
    verdict_note: str | None
    """Why the VERDICT row names no verdict the board can act on, when it does not."""
    watercooler: list[WatercoolerLine]
    """The project's watercooler, newest last: what a lane on this card reads."""
