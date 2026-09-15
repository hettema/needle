"""What the dial may take next, what counts against its number, and who
filed each defect in the Defects column (plan 11) — pure over domain values;
the cadence that acts on these answers lives in `api/dial.py`.

Eligibility is the document's mark plus the card's latest reading, and the
board edits nothing: a defect marked `Fix: now`, or `Fix: when <signal>`
whose trigger was last read as delivered, standing on its own in the
Defects column, with no lane on it, no planning session open for it, no fix
lane the dial already ran for it, and no question left on it for the owner.
Gravest first across projects, then oldest (card #100, item 3): the column
is machine-kept and carries no owner rank, so the reading's grade and the
card's age are the facts every card has.
"""

import re
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from pydantic import BaseModel

from board.lane import has_row
from board.title import wants_title_reading
from board.triage import GradeKey, at_or_above, band_of, fingerprint, order_key
from domain.card import Card
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.dial import (
    DefectsCount,
    Dial,
    DialChange,
    DialState,
    Filer,
    FixLane,
    FixStage,
    Headroom,
    ScopeHeld,
    ScopeState,
)
from domain.document import Document, DocumentKind, FixMark, SuggestionKind
from domain.lane import HANDS_ON, Lane, LaneState
from domain.release import Held
from domain.row import RowKind
from domain.session import Session
from domain.signal import Reading, WindowlessSession
from domain.triage import (
    Band,
    Grade,
    ReadingsSpent,
    Reason,
    Routed,
    Routing,
    TitleReading,
    Triage,
)

LIVE_STAGES: frozenset[FixStage] = frozenset(
    {FixStage.PLANNING, FixStage.PLANNED, FixStage.STARTED}
)
"""The stages that count against the number. The plan's letter counts a fix
lane from its Start; a planning session is a session on a subscription too,
and counting from there is the only reading under which the number bounds
what the dial opens — otherwise a dial at one would open one planning
session per defect on the rail before the first lane started."""

_FIX_LANE = re.compile(r"\bfix lane\b|\bstarted by the dial\b", re.I)
_OWNER = re.compile(r"^\W*(?:the\s+)?owner\b", re.I)
_READING = re.compile(r"^\W*(?:#\d+'?s?\s+)?reading\b|^\W*the reading\b|\breading session\b", re.I)
_LANE = re.compile(
    r"^\W*(?:the\s+)?(?:lane|review|close)\b|^\W*(?:card\s+)?#?\d+'?s\s+(?:lane|review|close)\b"
    r"|\blane on card\b|\bcard #\d+'?s lane\b",
    re.I,
)


def filer_of(found_by: str | None) -> Filer:
    """Who filed a defect, from the words that open its `Found by:` line:
    the fix lane the dial ran, the owner, a reading session, or a feature
    lane (a lane, a review, a close). A heuristic over prose, printed beside
    its count so the owner can read what it decided; a line it cannot place
    is unknown, never guessed."""
    if not found_by:
        return Filer.UNKNOWN
    text = found_by.strip()
    if _FIX_LANE.search(text):
        return Filer.FIX_LANE
    if _OWNER.search(text):
        return Filer.OWNER
    if _READING.search(text):
        return Filer.READING
    if _LANE.search(text):
        return Filer.FEATURE_LANE
    return Filer.UNKNOWN


def filed_against(
    number: int, lane: str, documents: Sequence[Document], *, live_only: bool = True
) -> list[Document]:
    """The defects — suggestions of that kind, never ideas — whose `Found
    by:` line names the card or its lane: what `needle fixes` reads as a
    defect filed against a fix lane (plan 11, item 6), and what the team's
    reader counts as an escape (card #58), one reading for both. The rail
    reads the live ones; the reader reads the archived too, since a defect
    fixed since was still filed."""
    pattern = re.compile(rf"(?<!\d)#{number}(?!\d)|{re.escape(lane)}")
    return [
        d
        for d in documents
        if d.kind == DocumentKind.SUGGESTION
        and d.suggestion_kind == SuggestionKind.DEFECT
        and (not d.archived or not live_only)
        and d.found_by is not None
        and pattern.search(d.found_by) is not None
    ]


