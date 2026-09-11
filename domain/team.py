"""The team a card runs with, and what the evidence says about which team
earns its place (card #58).

INTENT.md: the organisation discovers how the colleagues collaborate best
through measured work and preserves what it learns. Before this card the
collaboration was scheduled by the owner — "put this to Codex first" — which
made him the coordination bottleneck the board exists to remove, and no
reading of whether it paid existed anywhere but in his memory. Now every
Start assigns one team from the evidence the corpus, the board and git
already hold, the assignment is written once and never rewritten, and one
reader joins the facts each closed card left behind into a reading per
kind of work. Nothing here is a new measurement: the plan's `Challenged:`
line, the review record's dispositions, the defects filed against a card,
the card's history and the lane's transcripts are the facts, and the store
keeps only the one thing no fact can hold — what was declared before the
work began.

The team is called a *composition* in the plan; the board's word for it is
the team, which is the owner's.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.slot import Make

POLICY = "2026-09-11"
"""The routing policy's version: the date its thresholds were last set.
Every assignment carries it, so a card in flight says which policy chose
its team and a rollback — putting the previous thresholds back in one
change — is visible on every card started after it, and changes none
started before (plan item 4)."""

TRIALS_TO_JUDGE = 3
"""How many closed cards a composition needs under one shape before the
reading judges it: the plan's threshold speaks of "its first three eligible
trials", and below that the reading says exploring, never a winner."""

CORRECTING_TRIALS_TO_EARN = 2
"""A challenge earns the lead when at least this many of its first three
trials produced a material correction before build the accountable hand's
own reading had missed (the plan's Loop)."""

ESCAPE_DAYS = 14
"""A defect filed against a card within this many days of its close is an
escape: the card's quality as the plan measures it, and the one fact that
denies a challenge the lead however many corrections it made."""

EXPLORE_EVERY = 4
"""One card in four explores a composition other than the earned leader
(plan item 4), by the card's own number, so which cards explore is a fact
the owner can read off the board and never a draw."""


class Challenge(StrEnum):
    """Who challenges the accountable hand. There is always exactly one
    accountable hand — the lane's driver, chosen by the one rule — and the
    composition says who reads its work before it builds and after."""

    ALONE = "alone"
    """The accountable hand alone: nobody challenges the plan before build.
    The independent review §13 asks of every software change still happens,
    by a cold reader of the hand's own make; the doctrine of 2026-09-11
    postdates this plan and governs it."""
    SAME_MAKE = "same-make"
    """A colleague of the hand's own make challenges the plan before build
    and reads the change cold."""
    DIFFERENT_MAKE = "different-make"
    """A colleague of the other make does both: the composition #59's plan
    ran first, twelve corrections before build."""


class Shape(StrEnum):
    """The kind of work a card is, as far as compositions are compared: a
    finding under one shape says nothing about another, so a harder
    assignment cannot make a composition look worse (plan item 3). Read from
    the card's effort gate, the one fact every started card has."""

    JUDGMENT = "judgment"
    """A card gated high or xhigh: design, where the plan's bootstrap
    explores from #54's and #59's different-make observations."""
    BOUNDED = "bounded"
    """A card gated low or medium: bounded work, which begins with one
    accountable hand."""
    READING = "reading"
    """The triage seat (#59): one reader verifying a mark. Named here
    because the plan calls it a work shape the router decides; the runtime
    gives a windowless seat to one make only (`runtime/launch.py::windowless`)
    and #59 rules the seat one verifier and never a committee, so today
    its one executable composition is the hand alone."""


class Conclusion(StrEnum):
    """What the reading concluded for a shape, and so why a card got the
    team it got."""

    EARNED = "earned"
    """A composition met the predeclared threshold and leads."""
    BEST_QUALITY = "best-quality"
    """No composition met the threshold, and the best quality result leads
    (the plan's Loop), time breaking a quality tie."""
    TIED = "tied"
    """Two compositions do not differ on quality or on efficiency."""
    EXPLORING = "exploring"
    """The evidence is incomplete: the next under-sampled composition is
    chosen without any claim that it is optimal."""
    UNAVAILABLE = "unavailable"
    """Only one composition can be executed for this card, so nothing was
    chosen."""
    STALE = "stale"
    """A model that took part in the observations is not the model that
    would take part now: the old evidence no longer speaks for this shape,
    which returns to exploration."""
    PINNED = "pinned"
    """The card's own plan pinned its composition with a reason — a safety
    or intent constraint — and the router honoured it."""


