"""The dial: the owner's standing ruling that a marked defect may enter
execution without him (plan 11), and the record of every fix lane it ran.

INTENT.md: one move is his — he decides what enters execution. The dial is
that decision made once instead of once per card: while it is on, the board
plans and starts a defect whose finder marked it `Fix: now`, up to the
number of fix lanes he set, and everything that follows is the ordinary
path. The dial is one for the whole board because its limit is the machine's
slots and its one trunk, not a project (plan 11, rulings).
"""

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from domain.card import Actor
from domain.triage import Decision


class Dial(BaseModel):
    """The dial as the store holds it: on or off, and how many fix lanes may
    run at once. Both survive a restart; every change is audited."""

    on: bool
    lanes: int = Field(ge=0)
    changed_at: datetime | None
    """When the owner last turned it; None while it has never been touched."""
    first_on_at: datetime | None
    """When it was first turned on: the moment the rail's size was recorded
    for the loop (plan 11, item 6)."""


class DialChange(BaseModel):
    """One turn of the dial, as the record keeps it: who, when, and to what."""

    id: int
    at: datetime
    actor: Actor
    on: bool
    lanes: int


class Meminfo(BaseModel):
    """The machine's memory as `/proc/meminfo` reports it, in bytes: what
    the runtime reads before the dial opens anything."""

    available: int
    swap_total: int
    swap_free: int
    total: int = 0
    """`MemTotal`: what the machine has, so a high-water mark can be said as
    memory used (card #83). Zero for a reading made before the field existed."""


class ScopeMemory(BaseModel):
    """What one lane's scope holds right now, as the user manager counts it
    (`MemoryCurrent`), with the card whose lane it is when the board knows
    (plan 53, item 1)."""

    unit: str
    held: int
    project: str | None
    card_number: int | None


class ScopeHeld(BaseModel):
    """What one process group of ours holds right now, as the user manager
    and its control group say (card #99): the unit, every pid in it, each
    one's command line and ancestry, so who owns it can be read and a group
    the board stops is named on the card by what was in it."""

    unit: str
    pids: list[int]
    commands: dict[int, str]
    lineage: dict[int, list[int]]
    """Each pid's ancestors, nearest first: a process a live session started
    is that session's wherever the session's own pid sits this instant."""
    machine: str = ""
    """The machine the group is on, by the board's name for it (card #83);
    empty for a group read by a runtime with no name for its own machine."""


class ScopePids(BaseModel):
    """What one group holds right now, as one machine's runtime answers it
    over the wire (card #83)."""

    unit: str
    pids: list[int]


class ScopeStop(BaseModel):
    """Whether one machine's manager took the job of ending a group, and its
    words (card #83)."""

    unit: str
    taken: bool
    words: str