_BY_THE_CARD = (
    r"^\W*(?:the\s+)?(?:lane|review|close|session)\s+(?:on|of)\s+(?:card\s+)?#{n}\b"
    r"|^\W*(?:card\s+)?#{n}'?s\s+(?:lane|review|close|session)\b"
)


def filed_by_the_card(number: int, found_by: str | None) -> bool:
    """Whether the `Found by:` line says the card's own lane, review or
    close filed it: a defect the card found in something else, which
    names the card without being about its work. The team's reader keeps
    those out of a card's escapes (card #58, from its independent review),
    since a lane filing what its review found outside its change is
    doing what §13 asks, not escaping a defect."""
    if not found_by:
        return False
    return re.search(_BY_THE_CARD.format(n=number), found_by.strip(), re.I) is not None


def column_defects(cards: list[Card], index: CorpusIndex) -> list[tuple[Card, Document]]:
    """Every card standing on its own in the project's Defects column — a
    card there behind a live suggestion whose document says defect, which
    is what the corpus keeps the column to (card #100, item 1)."""
    found: list[tuple[Card, Document]] = []
    for card in cards:
        if card.folded_into is not None or card.place.column != Column.DEFECTS:
            continue
        if card.link is None or card.link.kind != DocumentKind.SUGGESTION:
            continue
        document = index.find(card.link.kind, card.link.stem)
        if document is None or document.archived:
            continue
        if document.suggestion_kind != SuggestionKind.DEFECT:
            continue
        found.append((card, document))
    return found


TITLE_READ_COLUMNS: frozenset[Column] = frozenset({Column.BACKLOG, Column.PLANNED, Column.UP_NEXT})
"""Where a title is read cold (card #74, item 3): the columns a card is
ranked in before anyone has hands on it. A card in flight, shipped, parked
or on the owner's desk is not read — its Start is closed by other facts
and a reading would answer a question nothing acts on."""


def unread_titles(
    cards: list[Card], index: CorpusIndex, latest: dict[int, TitleReading]
) -> list[tuple[Card, Document]]:
    """Every card standing on its own behind a live plan or idea whose
    title has not been read as it stands. Defects are not listed here: a
    defect's title is read by the same session as its mark, so it rides on
    the mark's reading (`column_defects`) and never opens a second one."""
    found: list[tuple[Card, Document]] = []
    for card in cards:
        if card.folded_into is not None or card.place.column not in TITLE_READ_COLUMNS:
            continue
        if card.link is None:
            continue
        document = index.find(card.link.kind, card.link.stem)
        if document is None or document.archived:
            continue
        if document.suggestion_kind == SuggestionKind.DEFECT:
            continue
        if wants_title_reading(document, latest.get(card.number)):
            found.append((card, document))
    return found


def defects_count(slug: str, cards: list[Card], index: CorpusIndex) -> DefectsCount:
    """The column's size, split by who filed each card (plan 11, item 6)."""
    counts: dict[Filer, int] = {}
    for _, document in column_defects(cards, index):
        filer = filer_of(document.found_by)
        counts[filer] = counts.get(filer, 0) + 1
    return DefectsCount(project=slug, counts=counts, total=sum(counts.values()))


