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

from pydantic import BaseModel, model_validator

from domain.card import Actor
from domain.row import RowKind


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
    WAITING = "waiting"
    """A parked card waits for a signal the board can read, named in the
    WATCH grammar (card #82, item 1); the board writes the row and the
    signal loop owns the card from there."""
    STALE = "stale"
    """A parked card is over — what it asked about ended, and the words say
    what ended it (card #82, item 1). The one exit the door refuses while a
    commitment on the card is unaccounted for (item 3)."""


class Ground(StrEnum):
    """What a reading read (card #82, item 1). One reading, two grounds:
    plan 59's verifies a defect's `Fix:` mark against the source it cites;
    card #82's reads a card parked in the owner's column against the §1
    test. The results share a table and a verb; the ground says which
    results a reading may land and which readers may act on it — routing
    reads marks and never a parked reading."""

    MARK = "mark"
    """A defect's mark, read against its source (plan 59)."""
    PARKED = "parked"
    """A card in Decision moment, read against its own record (card #82)."""


MARK_RESULTS: frozenset[TriageResult] = frozenset(
    {
        TriageResult.NOW,
        TriageResult.HIS,
        TriageResult.WHEN,
        TriageResult.SPLIT,
        TriageResult.CANNOT_TELL,
    }
)
"""What a mark's reading may land."""

PARKED_RESULTS: frozenset[TriageResult] = frozenset(
    {TriageResult.NOW, TriageResult.HIS, TriageResult.WAITING, TriageResult.STALE}
)
"""What a parked card's reading may land (card #82, item 1): what the
record settles is execution (`now`), what waits for a signal is `waiting`,
what is over is `stale`, and what is his is `his` with one line he can
answer. No `cannot-tell`: a decision the evidence cannot settle is his,
with the missing evidence as the line — a card in his column never lands
as nobody's."""


class Commitment(BaseModel):
    """One thing on a parked card nothing accounts for (card #82, item 3):
    which row promised it, the sentence the door and the face say, and
    whether a WATCH row can carry it — a promise to watch something can be
    transferred to a signal the board reads; a question in the owner's
    words, or a ruling nobody has ruled on, cannot. Read from the rows by
    `board/parked.py::commitments_of`, never stored."""

    row: RowKind
    words: str
    transferable: bool


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


class Reach(StrEnum):
    """Who a defect reaches, from the second reading (card #100, ruling 2):
    the outermost person or thing it touches. The doctrine's own cut — §1's
    exposure past a bound is the reach — so a defect that only costs a
    session and one that can spend a client's money never sort together."""

    CLIENT = "client"
    """A client or the public: someone outside sees or bears it."""
    MONEY = "money"
    """A spend, or a bound the owner authorised, is crossed."""
    YOU = "you"
    """A decision or a reading of the owner's."""
    SESSION = "session"
    """A colleague's work or time."""


class Breaks(StrEnum):
    """What a defect breaks, from the second reading (card #100, ruling 2),
    gravest first. *Lies* outranks *loses* because a lie is silent and a
    loss is loud (§5): a partial result reported whole is bad information,
    and every decision built on it inherits the error (§6, §11)."""

    LIES = "lies"
    """Something shown as true is false, or work is reported done that is
    not, and a decision is built on it."""
    LOSES = "loses"
    """Work, data or money that should land does not, or a card cannot move."""
    COSTS = "costs"
    """A retry, a wait, a step done by hand, or output worse or slower than
    it should be; nothing false and nothing lost."""
    LOOKS = "looks"
    """True and readable, only ugly or clumsy."""
    NOTHING = "nothing"
    """The document describes no failure: it is an idea in a defect's
    clothing, and the reading's words say so. Reach and how often are
    empty on such a grade, since nothing bites."""


class Often(StrEnum):
    """How often a defect bites, from the second reading (card #100, ruling 2)."""

    EVERY_TIME = "every-time"
    """Each session, read, close or beat it touches."""
    SOMETIMES = "sometimes"
    ONCE_SEEN = "once-seen"


REACH_WORDS: dict[Reach, str] = {
    Reach.CLIENT: "a client or the public",
    Reach.MONEY: "money",
    Reach.YOU: "you",
    Reach.SESSION: "a session",
}
"""The owner's phrase for each reach: what the face, the verb and the brief
say. The value is the token a reading types; this is what he reads."""

