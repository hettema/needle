"""The machines the work runs on, and what each holds (card #83).

One board, one store, more than one machine. The board reads and acts on
every machine it knows through the runtime, and a session's row says which
machine it ran on. A machine is a row in the store, registered once by
`needle machine add` the way a project is by `needle add`; the runtime tells
which row is itself by the identity the kernel gives it (`/etc/machine-id`),
never by a hostname, which the owner may change. The desktop is the machine
with his screen: every window, every focus, every notification opens there,
wherever the board runs. A machine's ground is the project that is its own
record — the Omarchy board is the laptop's — and a card in that project runs
on that machine and nowhere else, because it edits that machine (the plan's
ruling of 2026-09-07).
"""

from datetime import date, datetime

from pydantic import BaseModel

from domain.dial import Headroom, ScopeHeld
from domain.ending import Boot
from domain.lane import LaneDocs, LaneTip
from domain.session import Session
from domain.slot import Limits, Where


class Machine(BaseModel):
    """One machine the board knows, as the store holds it."""

    name: str
    """The word the board and the owner use for it: `laptop`, `rented`."""
    machine_id: str
    """The kernel's identity for it (`/etc/machine-id`): what the runtime
    compares to its own to know which row it is."""
    host: str | None
    """The ssh name the other machines reach it by; None when nothing
    reaches it from outside, which is the laptop until the tunnel exists."""
    desktop: bool
    """It holds the owner's screen: windows, focus and notifications open
    here, whatever machine the board runs on."""
    ground: str | None
    """The path of the project that is this machine's own record; a card in
    it runs here and nowhere else. None for a machine no project records."""
    command: str
    """How `needle` is run on it, as a shell line: what the board's runtime
    hands to `ssh` when it asks this machine for a typed answer."""
    added_at: datetime


class BoardMachine(BaseModel):
    """The machine the board serves from, as another machine knows it: enough
    to hand a board verb there (card #83, item 3). Written by `needle board
    NAME` from that machine's row, absent on the board's own machine; a
    machine that holds one runs every verb that opens the board's store on
    the named machine instead, so no session ever writes a copy the board
    never reads."""

    name: str
    host: str
    command: str


class HighWater(BaseModel):
    """The least memory a machine had available on one day, as the board
    read it on its passes: the mark the plan's loop reads to decide 32 or
    64 GB. Kept per day so two weeks are fourteen rows, not a million."""

    machine: str
    day: date
    least_available: int
    """Bytes, as `MemAvailable` counted them at the lowest read."""
    total: int
    """`MemTotal` at that read, so the mark can be said as memory used."""
    at: datetime
    """When the lowest read was made."""

    @property
    def used(self) -> int:
        return max(0, self.total - self.least_available)


class Timing(BaseModel):
    """One measured wall-clock of a build step on a machine (the plan's item
    5): written by hand from a measurement, read by the close and the loop
    against the other machine's."""

    machine: str
    what: str
    """`npm ci`, `vitest`, `pytest`: the step, in the plan's words."""
    seconds: float
    at: datetime


class MachineRoom(BaseModel):
    """One machine as the head shows it: whether the board runs on it,
    whether it answered, and what it holds against the floor."""

    machine: Machine
    here: bool
    """The board's own process runs on it."""
    room: Headroom | None
    """The machine against the floor as the runtime read it this pass; None
    when it could not be reached, and `why` says so."""
    why: str | None
    """Why there is no reading, in the transport's words."""
    high_water: HighWater | None
    """The highest memory use the board has seen on it, over the loop's window."""
    killed: int
    """Lanes the system killed on it over the loop's window."""
    timings: list[Timing] = []
    """The latest measured time per build step on this machine, for the
    plan's item 5."""
    clones: list[str] = []
    """Each project whose clone on this machine was not level with the
    trunk when the board last levelled it (`needle: 2 behind`), so a
    machine's stale checkout is said on its own line and never as the
    board's own checkout's state (Codex's eighth pass on card #83)."""
    observed_at: datetime | None = None
    """When the observation the board holds of this machine was read (card
    #123): this pass's when the machine answered, an earlier pass's when
    it did not — then `why` says why and the age is on the head, and the
    machine's lanes stand as last read rather than empty."""
    behind: bool = False
    """Its `needle` is older than the one question (card #123): it was read
    the old way, one verb at a time, and the head says so."""


def find_ground(machines: list[Machine], repo: str) -> Machine | None:
    """The machine whose own record the repository is, if any."""
    wanted = repo.rstrip("/")
    return next((m for m in machines if m.ground and m.ground.rstrip("/") == wanted), None)


