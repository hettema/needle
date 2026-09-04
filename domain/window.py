"""A window into a session: a terminal the compositor places by its app-id.

The app-id contract is the owner's (2026-09-03): `org.omarchy.<kind>-<card>`,
where the kind is `lane` or `board-<door>`, because his compositor rule sends
those to the board-terminal workspace as tabs in one group.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class WindowKind(StrEnum):
    LANE = "lane"
    """The lane's own window: an attach to its live session."""
    WATCH = "board-watch"
    """A door the owner opened to look at a live session."""
    LOOK = "board-look"
    """A fresh session from a transcript, for a session live nowhere."""
    DISCUSS = "board-discuss"
    """A fresh conversation about a card, never hands on its tree."""
    IDEA = "board-idea"
    """A fresh conversation about nothing yet, in the project's checkout; what
    it writes into the corpus becomes a card (plan 07, item 1)."""
    PLAN = "board-plan"
    """A plan-writing conversation for one suggestion or several, in the
    project's checkout; the plan it writes carries them (plan 06, item 5)."""


class Window(BaseModel):
    id: int
    session_id: str
    kind: WindowKind
    app_id: str
    address: str
    """The compositor's handle for the window; how the runtime knows this one."""
    opened_at: datetime
    closed_at: datetime | None
    """When the runtime found the window gone; the owner closes, the runtime never does."""


class Focused(BaseModel):
    """What a `focus` call answers: the window brought forward, and the app-id
    the compositor reports active afterwards — the proof (plan 04, item 2)."""

    window: Window
    app_id: str


class Opened(BaseModel):
    """What a `window` call answers: the window it proved, and what runs inside."""

    window: Window
    fresh: bool
    """True when the window runs a new session from the transcript, not an attach."""
    banner: str | None
    """The window's first line when it is fresh."""
