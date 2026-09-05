"""What the dial may take next, what counts against its number, and who
filed each defect on the rail (plan 11) — pure over domain values; the
cadence that acts on these answers lives in `api/dial.py`.

Eligibility is the document's mark plus the card's latest reading, and the
board edits nothing: a defect marked `Fix: now`, or `Fix: when <signal>`
whose trigger was last read as delivered, standing on its own on a Backlog
rail, with no lane on it, no planning session open for it, no fix lane the
dial already ran for it, and no question left on it for the owner. Oldest
first across projects (the rulings): the rail is machine-kept and carries no
owner rank, so age is the one fact every card has.
"""

import re
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel

from board.lane import has_row
from domain.card import Card
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.dial import (
    Dial,
    DialState,
    Filer,
    FixLane,
    FixStage,
    Headroom,
    Meminfo,
    RailCount,
)
from domain.document import Document, DocumentKind, FixMark, SuggestionKind
from domain.lane import HANDS_ON, Lane, LaneState
from domain.row import RowKind
from domain.signal import Reading
from domain.triage import Routed, Routing

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


def rail_defects(cards: list[Card], index: CorpusIndex) -> list[tuple[Card, Document]]:
    """Every card standing on its own on the project's defects rail — a
    Backlog card behind a live suggestion whose document says defect."""
    found: list[tuple[Card, Document]] = []
    for card in cards:
        if card.folded_into is not None or card.place.column != Column.BACKLOG:
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


def rail_count(slug: str, cards: list[Card], index: CorpusIndex) -> RailCount:
    """The rail's size, split by who filed each card (plan 11, item 6)."""
    counts: dict[Filer, int] = {}
    for _, document in rail_defects(cards, index):
        filer = filer_of(document.found_by)
        counts[filer] = counts.get(filer, 0) + 1
    return RailCount(project=slug, counts=counts, total=sum(counts.values()))


class Candidate(BaseModel):
    """A defect the dial may take, with the age it is ranked by."""

    project: str
    card: Card
    document: Document

    @property
    def age_key(self) -> tuple[datetime, int]:
        return (self.card.born_at, self.card.number)


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
) -> str | None:
    """Why the dial leaves this defect where it is, in one sentence, or None
    when it may take it. Every reason is a fact the card, its document or
    its reading carries, so the owner can change it by changing the fact.

    The mark alone no longer opens the door (plan 59): `routed` is the state
    every reader derives from the document's mark and the card's latest
    reading together, and anything but `triaged now` — or a verified `when`
    whose own trigger has fired — is a reason in its own words."""
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
    return None


def held_lanes(
    fix_lanes: list[FixLane], start_offered: Callable[[str, int], bool | None]
) -> list[FixLane]:
    """The fix lanes at the planned stage whose Start door is closed — parked,
    waiting on a Sequencing card, nowhere to run, or not read yet. Such a
    card is no process: on the dial's first night four of them held four
    slots while fourteen eligible defects waited. `start_offered` answers
    from the loop's last read; None (unread) is closed."""
    return [
        lane
        for lane in fix_lanes
        if lane.stage == FixStage.PLANNED
        and start_offered(lane.project, lane.card_number) is not True
    ]


def running(
    fix_lanes: list[FixLane], held: list[FixLane] | None = None, *, triaging: int = 0
) -> int:
    """What counts against the number: every fix lane at a live stage that
    is not held, plus every open triage reading. The planning stage always
    counts, which bounds how many plans are written ahead; a triage counts
    for the same reason — it is a live session on a machine whose ceiling is
    memory, and a rail of forty untriaged defects would otherwise open forty
    of them under a dial set to one (plan 59, item 3)."""
    held_ids = {lane.id for lane in held or []}
    return (
        sum(1 for lane in fix_lanes if lane.stage in LIVE_STAGES and lane.id not in held_ids)
        + triaging
    )


def is_quiet(lanes_by_project: dict[str, dict[int, Lane]]) -> bool:
    """No lane has hands on any project: when the board's own rail may run."""
    return not any(
        lane.state in HANDS_ON for lanes in lanes_by_project.values() for lane in lanes.values()
    )


MEMORY_FLOOR_BYTES = 5 * 1024**3
"""Below this much available memory, or free swap on a machine that has
swap, the beat takes nothing. It shipped at 3 GB, because a fix lane peaked
at 3.1 GB on the dial's first night (Hello Revenue #385, `systemctl show
MemoryCurrent`, 2026-09-05) and systemd-oomd acts at 90 percent of both
memory and swap. It rose to 5 GB the same day: forty seconds after the
board restarted on the floor, oomd killed Hello Revenue #386's lane, whose
scope peaked at 4.7 GB after the dial had let it in — the plan's loop said
the floor rises by a killed scope's peak, the reading said so, and the owner
set 5 GB (the peak with headroom) rather than the rule's 7.7 GB, which would
have let the dial open little on a 16 GB machine. The floor is read at the
beat, before a start; a lane that grows past the machine after it is in is
the card "a lane that grows toward the machine's ceiling pauses new starts
before oomd has to kill it"."""


def _gb(byte_count: int) -> str:
    return f"{byte_count / 1024**3:.1f} GB"


def headroom(meminfo: Meminfo | None, floor: int, now: datetime) -> Headroom:
    """The machine against the floor. A reading the runtime could not make
    is full: the beat waits until the machine can be read, and the head says
    so, rather than opening a lane on a number nobody has."""
    if meminfo is None:
        return Headroom(
            available=0,
            swap_free=0,
            floor=floor,
            full=True,
            sentence="the machine is full: its memory could not be read",
            read_at=now,
        )
    short: list[str] = []
    if meminfo.available < floor:
        short.append(f"{_gb(meminfo.available)} available")
    if meminfo.swap_total > 0 and meminfo.swap_free < floor:
        short.append(f"{_gb(meminfo.swap_free)} swap free")
    sentence = (
        f"the machine is full: {', '.join(short)}, {floor // 1024**3} GB needed" if short else None
    )
    return Headroom(
        available=meminfo.available,
        swap_free=meminfo.swap_free,
        floor=floor,
        full=bool(short),
        sentence=sentence,
        read_at=now,
    )


def dial_state(
    dial: Dial,
    fix_lanes: list[FixLane],
    lanes_by_project: dict[str, dict[int, Lane]],
    *,
    held: list[FixLane],
    room: Headroom | None,
    triaging: int = 0,
) -> DialState:
    return DialState(
        dial=dial,
        running=running(fix_lanes, held, triaging=triaging),
        triaging=triaging,
        held=len(held),
        full=room.sentence if room is not None and room.full else None,
        quiet=is_quiet(lanes_by_project),
    )
