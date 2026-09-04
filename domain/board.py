"""What the page receives: the board assembled, and one card in full."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.audit import AuditEntry
from domain.card import Card, Place
from domain.column import ColumnDefinition
from domain.corpus import CorpusSummary
from domain.document import Document, DocumentRef, DocumentState
from domain.gate import Gate
from domain.lane import Doors, Lane, LaneState
from domain.project import Project
from domain.row import Row
from domain.signal import Reading, Signal


class EssenceSource(StrEnum):
    CARD = "card"
    """The card's own SERVES row."""
    DOCUMENT = "document"
    """The first sentence of the document's intent, standing in."""


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


class GroupView(BaseModel):
    name: str | None
    cards: list[CardSummary]


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
    lanes_ended: int
    """Lanes whose session is gone without a close: Resume or Look is your choice."""
    signals_due: int
    """Executed cards past their signal's due time with nothing delivered yet."""
    arrived_today: int
    documents_gone: int
    documents_without_card: int


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
