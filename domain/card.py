"""A card: a view onto a document, plus what the document cannot hold.

The board stores a card's place (column, group, position), its rows, its
citations and its link to its document. Everything else the page shows about
a card is derived at read time from the document itself.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from domain.column import Column
from domain.document import DocumentKind
from domain.gate import Gate
from domain.row import Row


class Actor(StrEnum):
    """Who made a change to the board."""

    OWNER = "owner"
    SESSION = "session"
    IMPORT = "import"
    CORPUS = "corpus"


class CardOrigin(StrEnum):
    IMPORTED = "imported"
    """Born from Needle 0.1's card file."""
    FOUNDING = "founding"
    """Born from the corpus when the project was registered."""
    ARRIVED = "arrived"
    """Born from a document that landed while the board was watching."""


class Place(BaseModel):
    """Where a card sits: the column, the group within it, and the position."""

    column: Column
    group: str | None
    """The group's name; None is the column's unnamed group."""
    position: int = Field(ge=0)


class DocumentLink(BaseModel):
    """What a card cites, as last seen. Identity is the stem, then the title."""

    kind: DocumentKind
    stem: str
    title: str
    archived: bool


class Card(BaseModel):
    number: int
    project: str
    """The project's slug."""
    place: Place
    title: str
    gate: Gate | None
    """The card's own gate; the document's wins when it has one."""
    tags: list[str]
    deep: str
    """The card's own longer note, from 0.1's `deep`; empty for most cards."""
    citations: list[str]
    """Every path the card cites, in order; the first plan or suggestion is the link."""
    link: DocumentLink | None
    origin: CardOrigin
    born_at: datetime
    rows: list[Row]


class Move(BaseModel):
    """The one write the page makes: put this card there."""

    to: Place
