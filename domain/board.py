"""What the page receives: the board assembled, and one card in full."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.audit import AuditEntry
from domain.card import Card, Place
from domain.column import ColumnDefinition
from domain.corpus import CorpusSummary
from domain.dial import DialState
from domain.document import Document, DocumentRef, DocumentState, Fix, SuggestionKind
from domain.evidence import Standing
from domain.gate import Gate
from domain.handout import Handouts
from domain.hook import HeardMark
from domain.lane import Collision, Conversation, Doors, Lane, LaneState, Progress
from domain.project import Project
from domain.row import Row
from domain.signal import Reading, Signal, SignalKind, WindowlessSession
from domain.verdict import Verdict, VerdictLine
from domain.watercooler import WatercoolerLine


class EssenceSource(StrEnum):
    CARD = "card"
    """The card's own SERVES row."""
    DOCUMENT = "document"
    """The first sentence of the document's intent, standing in."""


class FoldedCard(BaseModel):
    """A card carried under another: its suggestion is in that card's plan (plan 06, item 5)."""

    number: int
    title: str
    document_path: str | None


class Meaning(StrEnum):
    """The colour language's five words (plan 27). Every colour on the board
    says one of these and nothing else; the page paints a meaning, never a
    count, a category, a button or a column."""

    YOURS = "yours"
    """Amber: only you can act."""
    BROKEN = "broken"
    """Red: evidence is gone or two things disagree."""
    LIVE = "live"
    """Teal: happening right now."""
    PROVEN = "proven"
    """Green: the loop closed."""
    QUIET = "quiet"
    """Grey: information with no claim on you."""


class Claim(StrEnum):
    """What can claim the owner's eye, one kind per value. The head counts
    each and filters the board to the cards carrying it (plan 27, item 1)."""

    VERDICT = "verdict"
    LANE_ASKING = "lane asking"
    SIGNAL_ASKING = "signal asking"
    DECISION = "decision"
    LANE_ENDED = "lane ended"
    DOUBTED = "doubted"
    SIGNAL_OVERDUE = "signal overdue"
    DOCUMENT_GONE = "document gone"
    COLLIDING = "colliding"
    DOCUMENT_WITHOUT_CARD = "document without card"
    NO_REVIEW = "no review"
    """Shipped by a close, with no REVIEW row: a close that slipped past the
    refusal by another door (plan 11, item 1)."""
    LANE_WORKING = "lane working"
    CONVERSATION = "conversation"
    SIGNAL_READING = "signal reading"
    PLANNING = "planning"
    """A defect the dial is planning right now (plan 11, item 4)."""


CLAIM_MEANING: dict[Claim, Meaning] = {
    Claim.VERDICT: Meaning.YOURS,
    Claim.LANE_ASKING: Meaning.YOURS,
    Claim.SIGNAL_ASKING: Meaning.YOURS,
    Claim.DECISION: Meaning.YOURS,
    Claim.LANE_ENDED: Meaning.BROKEN,
    Claim.DOUBTED: Meaning.BROKEN,
    Claim.SIGNAL_OVERDUE: Meaning.BROKEN,
    Claim.DOCUMENT_GONE: Meaning.BROKEN,
    Claim.COLLIDING: Meaning.BROKEN,
    Claim.DOCUMENT_WITHOUT_CARD: Meaning.BROKEN,
    Claim.NO_REVIEW: Meaning.BROKEN,
    Claim.LANE_WORKING: Meaning.LIVE,
    Claim.CONVERSATION: Meaning.LIVE,
    Claim.SIGNAL_READING: Meaning.LIVE,
    Claim.PLANNING: Meaning.LIVE,
}
"""Which of the three head words each claim counts under; the two other
meanings never claim anyone."""


class LoopState(StrEnum):
    OPEN = "open"
    """Shipped; the signal is named and not yet read as delivered."""
    CLOSED = "closed"
    """The signal was read as delivered, or the card is Done."""


class Loop(BaseModel):
    """A shipped card's loop as the glyph carries it (plan 27, item 3): an
    open ring in ink, a filled green dot; the ring is amber when only the
    owner can read the signal."""

    state: LoopState
    owner_only: bool


class FaceDoorName(StrEnum):
    """What the one door on a collapsed card does when pressed."""

    START = "start"
    PLAN = "plan"
    WATCH = "watch"
    OPEN = "open"
    """Opens the card: the act the state asks for lives on the open face."""


class FaceDoor(BaseModel):
    """The one door a state allows on the collapsed face, bottom-right. A door
    is a shape, never a colour: filled when it is the card's primary act."""

    name: FaceDoorName
    label: str
    why: str
    primary: bool