class Candidate(BaseModel):
    """A defect the dial may take, or a card to open a reading on, with
    what it is ranked by: the grade its current reading landed and its
    age. A candidate for a reading has no grade yet, so among those age
    alone orders (card #100, item 3: the queue of readings stays oldest
    first) — behind every defect and title, the cards parked on the owner,
    oldest park first (card #82, ruling 9): `parked_since` is set on those
    and they rank after the rest, never by their date against a defect's
    birth. `document` is None only for a parked card with no document."""

    project: str
    card: Card
    document: Document | None
    grade: Grade | None = None
    parked_since: datetime | None = None

    @property
    def age_key(self) -> tuple[int, datetime, int]:
        if self.parked_since is not None:
            return (1, self.parked_since, self.card.number)
        return (0, self.card.born_at, self.card.number)

    @property
    def order_key(self) -> GradeKey:
        """Gravest first, then oldest: the one order the column shows."""
        return order_key(self.grade, self.card.born_at, self.card.number)


def why_not_eligible(
    card: Card,
    document: Document,
    *,
    routed: Routed,
    last: Reading | None,
    lane: Lane | None,
    planning_open: bool,
    triage_open: bool,
    ran_before: bool,
    grade: Grade | None = None,
    line: Band | None = None,
) -> str | None:
    """Why the dial leaves this defect where it is, in one sentence, or None
    when it may take it. Every reason is a fact the card, its document or
    its reading carries, so the owner can change it by changing the fact.

    The mark alone no longer opens the door (plan 59): `routed` is the state
    every reader derives from the document's mark and the card's latest
    reading together, and anything but `triaged now` — or a verified `when`
    whose own trigger has fired — is a reason in its own words. The board's
    line is one more fact (card #149, item 2): a graded defect whose band
    is below it is left with the line's own sentence, so the beat, `needle
    fixes` and the face say one thing; the comparison is `at_or_above` and
    is written nowhere else."""
    fix = document.fix
    if routed.state == Routing.TRIAGED_WHEN and fix is not None and fix.mark == FixMark.WHEN:
        if fix.trigger is None:
            return "marked when, and the line names no trigger"
        if last is None:
            return "marked when, and its trigger has not been read as delivered"
        if not last.delivered:
            read = "not delivered" if last.delivered is False else "unreadable"
            return f"marked when, and its trigger last read {read}"
    elif routed.state != Routing.TRIAGED_NOW:
        return routed.why
    if triage_open:
        return "a reading is verifying its mark now"
    if lane is not None and (lane.state != LaneState.NONE or lane.path is not None):
        return f"a lane exists for it ({lane.state.value})"
    if planning_open:
        return "the dial is planning it now"
    if ran_before:
        return "the dial took it once already; it is the owner's from here"
    if has_row(card, RowKind.ASK):
        return "it carries a question for the owner"
    if grade is not None and line is not None and not at_or_above(band_of(grade), line):
        return below_line_words(line)
    return None


def below_line_words(line: Band) -> str:
    """The one sentence for a defect the line leaves filed (card #149):
    what `needle fixes` says of it, what holds its plan at Start, and what
    the face ends with."""
    return f"below this board's line at {line.value}"


def held_lanes(
    fix_lanes: list[FixLane],
    start_offered: Callable[[str, int], bool | None],
    switched_on: Callable[[str], bool],
    held_by_release: Callable[[str, int], str | None] | None = None,
    below_line: Callable[[str, int], str | None] | None = None,
    planning_open: Callable[[str, int], bool] | None = None,
) -> list[FixLane]:
    """The fix lanes at the planned stage the dial cannot start — the Start
    door closed (parked, waiting on a Sequencing card, nowhere to run, or
    not read yet), the board's switch off since the plan was written (card
    #80), a release already waiting on this board that this card's plan
    would pile onto (card #139, item 4), or the board's line moved below
    the card's band since the plan was written (card #149, ruling 5: a
    plan is not execution until Start, and the line at that moment is the
    ruling that applies). Such a card is no process: on the dial's first
    night four of them held four slots while fourteen eligible defects
    waited. `start_offered` answers from the loop's last read; None
    (unread) is closed. `switched_on`, `held_by_release` and `below_line`
    answer from the board's own state.

    *No process* is the whole reason a held lane counts against nothing, so
    a planned lane whose planning session is still open is never held,
    whatever closes its Start (card #151, ruling 7): while the board hands
    a writer the readings that refuse its title, that writer is a live
    session on a machine, and a number of four would otherwise hold four of
    them at zero and open four more beside them. `planning_open` answers
    whether that card still has one."""
    return [
        lane
        for lane in fix_lanes
        if lane.stage == FixStage.PLANNED
        and not (planning_open is not None and planning_open(lane.project, lane.card_number))
        and (
            start_offered(lane.project, lane.card_number) is not True
            or not switched_on(lane.project)
            or (
                held_by_release is not None
                and held_by_release(lane.project, lane.card_number) is not None
            )
            or (below_line is not None and below_line(lane.project, lane.card_number) is not None)
        )
    ]