class Hand(BaseModel):
    """The accountable hand: the make and rung the rule chose to drive."""

    make: Make
    model: str | None
    """The rung's model in the rule's own word; None when the rule named
    none, never a guess (card #63)."""
    slot: str


class Route(BaseModel):
    """The team the router assigns a card, with why: what the reading
    concluded, the observations it rests on and the policy that applied."""

    shape: Shape
    challenge: Challenge
    hand: Hand
    challenger: Make | None
    """The make that challenges: the hand's own under same-make, the other
    under different-make, None when alone."""
    conclusion: Conclusion
    why: str
    observations: list[str]
    """The cards the reading rests on, as `#N`, so every route links to
    its evidence."""
    policy: str = POLICY


class Composition(BaseModel):
    """A card's team as the store holds it: assigned before the work at the
    first Start, and immutable from then — a restart of the card keeps it,
    and no outcome rewrites its experiment (plan item 1)."""

    project: str
    card_number: int
    route: Route
    assigned_at: datetime


class Observation(BaseModel):
    """One closed card as the reader joins its facts: what was declared
    before the work, and what the corpus, the board and git say became of
    it. Every count names where it was read from, so deleting or changing
    the source changes the observation."""

    project: str
    card_number: int
    title: str
    shape: Shape
    challenge: Challenge
    hand_make: Make | None
    hand_model: str | None
    challenger_model: str | None
    """The challenger's model when the declaration named it."""
    declared_in: str
    """Where the composition was declared: the store, or a document's
    `Composition:` line by path."""
    corrections: int | None
    """Material corrections before build, from the plan's `Challenged:`
    line; None when no line says — under a challenge, the invited round
    left no record, which the reading says rather than counting zero."""
    findings: int
    """The review record's findings, all rings."""
    inside: int
    adjacent: int
    outside: int
    """The findings by ring, from each disposition's class: feature is
    inside the change, seam adjacent, boundary outside; the rest are
    counted in `findings` only."""
    escapes: int
    """Live defects filed against the card within ESCAPE_DAYS of its close."""
    stops: int
    """Times the owner or the machine stopped the lane, from the card's history."""
    reverted: bool
    """A commit on the trunk reverts the lane's tip."""
    hours: float | None
    """From the first Start to the close, by the card's history; None while
    the card is not closed."""
    tokens: int | None
    """Tokens the lane's transcripts show, counted once by request; None
    when no transcript could be read, or the make keeps none the reader
    knows."""
    closed_at: datetime | None
    sources: list[str]
    """The facts read, each named: a document path, a review path, a
    suggestion path, `history`, `transcripts`, `git`."""


class Tally(BaseModel):
    """One composition's showing under one shape, over its observations."""

    challenge: Challenge
    trials: int
    correcting: int
    """Trials whose challenge produced at least one material correction
    before build."""
    corrections: int
    unrecorded: int
    """Trials under a challenge whose plan carries no `Challenged:` line."""
    escapes: int
    escaping: int
    """Trials with at least one escape."""
    findings: int
    stops: int
    reverts: int
    hours: float | None
    """Mean hours per closed trial; None when none says."""
    tokens: int | None
    """Mean tokens per trial with a count; None when none has one."""


class ShapeReading(BaseModel):
    """What the evidence says for one shape: each composition's tally, the
    conclusion, and the leader when one earned it."""

    shape: Shape
    observations: list[Observation]
    tallies: list[Tally]
    conclusion: Conclusion
    leader: Challenge | None
    why: str
    confounds: list[str]
    """What the reading cannot separate: mixed hands, unrecorded rounds,
    a sample of one — named so a number is never read as more than it is."""


class TeamReading(BaseModel):
    """The whole reading for one project, as `needle team` and the page
    show it: reproducible from the corpus, the board and git alone."""

    project: str
    policy: str
    shapes: list[ShapeReading]
    assigned: list[Composition]
    """Every team the store holds for the project's cards, oldest first."""
    read_at: datetime
