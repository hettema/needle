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

from domain.dial import Headroom


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
        return ground, f"{ground.name} is the machine this project records, so its cards run there"
    if len(rooms) == 1:
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