def running(fix_lanes: list[FixLane], held: list[FixLane] | None = None) -> int:
    """What counts against the number: every fix lane at a live stage that
    is not held. The planning stage always counts, which bounds how many
    plans are written ahead. A reading does not count (card #154): plan 59,
    item 3 folded readings in so a rail of forty untriaged defects could not
    open forty sessions under a dial set to one, and the number then held
    back the board's eyes whenever auto-fix filled it with hands — a
    planned card waited six hours to start on 2026-09-15 because nothing
    was read while four lanes ran. Readings have their own bound now,
    `READINGS_AT_ONCE`, which keeps the forty out just the same."""
    held_ids = {lane.id for lane in held or []}
    return sum(1 for lane in fix_lanes if lane.stage in LIVE_STAGES and lane.id not in held_ids)


READINGS_AT_ONCE = 3
"""How many readings the board holds open at once across every board (card
#154, item 2): the bound that keeps a rail of forty unread cards from
opening forty sessions, now that a reading no longer counts against the
number. A constant and not a setting (ruling 1): the owner already sets one
number and a line per board, and the thing this protects is the machine,
which has a floor he never sets by hand and which stops everything first.
Three is a few — enough that a night's rail is read in a night, few enough
that readings never take the room a lane needs; if the evidence says it is
wrong, this is a one-line change with a reason."""


def reading_gaps(
    fix_lanes: Sequence[FixLane], readings: Sequence[WindowlessSession], now: datetime
) -> list[datetime]:
    """The hours of the last day in which a fix lane ran and no reading
    opened — the plan's own class made loud (card #154, item 5), what
    `needle fixes --reading-gaps` prints and its Loop reads. Only whole
    hours: the twenty-four ending at the top of this one, so the hour still
    running never reads as a gap before it has had its chance.

    A lane ran in an hour when the hour meets one of its two working
    spells — its planning session, from the start to the plan or the end,
    and its lane, from the Start to the end — and never the wait between
    them: a plan held at a closed door for a week is nothing running, and
    counting it would give the Loop a number it could not bring back to
    zero. A reading opened in an hour when its start falls inside it."""
    top = now.replace(minute=0, second=0, microsecond=0)
    hours = [top - timedelta(hours=k) for k in range(24, 0, -1)]
    opened = [r.started_at for r in readings]
    spells: list[tuple[datetime, datetime]] = []
    for lane in fix_lanes:
        planning_until = lane.planned_at or lane.ended_at or now
        spells.append((lane.planning_started_at, max(planning_until, lane.planning_started_at)))
        if lane.started_at is not None:
            spells.append((lane.started_at, max(lane.ended_at or now, lane.started_at)))
    gaps: list[datetime] = []
    for start in hours:
        end = start + timedelta(hours=1)
        ran = any(began < end and until > start for began, until in spells)
        looked = any(start <= at < end for at in opened)
        if ran and not looked:
            gaps.append(start)
    return gaps


