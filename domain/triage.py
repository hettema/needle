"""Who a defect belongs to, verified before it routes (plan 59).

A defect's `Fix:` mark is written by the session that found it, from inside
its own context, and until this plan nothing read it again. The measurement
that opened the card: eight live `his` defects, the oldest 41 days, zero
answers ever given — and five of the eight were execution mislabelled by
the finder. So the mark alone no longer routes. A second reading, with no
share of the finder's context, verifies the mark against the source it
cites and lands one typed result; the routing state every reader shows is
derived from the document's mark and that result together, by one function
(`board/triage.py::routing_of`), and never by matching words.

Two rules hold the whole thing, and both are in `routing_of`:

- **A row may make routing stricter at once, never looser.** `his` or
  `cannot tell` on a document marked `now` closes the dial the moment it
  lands. `now` on a document marked `his`, `when` or nothing authorises
  nothing until a session has rewritten the mark in a commit that cites the
  row; the row records the verified decision and the document stays the
  routing fact.
- **An unmarked defect is nobody's yet.** It was his by default before this
  plan, applied once by the session that filed it, which is how the pile
  grew without anyone deciding anything.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from domain.card import Actor


class TriageResult(StrEnum):
    """What one independent reading of a defect lands, through `needle triage`."""

    NOW = "now"
    """The written record selects this outcome and the machine may act on
    it: the words name the resolved source and the proposition in it."""
    HIS = "his"
    """The record does not select among outcomes the owner owns, or acting
    would create exposure past a bound he has authorised."""
    WHEN = "when"
    """It waits for a trigger the board can read, in the WATCH grammar."""
    SPLIT = "split"
    """The document holds an outcome the record selects beside one it does
    not; the halves and their sources are named and a corpus lane separates
    them (plan 59, item 4). The reading authorises neither half."""
    CANNOT_TELL = "cannot-tell"
    """The evidence that would decide it is missing; the words say what is
    missing and where it should come from. The card stays nobody's."""


class Direction(StrEnum):
    """Which way a colleague-taken decision moved the product, from a fixed
    set (plan 59, item 6). The set is small on purpose: a free-text
    direction cannot be added up, and the drift the loop looks for is the
    sum — twenty decisions each locally right, all pushing one way, with no
    single citation saying so."""

    SURFACE_ADDED = "surface added"
    SURFACE_REMOVED = "surface removed"
    STRICTNESS_RAISED = "strictness raised"
    STRICTNESS_LOWERED = "strictness lowered"
    AUTOMATION_INCREASED = "automation increased"
    AUTOMATION_DECREASED = "automation decreased"
    BOUND_USED = "a spend or risk bound used"
    NONE = "no direction"
    """It restored an invariant already written; the product moved nowhere."""


class Routing(StrEnum):
    """Where a defect routes right now: the one state the CLI, the dial and
    the page all read from `board/triage.py::routing_of`. Distinct from
    `FixMark`, which stays three values because an unmarked document is
    itself meaningful."""

    NEEDS_TRIAGE = "needs triage"
    """Nobody's yet: no reading has verified the mark, or the reading
    verified something the document does not authorise."""
    TRIAGED_NOW = "triaged now"
    """The document says `now` and a fresh reading agrees: the dial may take it."""
    TRIAGED_HIS = "triaged his"
    """A reading says the decision is the owner's: his door opens."""
    TRIAGED_WHEN = "triaged when"
    """A reading says it waits for a trigger; the document's trigger governs."""
    CANNOT_TELL = "cannot tell"
    """The reading could not settle it and said what is missing."""
    STALE = "stale"
    """A reading exists and the text it judged has changed underneath it: a
    second pair of eyes verifies today's proposition, never yesterday's."""


ROUTES_TO_THE_MACHINE: frozenset[Routing] = frozenset({Routing.TRIAGED_NOW})
"""The one state from which the dial may plan a defect without the owner."""

ROUTES_TO_THE_OWNER: frozenset[Routing] = frozenset({Routing.TRIAGED_HIS})
"""The one state that puts a defect on the owner's pile and opens Answer."""


