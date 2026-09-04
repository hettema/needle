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
from domain.project import Project
from domain.row import Row


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
    in_flight: int
    arrived_today: int
    documents_gone: int
    documents_without_card: int


class BoardState(BaseModel):
    project: Project
    version: int
    """Bumps on every write; the stream carries it so the page knows to refetch."""
    generated_at: datetime
    corpus: CorpusSummary
    attention: Attention
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