def stranded_words(
    fix: FixLane,
    *,
    carries_a_plan: bool,
    title_held: bool,
    writer_is_open: bool,
    hours_up: bool,
) -> str | None:
    """Why this fix lane sits on the owner's desk by the dial's own hand, or
    None (card #151, item 4). Two shapes, both read from stages and stamps
    and never from a note's words.

    A lane the beat ended before it was ever planned, whose card carries a
    plan now — the plan arrived after the board gave up on its session, and
    the beat that re-opens such a card has not run yet or could not.

    A planned lane a failing title holds, with no writer on it and the
    dial's hour spent: nobody will rewrite that title now but the owner.
    While the hour stands the dial hands each refusal back to the writer, so
    such a card is in flight and not stranded; a writer at work on it is the
    same. Zero is the class closed: every card the dial planned either
    started or reached him with a reason he can act on."""
    if fix.stage == FixStage.ENDED and fix.planned_at is None and fix.started_at is None:
        if carries_a_plan:
            return "the beat ended it without a plan, and its card carries one now"
        return None
    if fix.stage != FixStage.PLANNED or not title_held:
        return None
    if writer_is_open or not hours_up:
        return None
    return (
        "a cold reading refuses its title, the dial has spent its hour rewriting it, and no "
        "writer is on it: the title is the owner's"
    )


def is_quiet(lanes_by_project: dict[str, dict[int, Lane]]) -> bool:
    """No lane has hands on any project: when the board's own rail may run."""
    return not any(
        lane.state in HANDS_ON for lanes in lanes_by_project.values() for lane in lanes.values()
    )


def _head(command: str) -> str:
    return " ".join(command.split()[:2])[:40] or "?"


def who_is_home(held: Sequence[ScopeHeld], sessions: Sequence[Session]) -> list[ScopeState]:
    """Every group of ours against the registry (card #99): a live session
    whose pid is in the group, or that started something in it, is home,
    and everything else the group holds is a stranger, named by the head
    of its command. A group that holds
    processes and nobody is home in is a finished session's leftovers —
    forty wait loops from three sessions a day gone, on 2026-09-09 — and
    is what the beat stops and `needle scopes --stray` lists."""
    # A pid names a process on one machine only (card #83): a group read
    # on the rented machine is matched against the sessions read there,
    # never against a laptop session that happens to hold the same number.
    by_pid = {(s.machine, s.pid): s.short_id for s in sessions if s.pid is not None and not s.stale}
    states: list[ScopeState] = []
    for scope in held:
        owner = {
            pid: next(
                (
                    by_pid[(scope.machine, p)]
                    for p in (pid, *scope.lineage.get(pid, ()))
                    if (scope.machine, p) in by_pid
                ),
                None,
            )
            for pid in scope.pids
        }
        home = sorted({who for who in owner.values() if who is not None})
        strangers = [_head(scope.commands.get(p, "")) for p in scope.pids if owner[p] is None]
        states.append(
            ScopeState(
                unit=scope.unit,
                pids=list(scope.pids),
                home=home,
                strangers=strangers,
                machine=scope.machine,
            )
        )
    return states


def switch_was_on(changes: Sequence[DialChange], slug: str, moment: datetime) -> bool:
    """Whether a board's switch was on at a moment, from the audit of turns
    (card #80, item 3): the last turn at or before the moment that turned
    this board — by name, or a turn from before the switch was per board,
    which turned every board — says. No turn by then is off, which is how
    every board is born. A change of the number alone turns nothing. The
    rows are read in the order of their moments, not their ids, so a clock
    that stepped back between two turns cannot end the read early."""
    state = False
    for change in sorted(changes, key=lambda c: (c.at, c.id)):
        if change.at > moment:
            continue
        if change.on is None or change.project not in (None, slug):
            continue
        state = change.on
    return state


