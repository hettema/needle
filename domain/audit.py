"""The audit trail: one row per change to a card, from the first commit.

0.1 kept no history, so every card's record starts at the import and says so.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.card import Actor, Place


class AuditKind(StrEnum):
    BORN = "born"
    MOVED = "moved"
    LINKED = "linked"
    RENAMED = "renamed"
    ARCHIVED = "archived"
    RETIRED = "retired"


class AuditEntry(BaseModel):
    id: int
    at: datetime
    actor: Actor
    kind: AuditKind
    card_number: int
    from_place: Place | None
    to_place: Place | None
    detail: str
