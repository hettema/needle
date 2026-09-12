"""A project's focus: what matters now, what holds it back, and how every
open card bears on that (card #87).

The theory of constraints says one thing binds a project at a time and work
on anything else is a mirage. The owner ranks by position and gates what
enters execution (INTENT.md); what the board could not tell him was which
of the cards on the plate moves the thing that limits the project now. So a
project can carry a **focus**: two sentences in one document
(`docs/FOCUS.md`), the outcome he wants with its measure and a colleague's
diagnosis of what limits it with its own measure, its evidence, the rival
it rejected and the recheck that would show it wrong. He chooses the
document with one click, bound to the document's fingerprint; a reader of
the other make checks the diagnosis before the click is offered; a reading
of the other make then lands, per open card, whether the card helps remove
the limit, and the Leverage lens shows the board as the focus would arrange
it. Every judgment here binds to a version of what it judged, and a page
that showed yesterday's judgment in today's voice would be the one lie this
board exists to refuse — so a focus is *chosen* only while the document on
disk has the ruling's fingerprint, and a card's reading is *stale* the
moment either the focus or the card's document changes.

What never changes: who ranks and who starts. The lens never writes rank,
the dial never reads a class, and nothing here starts a lane.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from domain.call import HowKnown
from domain.card import Place
from domain.column import Column
from domain.lane import Conversation, Door
from domain.signal import Signal, SignalKind

# ── the document ───────────────────────────────────────────────────────


class Measure(BaseModel):
    """One of the document's two measures — the outcome's, the bottleneck's —
    as written and as read: the line in the WATCH grammar, the signal it
    parses to, or why it does not."""

    line: str | None
    """The head line's value, verbatim; None when the line is missing."""
    signal: Signal | None
    note: str | None
    """Why the line names no signal the board can read, when it does not."""


class FocusDocument(BaseModel):
    """`docs/FOCUS.md` as the board reads it: the head the board needs and
    nothing it does not. The M it lands on is prose in the body, never a
    field, so a project that is not a business can carry a focus."""

    path: str
    fingerprint: str
    """`board/triage.py::fingerprint` of the whole file: what a ruling and
    every reading bind to."""
    title: str
    what_matters: str | None
    """The outcome in the owner's words, without its measure."""
    outcome: Measure
    what_holds: str | None
    """The diagnosis in one sentence, without its measure."""
    bottleneck: Measure
    evidence: str | None
    rival: str | None
    """The explanation rejected and the observation that separates them."""
    recheck: Measure
    """When the diagnosis is due to be read again, as a WATCH line."""
    proposed: str | None
    """Who proposed it and when, as written."""
    doubts: list[str]
    """Every field missing or unreadable, each named; a document with any
    is proposed-with-a-doubt and never chosen."""
    read_at: datetime

    @property
    def complete(self) -> bool:
        return not self.doubts


# ── the ruling and the readings ────────────────────────────────────────


class FocusRuling(BaseModel):
    """The owner's click: use this document, at this fingerprint. The store
    holds the ruling and never the reasoning; an edit after the click is a
    new proposal, never an inherited ruling."""

    id: int
    project: str
    fingerprint: str
    what_matters: str
    """The outcome sentence as it stood at the click, so a changed outcome
    is read as a change and not as a rewording."""
    chosen_at: datetime


class FocusVerdict(StrEnum):
    """What a reader of the other make lands on a proposed diagnosis
    (card #87, item 3), before the ruling is offered."""

    STANDS = "stands"
    DOES_NOT_STAND = "does not stand"
    CANNOT_TELL = "cannot tell"


class FocusCheck(BaseModel):
    """One cold reading of a proposed focus, bound to the document it read."""

    id: int
    project: str
    fingerprint: str
    at: datetime
    verdict: FocusVerdict
    line: str
    how_known: HowKnown | None
    session_id: str | None


class Leverage(StrEnum):
    """How a card bears on the chosen focus (card #87, item 4): four
    classes and a likelihood word, never a score — the evidence supports
    classes, not precision (the plan's rulings)."""

    HELPS_REMOVE = "helps remove this limit"
    PROTECTS = "protects progress"
    DOES_NOT_ADDRESS = "does not address this limit"
    NEEDS_EVIDENCE = "needs evidence"
    """The card's document does not say what it would move; a finding on
    the plan, not on the focus."""