def line_at(changes: Sequence[DialChange], slug: str, moment: datetime) -> Band:
    """Where a board's line stood at a moment, from the audit of turns (card
    #149, item 2): the last row at or before the moment that names this
    board and carries a line says. No such row is the last rung — every
    defect — which is where auto-fix reached before the line existed and
    how every board is born. Read in the order of moments, as
    `switch_was_on` is, so a clock that stepped back cannot end the read
    early."""
    line = Band.NOTHING
    for change in sorted(changes, key=lambda c: (c.at, c.id)):
        if change.at > moment:
            continue
        if change.project != slug or change.line is None:
            continue
        line = change.line
    return line


def dial_state(
    dial: Dial,
    switches: Sequence[Dial],
    fix_lanes: list[FixLane],
    lanes_by_project: dict[str, dict[int, Lane]],
    *,
    held: list[FixLane],
    room: Headroom | None,
    triaging: int = 0,
    release: Held | None = None,
) -> DialState:
    """One board's head: its own switch, the other boards that are on, the
    count against the machine's number across every board, and the release
    waiting on the owner when one is (card #139)."""
    return DialState(
        dial=dial,
        others_on=[s.project for s in switches if s.on and s.project != dial.project],
        running=running(fix_lanes, held),
        triaging=triaging,
        readings_at_most=READINGS_AT_ONCE,
        held=len(held),
        full=room.sentence if room is not None and room.full else None,
        quiet=is_quiet(lanes_by_project),
        release=release,
    )


# ── card #148: a card whose machine is full never holds the rest ───────

LEFT_OUT = "The board left this card out of its beat: "
"""How a card says its machine cannot open a reading of it now (card
#148, item 2). The beat asks each unread card's project the question the
launch would ask — can this project's machine open a reading, over the
rooms read this pass — and reads the rest instead of spending its one act
on the refusal (twenty-four beats on Omarchy #3 while 127 defects waited,
2026-09-14). The words after the prefix are the rule's own sentence, with
the machine's numbers; the prefix is what a spell is read by."""

REFUSED = "The board could not start a reading of "
"""How a card says the launch itself refused its reading — a cause the
rooms do not carry: a machine that did not answer, no subscription with
allowance. The beat passes over the card and its project for the rest of
the beat and reads the next (card #148's suggestion names the class: any
candidate the runtime refuses to open this beat, for room or any other
reason the refusal names); the card says so once per spell, as a left-out
card does."""


def left_out_words(why: str) -> str:
    """The one note a card left out for room carries."""
    return (
        f"{LEFT_OUT}{why}. The beat reads the rest and comes back to this card "
        "when its machine has room."
    )


def refused_words(of_what: str, why: str) -> str:
    """The one note a card whose reading the launch refused carries."""
    return f"{REFUSED}{of_what}: {why}"


def spell_stands(last_dial_note: str | None, prefix: str) -> bool:
    """Whether the card already says it, in this spell: its last dial note
    by the machine opens with the prefix. A reading that opened, or a
    death written since, ends the spell, and the next beat that leaves the
    card out or is refused says so again — once. The comparison is on the
    prefix, never the whole note: the machine's numbers in the sentence
    move between beats."""
    return last_dial_note is not None and last_dial_note.startswith(prefix)


# ── card #138: the seat reads a text once, and stops at the cap ────────

TRIAGE_ATTEMPTS = 3
"""How many readings the board opens on one card's text before it stops —
landed, died or stopped alike (card #138, item 2). The guard, `seat_opens`,
means a second reading of one text is already a hole; three bounds what
any hole in the seat can cost to a handful of readings and a card that
says the board stopped, never a day of the machine (850 readings of three
Hello Revenue cards, 629 million tokens, 2026-09-12 to 13)."""