OFTEN_WORDS: dict[Often, str] = {
    Often.EVERY_TIME: "every time",
    Often.SOMETIMES: "sometimes",
    Often.ONCE_SEEN: "once seen",
}

BREAKS_WORDS: dict[Breaks, str] = {
    Breaks.LIES: "shows something false as true",
    Breaks.LOSES: "loses work, data or money, or holds a card still",
    Breaks.COSTS: "costs a retry, a wait or a step by hand",
    Breaks.LOOKS: "only looks wrong",
    Breaks.NOTHING: "describes no failure",
}
"""What each kind of break does, in a sentence the face can carry."""


class Grade(BaseModel):
    """How bad one defect is, as the second reading graded it from the
    document alone (card #100, item 2): three parts in the owner's words,
    each with the reading's words for what in the document selected it. A
    grade is never a number — a number carries no reason a cold audit can
    check — and never free text, which cannot be sorted. The band the
    column is ordered by is computed from the parts
    (`board/triage.py::band_of`) and never landed."""

    breaks: Breaks
    breaks_words: str
    """What in the document says this is what breaks — or, on `nothing`,
    why the document describes no failure."""
    reach: Reach | None
    reach_words: str | None
    often: Often | None
    often_words: str | None

    @model_validator(mode="after")
    def _whole(self) -> "Grade":
        if not self.breaks_words.strip():
            raise ValueError("a grade says what in the document selected what breaks")
        if self.breaks == Breaks.NOTHING:
            if any(
                part is not None
                for part in (self.reach, self.reach_words, self.often, self.often_words)
            ):
                raise ValueError("a grade of nothing names no reach and no how-often")
            return self
        missing = [
            part
            for part, value in (
                ("reach", self.reach),
                ("reach words", self.reach_words),
                ("often", self.often),
                ("often words", self.often_words),
            )
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise ValueError(f"a grade names all three parts with their words; missing {missing}")
        return self


class Band(StrEnum):
    """The ladder the Defects column is ordered by (card #100, ruling 4):
    computed from a grade's parts, never landed. The doctrine's two cuts in
    the order it makes them — harm outside first, then false before lost."""

    HARM_OUTSIDE = "harm outside"
    """Something false or lost that reaches a client, the public or money."""
    LIES = "lies"
    LOSES = "loses"
    COSTS = "costs"
    LOOKS = "looks"
    NOTHING = "nothing"
    """Graded as describing no failure: last of the graded."""


LINE_WORDS: dict[Band, str] = {
    Band.HARM_OUTSIDE: "stops at harm outside",
    Band.LIES: "stops at lies",
    Band.LOSES: "stops at loses",
    Band.COSTS: "stops at costs",
    Band.LOOKS: "stops at looks",
    Band.NOTHING: "takes every defect",
}
"""Where a board's auto-fix stops, in one phrase per rung (card #149, ruling
4): the head, its said-sentence, `needle dial` and `needle fixes` all say
this and nothing else, so the page and the terminal never differ. It lives
here, beside `Band`, because `api/typegen.py` mirrors an enum-to-words map
declared in the same module as its enum into `frontend/src/types/` — which
is what stops a second hand-written copy from drifting, as it already does
for `REACH_WORDS`, `OFTEN_WORDS` and `BREAKS_WORDS`. The last rung is
"takes every defect" because the ladder's own word for it, `nothing`, means
"graded as describing no failure" on a card and would read as "no line"
beside a switch.

Found by the cold read of card #149 (2026-09-15, finding 2): the map was
first written in `board/triage.py` and copied by hand into the page, with
nothing holding the two together."""

EVERY_DEFECT = "every defect"
"""What the owner types to move a line back to the last rung."""


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


class Reason(StrEnum):
    """Which branch of `board/triage.py::routing_of` chose the state: one
    value per return, so a reader that must stance every branch — the seat
    deciding whether another reading could change anything (card #138) —
    keys on the branch and not on the state, which five branches share."""

    NO_DOCUMENT = "no document"
    UNREAD = "unread"
    """No reading has verified the mark: the one state a reading opens on."""
    DOCUMENT_MOVED = "document moved"
    SOURCE_MOVED = "source moved"
    CANNOT_TELL = "cannot tell"
    SPLIT = "split"
    HIS = "his"
    WHEN = "when"
    WHEN_OVER_MARK = "when over mark"
    """A `when` reading against a document marked `his` or unmarked."""
    NOW = "now"
    NOW_OVER_MARK = "now over mark"
    """A `now` reading against a document the corpus does not mark `now`."""


COMMIT_BOUND: frozenset[Reason] = frozenset(
    {Reason.SPLIT, Reason.WHEN_OVER_MARK, Reason.NOW_OVER_MARK}
)
"""The branches a reading of today's text has already been through and
left the card at `needs triage`: what moves the card from here is a commit
rewriting the document (or a lane separating it), which no reading can
write, so the seat never opens another one (card #138, item 1)."""


class Routed(BaseModel):
    """A defect's routing state and the sentence that says why, in the words
    the rail, the card and `needle fixes` all print."""

    state: Routing
    reason: Reason
    """The branch that chose the state."""
    why: str
    """One sentence, from facts the card or its document carries."""


class ReadingsSpent(BaseModel):
    """How many readings the board has opened on one card's text as it
    stands today (card #138, item 2): every reading opened on that text —
    landed, died or stopped — counts once, because each was a session the
    machine paid for, and past the cap the board opens no more on it."""

    text: str
    """The fingerprint of what the reader reads on this card today, in that
    reader's own terms: a mark's document and source, a title, or a parked
    card's record."""
    opened: int
    cap: int
    parked: bool
    """The count is per park and per answer (card #82, rulings 5 and 9): a
    park is a placement and an answer is an audit row, neither a change to
    the record, so both reset the count by time."""
    wanted: bool
    """Whether the card's own reader would open a reading on this text
    today by its own rule — a mark nobody has verified, a title not read
    as it stands, a parked card unread since its park or his answer. The
    fuse holds only where this is true; a card whose third reading
    settled it is not stopped, it is settled, and its face says so."""

    @property
    def stopped(self) -> bool:
        return self.opened >= self.cap


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
    ground: Ground = Ground.MARK
    """What was read: a defect's mark, or a parked card's record (card #82)."""
    grade: Grade | None = None
    """How bad the defect is, from the same reading (card #100, item 2).
    None on a reading landed before the scale existed; such a defect is
    read again, since the column has no order for it."""


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
    """One line of `needle decisions`: a decision a colleague took off the
    owner's defects, or off his column (card #82), with its source, its
    direction and its fate."""

    decision: str
    parent: str | None
    project: str
    card_number: int
    title: str
    at: datetime
    ground: Ground
    """What the reading read: a mark, or a parked card's record. The cold
    audit never reads a parked `now` as a mark's."""
    result: TriageResult
    words: str
    direction: Direction | None
    source: str
    """The source as the reading resolved it, or why it resolved nowhere."""
    routing: Routing | None
    """Where the card routes now, for a mark's reading: a decision whose
    row went stale says so. None for a parked card's reading, which routes
    nothing."""
    text: str
    """The fingerprint of the text the reading judged — a mark's document,
    a parked card's record — so a count of readings per card can tell one
    text from the next (card #138, the Loop)."""
    fate: Fate
    returned: bool
    """A parked card's reading moved the card out of the owner's column and
    the card is back in it (card #82, the Loop): displaced work, not
    relief. False for a mark's reading."""


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


class TitleVerdict(StrEnum):
    """Whether the owner can place the card from its title and the line
    beneath it, without opening it (card #74, item 3): the test
    `docs/plans/README.md` sets, applied by a reading with no share of the
    writer's context."""

    PLACEABLE = "placeable"
    UNPLACEABLE = "unplaceable"
    """The reader could not place it; its words say what and which words failed."""


class TitleReading(BaseModel):
    """One cold reading of a card's title and essence, as the record keeps
    it. The same session as the mark's reading on a defect, the only
    reading on a plan or an idea. A failing verdict is a machine fact on
    the card's face and holds Start closed until a reading passes; the
    reader marks and never rewrites, because the title is the owner's
    intent in the writer's words and a second guess over the first is two
    guesses."""

    id: int
    project: str
    card_number: int
    at: datetime
    verdict: TitleVerdict
    words: str
    """The reader's words: what he could not place, or why it passes."""
    failed: list[str]
    """The words that failed, from `docs/vocabulary.md` or the reader's own."""
    title_fingerprint: str
    """The title and essence this verdict judged; a changed title is read again."""
    session_id: str | None
