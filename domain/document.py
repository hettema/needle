"""A document in a project's corpus: a plan or a suggestion, read from its file.

A document is the substance of a card. Everything here is read from the file
at the moment of the read and nothing is stored, so a plan edited in the repo
is right on the board a second later with nobody syncing anything.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.gate import Gate


class DocumentKind(StrEnum):
    PLAN = "plan"
    SUGGESTION = "suggestion"


class DocumentState(StrEnum):
    """What is written behind a card — five states, and a card always shows one."""

    PLAN = "plan"
    SUGGESTION = "suggestion"
    ARCHIVED = "archived"
    NOTE = "note"
    """Nothing written behind the card (owner ruling 2)."""
    GONE = "gone"
    """The card cites a document that is nowhere — the one red state."""


class HeadField(BaseModel):
    """One `**Key:** value` line from the head of a document, in file order."""

    key: str
    value: str


class Document(BaseModel):
    kind: DocumentKind
    stem: str
    """The file name without its folder or extension: the document's identity."""
    path: str
    """Relative to the project root."""
    archived: bool
    title: str
    date: date | None
    """From the stem's leading YYYY-MM-DD, when it has one."""
    status: str | None
    """The whole Status line after the key."""
    status_word: str | None
    """The first word of the Status line, upper-cased: PENDING, DONE, ..."""
    gate: Gate | None
    gate_why: str | None
    sequencing: str | None
    found_by: str | None
    card_ref: int | None
    """A `**Card:** #N` line names the card this document belongs to."""
    head_fields: list[HeadField]
    intent_heading: str | None
    intent: str
    """The body of the intent section, as markdown."""
    essence: str | None
    """The first sentence of the intent, for a card with no words of its own."""
    read_at: datetime


class DocumentRef(BaseModel):
    """Enough of a document to name it on the page."""

    kind: DocumentKind
    stem: str
    path: str
    title: str