def choose_machine(rooms: list[MachineRoom], repo: str) -> tuple[Machine | None, str]:
    """Where a card in `repo` runs next, and why, in one sentence (the plan's
    item 4): its ground's machine when the project is a machine's own record,
    whatever that machine's room — a full ground is refused by the room
    below, never moved; else the first machine that is not the desktop and
    has room under the floor; else the desktop when it has room; else
    nowhere, with every machine's numbers so the refusal is #53's door with
    the machine's numbers. A machine that did not answer is a machine with
    no room, said by name. One machine and no rooms read is that machine:
    a board that has not read the machine yet places as it always has."""
    machines = [r.machine for r in rooms]
    ground = find_ground(machines, repo)
    if ground is not None:
        reading = next(r for r in rooms if r.machine is ground)
        if reading.room is not None and reading.room.full:
            # Its own cards run nowhere else, so a full ground is #53's
            # refusal with that machine's numbers, never a move.
            return None, (
                f"{ground.name} is the machine this project records and it is full "
                f"({reading.room.sentence or 'full'}); its cards run nowhere else"
            )
        return ground, f"{ground.name} is the machine this project records, so its cards run there"
    if len(rooms) == 1:
        # One machine places as every board did before this card; its room
        # is the door's and the start's to refuse, in the words they had.
        only = rooms[0]
        return only.machine, f"{only.machine.name} is the one machine the board knows"

    def has_room(reading: MachineRoom) -> bool:
        return reading.room is not None and not reading.room.full

    for reading in sorted(rooms, key=lambda r: (r.machine.desktop, r.machine.name)):
        if has_room(reading):
            kind = "the desktop" if reading.machine.desktop else "the horsepower"
            return reading.machine, f"{reading.machine.name} has room ({kind})"
    said: list[str] = []
    for reading in rooms:
        if reading.room is None:
            said.append(f"{reading.machine.name} did not answer ({reading.why or 'no reason'})")
        else:
            said.append(f"{reading.machine.name}: {reading.room.sentence or 'full'}")
    return None, "no machine has room — " + "; ".join(said)


# ── the one question a pass (card #123) ────────────────────────────────


class LaneAsk(BaseModel):
    """One lane the board asks a machine about: the checkout, the
    repository and branch its tip is read for, and which of its documents
    to carry — the plan by its candidate paths, and the review records
    only once every item is met, since a lane's reviews folder is every
    record the project ever wrote."""

    checkout: str
    repo: str
    branch: str | None
    plans: list[str] = []
    """The plan's candidate paths, relative to the checkout, live first and
    archived second; the first that exists is carried."""
    reviews: bool = False


class Ask(BaseModel):
    """What the board asks a machine on one pass: every read the pass made
    one verb at a time before this card (the plan's item 1 names them),
    named so the machine answers them in one reply."""

    repos: list[str] = []
    """Every project's path: the machine lists its checkouts of each."""
    lanes: list[LaneAsk] = []
    hold: bool = True
    """Hold every group of ours at the machine's mark before reading the
    room, as the pass does (card #107)."""
    owners: dict[str, tuple[str, int]] = {}
    """Which card each group is, by unit, when the board knows."""
    read: list[str] = []
    """Groups asked for by name whether or not the manager lists them:
    every lane with hands on (plan 53, item 1)."""


class LaneSeen(BaseModel):
    """One lane as its machine answered for it."""

    checkout: str
    tip: LaneTip
    edits: list[str]
    """What the checkout has changed against the trunk, committed and not."""
    docs: LaneDocs
    plans: list[str] = []
    """The candidates the documents were read for, so a read with other
    candidates (a door reading one record by path) never answers from here."""
    reviews: bool = False
    """The review records were asked for and are in `docs`."""


class Observation(BaseModel):
    """Everything the board asks one machine on one pass, as that machine
    answered it (card #123, item 1): the machine's own `needle` reads its
    registries, its manager, its memory and its checkouts and answers once.
    The same value is read here for the board's own machine, by the same
    function, so a one-machine board and a five-machine board are read by
    one code path."""

    at: datetime
    """The machine's own clock when it began answering."""
    seconds: float
    """How long the machine took to answer, by its own clock."""
    sessions: list[Session]
    """Every session there, lean (without each one's brief)."""
    boots: list[Boot]
    room: Headroom
    scopes: list[ScopeHeld] | None
    """Every process group of ours the manager holds; None when the manager
    could not be asked."""
    placement: Where
    """Where that machine's own rule would run the next card, asked with
    nothing tried: the pass's placement read (`_where_on`) for a machine
    the rooms chose."""
    checkouts: dict[str, dict[str, str | None]] = {}
    """Per repository asked, every checkout there: path → branch."""
    lanes: list[LaneSeen] = []
    limits: dict[str, Limits | None] = {}
    """Every subscription's last limits reading on that machine, by slot:
    what a parked lane's end is read against, so a park is checked without
    asking the machine under the lock (card #123). Empty for a machine read
    the old way."""
    windows: list[str] | None = None
    """The addresses of every window the compositor holds, when this
    machine is the desktop and the compositor answered; None otherwise.
    The board reconciles its window records against this instead of
    asking the desktop's compositor over the wire on every read."""


class Observed(BaseModel):
    """What the board holds of one machine between passes (card #123, item
    2): the newest observation it accepted, when the board read it, and —
    when this pass brought no new one — why. A machine that never answered
    holds None with the reason, so every read of it answers empty and
    unread rather than reaching for the wire."""

    machine: str
    observation: Observation | None
    read_at: datetime | None
    """The board's clock when `observation` was accepted."""
    asked_at: datetime | None = None
    """The board's clock when the last question accepted for this machine
    went out, answered or not: an answer to an older question is dropped,
    and a launch after a fresh observation's question stands beside it."""
    fresh: bool
    """The observation is this pass's."""
    why: str | None
    """Why this pass brought no observation, in the transport's words."""
    behind: bool = False
    """The machine's `needle` has no `observe` verb: read the old way."""
    seconds: float = 0.0
    """How long this pass's collection of the machine took, by the board's
    clock — the wire included — for the beat's record (item 4)."""