class Likelihood(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LeverageReading(BaseModel):
    """One reading of one card against the chosen focus, bound to both
    fingerprints: the card's document and the focus document. Either
    changing makes it stale, and a stale reading orders nothing."""

    id: int
    project: str
    card_number: int
    at: datetime
    leverage: Leverage
    likelihood: Likelihood | None
    """Required with `helps remove this limit`, absent otherwise."""
    words: str
    """One sentence of why, citing the card's document and the diagnosis."""
    focus_fingerprint: str
    document_fingerprint: str
    session_id: str | None


class RecheckOutcome(StrEnum):
    """What the scheduled reading of the two measures lands (card #87,
    item 6): which link of work → bottleneck → outcome broke, or none.
    The board never turns a missed target into "choose another priority":
    replacing the focus is the owner's ruling through the door."""

    HOLDS = "holds"
    """Both measures read as the diagnosis predicts, or nothing has moved yet."""
    DIAGNOSIS_CHALLENGED = "diagnosis challenged"
    """The bottleneck measure improved and the outcome did not."""
    WORK_NOT_LINKED = "work not linked"
    """The work that said it removes the limit shipped, and the bottleneck
    measure has not improved."""
    EXPIRED = "expired"
    """The recheck date passed and no reading landed: the evidence is stale."""


class FocusRecheck(BaseModel):
    id: int
    project: str
    fingerprint: str
    at: datetime
    outcome: RecheckOutcome
    words: str
    session_id: str | None


class MeasureSide(StrEnum):
    OUTCOME = "outcome"
    BOTTLENECK = "bottleneck"


class MeasureReading(BaseModel):
    """One machine reading of one of the two measures; the first per
    fingerprint and side is the baseline every later one is read against."""

    id: int
    project: str
    fingerprint: str
    side: MeasureSide
    at: datetime
    delivered: bool | None
    words: str
    baseline: bool


# ── what a reader of the other make answers in ─────────────────────────


class CheckAnswer(BaseModel):
    """The shape the cold check of a proposed focus answers in, held by
    Codex's `--output-schema`."""

    model_config = ConfigDict(extra="forbid")

    verdict: FocusVerdict
    line: str
    how_known: HowKnown
    sources: list[str]


class LeverageAnswer(BaseModel):
    """The shape a per-card reading answers in."""

    model_config = ConfigDict(extra="forbid")

    leverage: Leverage
    likelihood: Likelihood | None
    why: str
    how_known: HowKnown
    sources: list[str]


class RecheckAnswer(BaseModel):
    """The shape the scheduled recheck answers in."""

    model_config = ConfigDict(extra="forbid")

    outcome: RecheckOutcome
    words: str
    how_known: HowKnown
    sources: list[str]


class ReadingKind(StrEnum):
    """What a call the focus loop opened was for: the record of readings
    in flight and of readings that died (card #87, items 3, 4 and 6)."""

    CHECK = "check"
    CARD = "card"
    RECHECK = "recheck"


class FocusCall(BaseModel):
    """One call the focus loop made to a colleague of the other make, in a
    fresh thread: what it was for, what it read, and how it ended."""

    id: int
    project: str
    kind: ReadingKind
    card_number: int | None
    fingerprint: str
    """The focus document's fingerprint the reading was opened against."""
    document_fingerprint: str | None
    """A card reading's document fingerprint; None for the other kinds."""
    call_id: int | None
    """The `calls` record `needle wait` reads; None when the call never came alive."""
    session_id: str | None
    opened_at: datetime
    ended_at: datetime | None
    landed: bool
    """The answer landed and its result was recorded."""
    note: str | None
    """How it ended when it landed nothing."""


# ── what the page shows ────────────────────────────────────────────────


class LeverageState(StrEnum):
    """Where one card stands against the chosen focus, as its face says."""

    READ = "read"
    UNREAD = "unread"
    STALE = "stale"
    READING = "reading"
    """A colleague of the other make is reading it right now."""


class CardLeverage(BaseModel):
    """What a card's face shows under the Leverage lens: its class in the
    four plain phrases, its likelihood, the reading's sentence, and the
    hold beside it when the card also waits on another card — impact and
    readiness are two facts (the plan's rulings)."""

    state: LeverageState
    leverage: Leverage | None
    likelihood: Likelihood | None
    words: str | None
    sentence: str
    """One sentence in the one shape (card #75), built by the board."""
    hold: str | None
    """The cards a Sequencing line holds this one on, when any."""
    read_at: datetime | None


class ProposedMove(BaseModel):
    """One move the focus would make, and why; his tick makes it his."""

    number: int
    from_place: Place
    to_place: Place
    why: str
    wake: str | None
    """For a move into Not now: the trigger that wakes the card, in the
    WATCH grammar, written from the focus's recheck line."""


class ArrangedGroup(BaseModel):
    name: str | None
    numbers: list[int]


class ArrangedColumn(BaseModel):
    column: Column
    groups: list[ArrangedGroup]


class Arrangement(BaseModel):
    """The board as the focus would arrange it: one pure function's answer
    (`board/leverage.py::arrange`), read by the page, the verb and the
    tests alike. A view that stores nothing until his click."""

    available: bool
    why: str | None
    """Why the leverage order is unavailable, when it is."""
    columns: list[ArrangedColumn]
    moves: list[ProposedMove]


class AcceptedMove(BaseModel):
    number: int
    from_place: Place
    to_place: Place
    why: str


class Acceptance(BaseModel):
    """One click of "Accept this order": every move it made, with each
    card's place before it, so one click puts every one of them back."""

    id: int
    project: str
    at: datetime
    focus_fingerprint: str
    moves: list[AcceptedMove]
    put_back_at: datetime | None
    note: str | None
    """Moves the store refused at the click, named."""


class Decline(BaseModel):
    """A move the owner left unticked: not proposed again until the focus,
    the card's document or its class changes."""

    id: int
    project: str
    card_number: int
    focus_fingerprint: str
    document_fingerprint: str
    leverage: Leverage
    at: datetime


class FocusState(StrEnum):
    """The strip's state, one of these always."""

    NONE = "no focus"
    OUTCOME_ONLY = "outcome only"
    """The document names what matters and what holds it back is not settled."""
    TALKING = "talking"
    """A conversation is working out what holds it back."""
    ENDED = "ended without"
    """A conversation ended before a focus was written."""
    PROPOSED = "proposed"
    CHOSEN = "chosen"
    PAUSED = "paused"
    """Chosen, and the leverage order is paused: the recheck expired, the
    results challenge the diagnosis, or the outcome sentence changed."""


class Coverage(BaseModel):
    """How much of the board the readings cover, and whether anything
    queued removes the limit at all."""

    assessed: int
    total: int
    unread: int
    needs_evidence: int
    stale: int
    reading: int
    queued_helping: int
    """Cards in Up next read as helping remove the limit."""
    line: str
    """The coverage line: "K queued cards help remove this limit", or
    "Nothing queued is evidenced to remove this limit"."""


class FocusStrip(BaseModel):
    """The strip under the project head, above the columns, visible under
    every lens (card #87, item 5): which focus the board is sorted on, how
    many cards are read, and whether anything queued removes the limit."""

    state: FocusState
    sentence: str
    """The strip's first line, in the plan's own words for the state."""
    what_matters: str | None
    what_holds: str | None
    document: FocusDocument | None
    ruling: FocusRuling | None
    check: FocusCheck | None
    """The other make's reading of the proposed document, when one landed
    on this fingerprint."""
    checking: bool
    """A reading of the proposal is in flight."""
    check_note: str | None
    """Why no reading is offered beside the proposal, when the call ended
    without one: the door is offered with the reason shown."""
    conversation: Conversation | None
    coverage: Coverage | None
    moves_proposed: int
    accepted: Acceptance | None
    """The last acceptance still standing: put-back is offered on it."""
    put_back_offered: bool
    paused: str | None
    """Why the leverage order is paused, in the strip's words; None while it orders."""
    recheck_due: date | None
    recheck: FocusRecheck | None
    measures: list[MeasureReading]
    """The latest reading of each measure, baseline included when it is the only one."""
    talk: Door
    choose: Door
    propose: Door

    @model_validator(mode="after")
    def _chosen_is_bound_to_the_document(self) -> "FocusStrip":
        """A focus is chosen only while the document on disk has the
        ruling's fingerprint (card #87, item 1): the strip cannot be built
        saying otherwise, so the page cannot show yesterday's ruling over
        today's document."""
        if self.state in (FocusState.CHOSEN, FocusState.PAUSED):
            if self.document is None or self.ruling is None:
                raise ValueError("a chosen focus has a document and a ruling")
            if self.document.fingerprint != self.ruling.fingerprint:
                raise ValueError(
                    "a chosen focus's document has the ruling's fingerprint; "
                    f"{self.document.fingerprint} is not {self.ruling.fingerprint}"
                )
        return self


MACHINE_READ_KINDS: frozenset[SignalKind] = frozenset(
    {SignalKind.URL, SignalKind.FILE, SignalKind.COMMAND}
)
"""The measure kinds the board reads itself on the recheck's cadence; a
session measure is read by the recheck's reader, an owner measure by him."""
