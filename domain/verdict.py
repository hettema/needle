"""A verdict on an open card: what class of evidence it carries, the evidence
in a sentence, and where the card should go — a proposal until the owner
accepts or overturns it (plan 05).

Every card outside Done and Not now gets exactly one class. The board
computes the classes it can say from its own facts (a signal read, a signal
only the owner can read, a doubted placement, a stale plan); a session
judges the rest from the corpus (built under another name, superseded, live
and open) and writes the verdict as a VERDICT row. Nothing is moved by a
verdict: the owner accepts it, in batches, and the machine moves the card
with the verdict's reason on its history row and the owner named as the
acceptor.
"""

from enum import StrEnum

from pydantic import BaseModel

from domain.card import Place
from domain.column import Column


class EvidenceClass(StrEnum):
    SHIPPED_SIGNAL_READ = "shipped, signal read"
    """The plan is archived, DELIVERED is written, the signal read delivered."""
    SHIPPED_OWNER_ONLY = "shipped, signal owner-only"
    """The plan is archived, DELIVERED is written, and only the owner can read the signal."""
    BUILT_UNDER_ANOTHER_NAME = "built under another name"
    """A suggestion whose subject an archived plan delivered, cited."""
    SUPERSEDED = "superseded"
    """The intent was overtaken by a later ruling or plan, cited."""
    DOUBTED = "doubted"
    """A machine placement whose evidence is gone; the doubt's own fact decides."""
    STALE_PLAN = "stale plan"
    """A plan in Planned or Up next older than the stated age, with no lane ever."""
    LIVE_AND_OPEN = "live and open"
    """None of the above: open on purpose, with the reason in one line."""


class Verdict(BaseModel):
    evidence_class: EvidenceClass
    evidence: str
    """The evidence in one sentence, citing the plan, ruling or fact it rests on."""
    to: Column | None
    """Where the card should go; None means it stays where it is."""


class VerdictLine(BaseModel):
    """One line of the triage lens: a card, where it sits, and its unread verdict."""

    number: int
    title: str
    place: Place
    verdict: Verdict


class VerdictsRuled(BaseModel):
    """What accepting every verdict in a class answers: how many moved, how
    many stayed, and which were refused with the store's own words."""

    evidence_class: EvidenceClass
    accepted: int
    refused: list[str]