SEAT_OPENS: dict[Reason, bool] = {
    Reason.NO_DOCUMENT: False,
    Reason.UNREAD: True,
    Reason.DOCUMENT_MOVED: True,
    Reason.SOURCE_MOVED: True,
    Reason.CANNOT_TELL: False,
    Reason.SPLIT: False,
    Reason.HIS: False,
    Reason.WHEN: False,
    Reason.WHEN_OVER_MARK: False,
    Reason.NOW: False,
    Reason.NOW_OVER_MARK: False,
}
"""The seat's stance per branch of `routing_of` (card #138, item 1): a
reading opens only where nobody has verified today's text — never read,
or read and the document or its source moved since. A cannot-tell waits
for the evidence it named, and when that arrives the row goes stale, which
is this same door. The three commit-bound branches (`COMMIT_BOUND`) are
the loop this card was written for: today's text was read, the result
routes to nobody, and only a commit rewriting the document moves it, which
no reading can write. A card with no document has nothing to read. A
branch missing here fails `tests/board/test_dial.py` until it is stanced."""


def seat_opens(routed: Routed, triage: Triage | None) -> bool:
    """Whether a reading could still change where this defect routes: the
    stance per branch, and one exception above it — a reading that landed
    no grade (every reading from before card #100) is read again whatever
    it landed, because the column has no order for the card without one."""
    if triage is not None and triage.grade is None:
        return True
    return SEAT_OPENS[routed.reason]


def hands_off(lane: Lane | None) -> bool:
    """Whether the seat may read a card at all: nobody has hands on it and
    no copy of the code stands for it. A card with a lane is the owner's
    or a session's from here, so a reading of it is a session spent on an
    answer nothing will act on."""
    return lane is None or (lane.state == LaneState.NONE and lane.path is None)


def text_of_mark(document_fingerprint: str, source_fingerprint: str | None) -> str:
    """The text a mark's reading is bound to, from the two fingerprints a
    landed row carries: the one composition, so the count the seat keeps
    and the text `needle decisions` prints name the same thing."""
    return fingerprint(f"{document_fingerprint}\n{source_fingerprint or ''}")


def mark_text(document: Document, source_fingerprint: str | None) -> str:
    """What a mark's reading binds to: the document and the source the mark
    cites, as they read today — the two fingerprints `routing_of` tests a
    landed row against, so a change to either is a new text and a fresh
    count."""
    return text_of_mark(document.fingerprint, source_fingerprint)


def readings_spent(
    sessions: Sequence[WindowlessSession],
    *,
    text: str,
    since: datetime | None,
    parked: bool,
    wanted: bool,
) -> ReadingsSpent:
    """How many readings the board has opened on this text and seen end —
    landed or died — counting each once. A reading still open is not yet
    spent: the seat never opens beside it anyway, and counting it would
    have the face say the board stopped while a reading is in flight.
    `since` is a parked card's park or the owner's answer on it (card #82,
    rulings 5 and 9): neither moves the record, so that count is by time.
    `wanted` is whether the card's reader would open on this text today."""
    opened = sum(
        1
        for s in sessions
        if s.text_fingerprint == text
        and s.ended_at is not None
        and (since is None or s.started_at >= since)
    )
    return ReadingsSpent(
        text=text, opened=opened, cap=TRIAGE_ATTEMPTS, parked=parked, wanted=wanted
    )


def stopped_words(spent: ReadingsSpent | None) -> str | None:
    """The sentence a card the fuse stopped shows — on its face, in
    `needle fixes` and on the head's count — or None while the board is
    still reading it, and None where the fuse is not what holds the card:
    a card whose third reading settled it is settled, and saying the board
    stopped would paint broken over yours (the review of #138, finding 1).
    It says how many readings were spent, that nothing settled it, and
    what starts the readings again, so a card the board gave up on never
    reads as `needs triage`."""
    if spent is None or not spent.stopped or not spent.wanted:
        return None
    where = " since it was parked or you last answered on it" if spent.parked else ""
    again = (
        "your answer on it, a change to its document, or parking it again"
        if spent.parked
        else "a change to the document or to the source its mark cites"
    )
    return (
        f"the board read this {spent.opened} times on this text{where} and nothing settled it; "
        f"it opens no more readings on it — {again} starts them again"
    )