class Routed(BaseModel):
    """A defect's routing state and the sentence that says why, in the words
    the rail, the card and `needle fixes` all print."""

    state: Routing
    why: str
    """One sentence, from facts the card or its document carries."""


class Source(BaseModel):
    """What a triage reading relied on, resolved: the reference as written,
    where it landed, and the fingerprint of what was read there. A reference
    that resolved nowhere carries no text and no fingerprint — and cannot
    produce `now`."""

    ref: str
    """As the reading named it: a path, or `#N` for a card."""
    path: str | None
    """Relative to the project root, when the reference resolved to a file."""
    text: str | None
    """What was read there, capped; None when it resolved nowhere."""
    fingerprint: str | None
    note: str
    """How it resolved, or why it did not, in one sentence."""


class Triage(BaseModel):
    """One reading's result, as the record keeps it. The `TRIAGED` row on
    the card is this sentence for the owner to read; this is the fact the
    dial reads, because a row is prose and prose cannot carry a
    fingerprint."""

    id: int
    project: str
    card_number: int
    at: datetime
    actor: Actor
    result: TriageResult
    words: str
    """What the result must name, in the reading's own words."""
    decision: str
    """The decision identity minted here, carried through every SPLIT row,
    the plan the dial writes, the fix lane, the fold and anything later
    (plan 59, item 6)."""
    parent: str | None
    """The decision this one continues: the split it came out of, or the
    owner's ruling it applies. None for a decision that starts here."""
    direction: Direction | None
    """Which way it moved the product; required for `now`, absent for a
    reading that authorises nothing."""
    source_ref: str | None
    source_path: str | None
    source_fingerprint: str | None
    """The source text as the reading resolved it. Eligibility re-reads and
    re-fingerprints; a mismatch is `stale`."""
    document_fingerprint: str
    """The suggestion text this result classified."""
    session_id: str | None
    """The triage session that landed it; None when the owner ruled by hand."""


class Fate(BaseModel):
    """Where one colleague-taken decision ended up, from what the board
    already holds: no new bookkeeping, so the fate cannot drift from the
    facts it is read off."""

    planned: bool
    started: bool
    folded: bool
    reverted: bool
    defect_filed_against: bool
    stage: str | None
    """The fix lane's stage, when the dial ran one; None when it did not."""
    words: str
    """The fate in one sentence, for the cold audit the loop asks for."""


class Decision(BaseModel):
    """One line of `needle fixes` decisions: a decision a colleague took off
    the owner's rail, with its source, its direction and its fate."""

    decision: str
    parent: str | None
    project: str
    card_number: int
    title: str
    at: datetime
    result: TriageResult
    words: str
    direction: Direction | None
    source: str
    """The source as the reading resolved it, or why it resolved nowhere."""
    routing: Routing
    """Where the card routes now: a decision whose row went stale says so."""
    fate: Fate


class CorpusLaneKind(StrEnum):
    """What a corpus lane was opened to write. Both write the corpus and
    nothing else, both run in an isolated worktree, and neither authorises
    what it writes — the record it carries did (plan 59, items 4 and 5)."""

    SPLIT = "split"
    """Separates the settled half of a document from the unsettled one."""
    RULING = "ruling"
    """Rewrites a mark to what the owner's answer settled, citing his row."""


class CorpusLane(BaseModel):
    """One short lane the board opened to write the corpus, and how it went.
    Kept apart from the lane record a card carries, because a corpus lane is
    not the card's lane: it puts no plan into execution and the card never
    moves to Executing for it."""

    id: int
    project: str
    card_number: int
    kind: CorpusLaneKind
    decision: str
    name: str
    """The worktree's name; never `card-<n>-…`, so the lane loop does not
    read it as the card's own lane."""
    path: str | None
    session_id: str | None
    attempt: int
    """Which try this is: the board retries a lane that died before its
    commit, once, and then leaves the half-state on the card in words."""
    opened_at: datetime
    ended_at: datetime | None
    note: str | None
    """Why it ended, when it did."""
    applied: bool
    """The corpus now says what the lane was opened to write: read from the
    documents, never from the lane's own claim."""