class CardState(BaseModel):
    """The state line on a collapsed card (plan 27, item 2): one word in its
    meaning's colour, always bottom-left, and the one door that state allows
    or, when none opens, what opening the card gives. Named by one function
    in `board.assemble`; the page never invents a word."""

    word: str
    meaning: Meaning
    detail: str | None
    """What the state has to say in the essence's place: a lane's question,
    a doubt's words, a signal's what and when."""
    loop: Loop | None
    door: FaceDoor | None
    hint: str | None
    """Grey text where the door would be, when no door opens: "open to see"."""


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
    kind: SuggestionKind | None
    """A suggestion's kind, from its document; None behind a plan or a note."""
    fix: Fix | None
    """A suggestion's `Fix:` mark, from its document (plan 11, item 2); None
    behind a plan or a note, and None for an unmarked suggestion, which the
    face says."""
    state: CardState
    """The state line: one word, its meaning, the one door (plan 27, item 2)."""
    claims: list[Claim]
    """Every claim this card makes on the owner's eye; the head filters by them."""
    folded: list[FoldedCard]
    """The cards folded under this one: the suggestions its plan carries."""
    is_new: bool
    """Arrived within the last day (comp 1, call 1)."""
    age_date: date
    """The document's date, else the day the card was born; the Age lens."""
    place: Place
    lane_state: LaneState
    colliding: Collision | None
    """The lane has drifted into another live lane's files, named (plan 07, item 2)."""
    progress: Progress | None
    """How far the lane has come, in its own words, while a session has
    hands on the card (plan 13); None otherwise, and None for a plan with
    no items, which shows the signed card."""
    standing: Standing
    """Who placed the card here, on what evidence, and whether it holds on this read."""
    reading: WindowlessSession | None
    """The session reading the card's signal right now, when one runs (plan 09, item 1)."""
    planning: WindowlessSession | None
    """The session the dial has planning this defect right now, when one
    runs (plan 11, item 4)."""


class GroupView(BaseModel):
    name: str | None
    cards: list[CardSummary]
    rail: bool
    """Backlog's defects rail: pinned at the column's top, above the idea
    groups, with its own count (plan 06, item 2)."""


class ColumnView(BaseModel):
    definition: ColumnDefinition
    groups: list[GroupView]
    count: int


class ClaimCount(BaseModel):
    """One line of the head's breakdown: how many carry the claim, in words."""

    claim: Claim
    count: int
    label: str
    """The count's words, in number: "lanes asking you", "lane asking you"."""


class Attention(BaseModel):
    """The first inch: does anything need me? Three words on the head, each
    the sum of its claims, and the quiet facts that claim nobody (plan 27,
    item 1). A claim with a count of zero is not listed."""

    yours: list[ClaimCount]
    """Only you can act: verdicts to accept, lanes asking, signals only you
    can read, cards in Decision moment."""
    broken: list[ClaimCount]
    """Evidence gone or two things disagreeing: lanes died, statuses doubted,
    signals the board said it would read and has not, documents nowhere, two
    lanes in one file, documents with no card."""
    live: list[ClaimCount]
    """Happening now: lanes working, conversations, signals being read."""
    unplanned_defects: int
    """Defects written up as suggestions that no plan carries yet (plan 06, item 2)."""
    unplanned_ideas: int
    """Ideas written up as suggestions that no plan carries yet: the size of the unplanned pile."""
    arrived_today: int


class OwnerAsk(BaseModel):
    """One shipped card waiting on the owner's reading, in the batched list:
    a signal only he can read, or one a session read and could not tell,
    with the session's words (plan 09, item 4)."""

    number: int
    title: str
    what: str
    """The question, as the WATCH row's `what`."""
    due: date
    kind: SignalKind
    evidence: str | None
    """A session's cannot-tell finding, in its words; None for an owner's own signal."""


class TrunkState(BaseModel):
    """The project's main checkout against `origin/develop`, as the runtime last kept it."""

    level: bool | None
    """True when the checkout is at origin/develop; None when never read."""
    behind: int
    note: str | None
    """Why it could not be levelled, when it could not; shown on the attention rail."""
    read_at: datetime | None


class MachineState(BaseModel):
    """Whether the runtime can reach what it needs on this machine, and what
    the machine names that a plan may name too."""

    missing: list[str]
    """Commands the runtime needs and cannot find, by name."""
    roles: list[str] | None = None
    """The roles the machine's roles file names, in file order; None when
    the machine has no roles file (plan 12, item 2)."""


class BoardState(BaseModel):
    project: Project
    version: int
    """Bumps on every write; the stream carries it so the page knows to refetch."""
    generated_at: datetime
    corpus: CorpusSummary
    attention: Attention
    trunk: TrunkState
    machine: MachineState
    dial: DialState
    """The owner's standing ruling on defects, one for the whole board, with
    the fix lanes live against its number (plan 11, item 3)."""
    columns: list[ColumnView]
    documents_without_card: list[DocumentRef]
    asks: list[OwnerAsk]
    """Every shipped card waiting on the owner's reading, one click each way per card."""
    verdicts: list[VerdictLine]
    """Every card carrying an unread verdict, for the triage lens (plan 05)."""
    conversations: list[Conversation]
    """Every conversation alive right now, as the rail lists them (plan 07, item 1)."""
    watercooler: list[WatercoolerLine]
    """The project's watercooler, newest last; the page shows its last line on every live card."""


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
    lane: Lane | None
    doors: Doors
    signal: Signal | None
    """The signal the card's WATCH row names, when one parses."""
    signal_note: str | None
    """Why the WATCH row names no signal the board can read, when it does not."""
    trigger: Signal | None
    """The signal a defect's `Fix: when` trigger names, when one parses: read
    by the signal loop as an Executed card's WATCH row is (plan 11, item 5)."""
    trigger_note: str | None
    """Why the trigger names no signal the board can read, when it does not."""
    readings: list[Reading]
    verdict: Verdict | None
    """The verdict the card's VERDICT row names, when one parses."""
    verdict_note: str | None
    """Why the VERDICT row names no verdict the board can act on, when it does not."""
    watercooler: list[WatercoolerLine]
    """The project's watercooler, newest last: what a lane on this card reads."""
    heard: HeardMark | None
    """When this card's lane last heard the board inside its session, and
    what (plan 10, item 1); None when it has never been told anything."""
    handouts: Handouts
    """What the plan hands out, per item, against the machine's roles (plan 12, item 2)."""