class ScopeState(BaseModel):
    """One group of ours read against the registry (card #99): which live
    sessions are home in it, by short id, and what else it holds, by the
    head of each command. Nobody home — processes held, no live session
    among them — is a finished session's leftovers: what the beat stops
    and `needle scopes --stray` lists."""

    unit: str
    pids: list[int]
    home: list[str]
    strangers: list[str]
    machine: str = ""
    """The machine the group is on (card #83): the sweep stops it there."""

    @property
    def nobody_home(self) -> bool:
        return bool(self.pids) and not self.home


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
have let the dial open little on a 16 GB machine. Since plan 53 the floor
is read on every pass of the lane loop, not only at the beat, and each
lane's scope is read beside it: a scope holding as much as the floor is the
lane the floor was set from, again, and the machine reads full until it
shrinks or folds — the board stops admitting; it never stops a lane (that
plan's ruling 1). No code path raises the number; the loop in that plan
says when the owner should.

On 2026-09-09 the owner handed the number to the colleague ("it's a tech
thing so you own it"), remembering crashes since it came in. Read that day:
three kills by the userspace out-of-memory killer since 09-08, each of a
window he was using at 90 percent of memory and swap, while the floor held
six walled lanes parked. The floor was never the cause: it gates what the
board admits and chooses nothing about who is killed. It stays 5 GB — a
third of a 15.6 GB laptop that runs a browser, an editor and half its swap
beside the lanes; lower trades idle lanes for a slower machine, not a
crash. Since card #107 it is also the high mark of every lane's own space
(`MemoryHigh` on the scope, `runtime/machine.py::adopt`): past it the kernel
throttles the lane and reclaims inside its space — a throttle the kernel may
still let a lane exceed under pressure, never a hard cap and never a kill —
so a runaway lane presses on itself first rather than on a window; and a
walled lane gives its memory back the moment it waits for room. It lives
here so the runtime, which cannot import the board, sets the same number
it reads (the layers ratchet)."""


def lane_mark(desktop: bool, total: int, floor: int = MEMORY_FLOOR_BYTES) -> int:
    """What one lane's group may hold on a machine before the kernel slows
    it (`MemoryHigh`): on the desktop, the floor — a lane shares the machine
    with the owner's screen and the other lanes (card #107); on a machine
    rented for its memory, everything above the floor, since holding it to
    the desktop's rule slowed Hello Revenue #503 for two hours on a machine
    with 24 GB free (2026-09-10, the first evening a lane ran there). A
    total nobody read is the floor: the rule never hands out room it has
    not seen."""
    if desktop or total <= floor:
        return floor
    return total - floor


class Headroom(BaseModel):
    """The board's reading of the machine's memory against the floor (the
    plan "as many lanes as the machine can hold", item 3; read on every
    pass since plan 53): the number is a ceiling the machine lowers, never
    a count of records."""

    available: int
    swap_free: int
    floor: int
    full: bool
    """Available memory, or free swap on a machine that has swap, is under
    the floor, or a lane's scope holds as much as the floor: the beat takes
    nothing."""
    sentence: str | None
    """What the head says when the machine is full, with the numbers and
    the lane that is growing; None while there is headroom."""
    scopes: list[ScopeMemory] = []
    """Every lane scope the pass could read, biggest first."""
    read_at: datetime
    marked: list[str] = []
    """The scopes this read gave the floor as their high mark, because they
    stood without it (card #107, read on every machine since card #83)."""
    total: int = 0
    """`MemTotal` at this read, so a mark can be said as memory used (card #83)."""
    mark: int = MEMORY_FLOOR_BYTES
    """What a lane's group is held to on this machine (`lane_mark`): the
    floor on the desktop, what the machine has above it on the horsepower."""
    stale_queue: int | None = None
    """Events the sessions' hook has queued in this machine's data folder
    that are older than an hour (card #124): the hook empties its queue the
    moment the board answers, so a count here says the board did not, and
    the head shows it where the owner looks. None when the queue was not
    read — a machine running an older `needle` answers without the field,
    or the file could not be read — so a count nobody took never reads as
    zero (Codex's pass 2 on card #124, finding 2)."""


class DialState(BaseModel):
    """The dial as the head shows it: its setting, and the fix lanes live
    against the number right now."""

    dial: Dial
    running: int
    """Fix lanes the dial has started that have not folded or ended, plus
    the planning sessions it has open: what counts against the number. A
    planned card whose Start is closed is no process and is not counted."""
    triaging: int = 0
    """Triage readings open right now: live sessions against the same
    number, so a rail of untriaged defects cannot open one session per card
    (plan 59, item 3)."""
    held: int
    """Fix lanes at the planned stage whose Start door is closed — parked,
    waiting on a Sequencing card, nowhere to run: what the head shows
    beside *live* so a night of held plans reads as held, not running."""
    full: str | None
    """The machine is full, in the head's words with the numbers, when the
    memory floor stops the beat; None while there is headroom."""
    quiet: bool
    """No lane has hands on any project: when the board's own rail may run
    (plan 11, rulings — a fold on the board restarts the service under every
    running lane)."""


class FixStage(StrEnum):
    """Where a fix lane the dial started stands."""

    PLANNING = "planning"
    """A windowless session is writing the plan in the project's checkout."""
    PLANNED = "planned"
    """The plan landed and the card is its; the Start door is the next act."""
    STARTED = "started"
    """The lane runs; it counts against the number until it folds or ends."""
    FOLDED = "folded"
    """The lane's work is in the trunk."""
    ASKED = "asked"
    """The planning session found a decision that is the owner's and wrote it
    on the card; the dial leaves the card to him."""
    ENDED = "ended"
    """The planning session ended without a plan, or the lane ended with
    nothing folded; the card says why and the dial leaves it to him."""


class FixLane(BaseModel):
    """One defect the dial took: from its planning session to its fold."""

    id: int
    project: str
    card_number: int
    stage: FixStage
    planning_started_at: datetime
    planned_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    """When the lane folded, asked, or ended: from here it no longer counts."""
    note: str | None
    """Why it ended or asked, in one sentence, when it did."""
    decision: str | None
    """The decision identity the reading minted, carried in so one command
    follows a decision from its verification to its fold (plan 59, item 6);
    None for the fix lanes the dial ran before the triage seat existed."""


class Filer(StrEnum):
    """Who filed a defect, read from its `Found by:` line (plan 11, item 6):
    the split that says whether the rail is fed by the path that drains it."""

    FIX_LANE = "fix lane"
    FEATURE_LANE = "feature lane"
    READING = "reading session"
    OWNER = "owner"
    UNKNOWN = "unknown"


class RailCount(BaseModel):
    """The defects rail of one project, by who filed each card."""

    project: str
    counts: dict[Filer, int]
    total: int


class FixReport(BaseModel):
    """What `needle fixes` says of one fix lane."""

    project: str
    card_number: int
    title: str
    stage: FixStage
    folded: bool
    reviewed: bool
    """The card carries a REVIEW row: the close the machine refuses without
    one accepted it."""
    stopped_to_ask: bool
    """Its planning session asked the owner, or its lane's turn ended on a
    question."""
    defect_filed_against: bool
    """A live suggestion names the card or its lane in its `Found by:` line."""
    fold_reverted: bool
    """A commit on the trunk reverts the lane's tip."""
    class_closer: str | None
    """The plan's `Class:` line — what makes the class loud — or None when
    the plan carries none."""


class Waiting(BaseModel):
    """One defect on the rail the dial has not taken, and the fact that
    holds it: what the owner reads when the dial is on and nothing starts."""

    project: str
    card_number: int
    title: str
    born_at: datetime
    why: str


class Fixes(BaseModel):
    """The loop counted (plan 11, item 6): every fix lane the dial started,
    the rail now against the rail when the dial was first turned on, and
    every defect still on the rail with why the dial leaves it there."""

    dial: Dial
    lanes: list[FixReport]
    rail_now: list[RailCount]
    rail_at_first_on: list[RailCount]
    waiting: list[Waiting]
    decisions: list[Decision]
    """Every decision a colleague took off the owner's rail, oldest first,
    with its source, its direction and its fate (plan 59, item 6): the
    sample the loop's cold audit reads."""


def _gb(byte_count: int) -> str:
    return f"{byte_count / 1024**3:.1f} GB"


def _lane_of(scope: ScopeMemory) -> str:
    """What a group is, in the card's words: its lane, or the reading or
    planning session the board opened for the card (the unit's own prefix
    says which, since every group of ours is read now, card #83); the unit
    itself when no card is known."""
    if scope.card_number is None:
        return scope.unit
    kind = "lane"
    for word in ("reading", "planning", "triage"):
        if scope.unit.startswith(f"needle-{word}-"):
            kind = f"{word} session"
    return f"{scope.project} #{scope.card_number}'s {kind}"


def headroom(
    meminfo: Meminfo | None,
    floor: int,
    now: datetime,
    *,
    scopes: Sequence[ScopeMemory] | None = (),
    marked: Sequence[str] = (),
    mark: int | None = None,
    stale_queue: int | None = None,
) -> Headroom:
    """The machine against the floor, and every lane's scope beside it
    (plan 53, item 1). A reading the runtime could not make — the memory,
    or the scopes when there were lanes to read — is full: the beat waits
    until the machine can be read, and the head says so, rather than
    opening a lane on a number nobody has. Full names what is short and
    which lane is growing — the one past the mark, else the biggest — with
    what it holds, so the owner reads which lane the machine waits on. The
    mark is what a lane may hold here (`lane_mark`); None means the floor,
    which is the desktop's."""
    mark = floor if mark is None else mark
    if meminfo is None:
        return Headroom(
            available=0,
            swap_free=0,
            floor=floor,
            full=True,
            sentence="the machine is full: its memory could not be read",
            read_at=now,
            mark=mark,
            stale_queue=stale_queue,
        )
    if scopes is None:
        return Headroom(
            available=meminfo.available,
            swap_free=meminfo.swap_free,
            floor=floor,
            full=True,
            sentence="the machine is full: what its lanes hold could not be read",
            read_at=now,
            total=meminfo.total,
            mark=mark,
            stale_queue=stale_queue,
        )
    ranked = sorted(scopes, key=lambda s: (-s.held, s.unit))
    short: list[str] = []
    if meminfo.available < floor:
        short.append(f"{_gb(meminfo.available)} available")
    if meminfo.swap_total > 0 and meminfo.swap_free < floor:
        short.append(f"{_gb(meminfo.swap_free)} swap free")
    parts: list[str] = []
    if short:
        parts.append(f"{', '.join(short)}, {floor // 1024**3} GB needed")
    biggest = ranked[0] if ranked else None
    if biggest is not None and biggest.held >= mark:
        limit = (
            f"the {floor // 1024**3} GB floor"
            if mark == floor
            else f"the {mark // 1024**3} GB a lane may hold here"
        )
        parts.append(f"{_lane_of(biggest)} holds {_gb(biggest.held)}, past {limit}")
    elif short and biggest is not None:
        parts.append(f"the biggest lane is {_lane_of(biggest)} at {_gb(biggest.held)}")
    return Headroom(
        available=meminfo.available,
        swap_free=meminfo.swap_free,
        floor=floor,
        full=bool(parts),
        sentence=f"the machine is full: {'; '.join(parts)}" if parts else None,
        scopes=ranked,
        read_at=now,
        marked=list(marked),
        total=meminfo.total,
        mark=mark,
        stale_queue=stale_queue,
    )
