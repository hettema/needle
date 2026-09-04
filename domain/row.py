"""The rows a card carries: labelled sentences written by the owner or a session.

Every row kind belongs to one half of the card. The essence is the card's own
words for what it makes true; the brief is what is true before the work; the
record is what is true after. The halves are fixed here so a new row kind must
declare where it lives, and the page can show a card's shape from three feet
away.
"""

from enum import StrEnum

from pydantic import BaseModel


class RowHalf(StrEnum):
    ESSENCE = "essence"
    BRIEF = "brief"
    RECORD = "record"


class RowKind(StrEnum):
    SERVES = "SERVES"
    TODAY = "TODAY"
    COST = "COST"
    YOUR_TIME = "YOUR TIME"
    WAITS = "WAITS"
    PLAN = "PLAN"
    REC = "REC"
    Q = "Q"
    ASK = "ASK"
    WHY = "WHY"
    WHY_NOW = "WHY NOW"
    STAKES = "STAKES"
    STATE = "STATE"
    ITEMS = "ITEMS"
    OPEN = "OPEN"
    WHAT = "WHAT"
    WEEK = "WEEK"
    DELIVERED = "DELIVERED"
    WATCH = "WATCH"
    REVIEW = "REVIEW"
    RULING = "RULING"
    RULED = "RULED"
    DONE = "DONE"


ROW_HALF: dict[RowKind, RowHalf] = {
    RowKind.SERVES: RowHalf.ESSENCE,
    RowKind.TODAY: RowHalf.BRIEF,
    RowKind.COST: RowHalf.BRIEF,
    RowKind.YOUR_TIME: RowHalf.BRIEF,
    RowKind.WAITS: RowHalf.BRIEF,
    RowKind.PLAN: RowHalf.BRIEF,
    RowKind.REC: RowHalf.BRIEF,
    RowKind.Q: RowHalf.BRIEF,
    RowKind.ASK: RowHalf.BRIEF,
    RowKind.WHY: RowHalf.BRIEF,
    RowKind.WHY_NOW: RowHalf.BRIEF,
    RowKind.STAKES: RowHalf.BRIEF,
    RowKind.STATE: RowHalf.BRIEF,
    RowKind.ITEMS: RowHalf.BRIEF,
    RowKind.OPEN: RowHalf.BRIEF,
    RowKind.WHAT: RowHalf.BRIEF,
    RowKind.WEEK: RowHalf.BRIEF,
    RowKind.DELIVERED: RowHalf.RECORD,
    RowKind.WATCH: RowHalf.RECORD,
    RowKind.REVIEW: RowHalf.RECORD,
    RowKind.RULING: RowHalf.RECORD,
    RowKind.RULED: RowHalf.RECORD,
    RowKind.DONE: RowHalf.RECORD,
}

LEAD_ROWS: frozenset[RowKind] = frozenset({RowKind.TODAY})
"""The row that leads the brief, drawn in the accent."""

LANDED_ROWS: frozenset[RowKind] = frozenset({RowKind.DELIVERED})
"""The row that says it shipped, drawn in green."""

ASK_ROWS: frozenset[RowKind] = frozenset({RowKind.WATCH, RowKind.YOUR_TIME, RowKind.ASK, RowKind.Q})
"""Rows that are the owner's move, drawn in amber."""


class Row(BaseModel):
    kind: RowKind
    text: str
    """Plain text; backticks mark code and double asterisks mark bold."""
