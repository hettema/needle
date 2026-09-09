"""What the board tells the owner on his screen, and what it asks the page
to put in front of him (card #41).

The board learns a lane ended within a minute and moves the card on; the
owner learned it when he next looked. A notice is the one moment the board
interrupts him: a card the machine moved out of Executing, or a running
card that started waiting on him. It is raised by the board's own move,
through the runtime, never by a read: 0.1's toasts from a poll were its
deepest trap (INTENT, lesson 3).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Moment(StrEnum):
    """Which bell rings: the popup's words say where the card went and why;
    the moment picks the sound."""

    MOVED_ON = "moved on"
    """The machine moved the card out of Executing."""
    NEEDS_YOU = "needs you"
    """A running card started waiting on him: a question, a stop, a prompt."""


class Notice(BaseModel):
    project: str
    """The project's slug: the board the button opens."""
    project_name: str
    card_number: int
    title: str
    words: str
    """Where the card went and why, or what it is waiting on: the popup's body."""
    moment: Moment


class Told(BaseModel):
    """What became of a notice: raised on his screen, or why it could not
    be. Either way the card's `told` row carries the words, so the record
    says what he was told and when."""

    raised: bool
    words: str


class Shown(BaseModel):
    """What the runtime asked the page to put in front of him: the card the
    notification's button named. Carried on the stream, never in the
    board's state — it is a request to the page, not a fact about a card."""

    id: int
    """Counts up per request, so a page tells a new one from the one it acted on."""
    project: str
    card_number: int
    at: datetime


class Said(BaseModel):
    """What a verb did, in a sentence: what `needle show` answers."""

    said: str
