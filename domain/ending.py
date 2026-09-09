"""How a lane's session ended, what the work stood at, and what the board
does about it (the plan "work the laptop interrupted comes back by itself").

Two findings, never one. The *cause* is what took the process — read at the
end, from the evidence that held it: the wall detector's file, the journal
of the space the process ran in, the boot it ran in, or nothing — and the
*disposition* is what the work stood at when it stopped, read from the
card's own record: closed, the owner's, or unfinished. The machine resumes
only a cause it can name, on work that is unfinished; everything else is
said truly on the card and left where it fell.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Cause(StrEnum):
    """What took the session's process, or interrupted its turn. The value
    is the phrase the card shows, in the owner's words."""

    WALL = "its allowance ran out"
    """A usage limit: the wall detector's handoff, or a blocked turn the
    session's own stop-failure event names as a limit with no handoff."""
    LANE_KILLED = "the machine took back its memory"
    """systemd-oomd killed the lane's own space on the machine."""
    DAEMON_KILLED = "the machine took back its account's memory"
    """systemd-oomd killed the account's daemon space, which held the session
    because something had resumed it there (2026-09-05, four lanes at once)."""
    BOOT = "the laptop went down"
    """The process ran in a previous boot and did not come back."""
    RECOVERED = "the connection came back"
    """`claude-acct recover`: a turn died on a transient error and the
    handoff asks for the session to be put back to work where it is."""
    STRONGER_MODEL = "the stronger model is back"
    """`claude-acct`'s switch-back: the session ran on the weaker rung and
    the handoff asks for it to come back on the stronger one."""
    KILLED = "its process was ended by a signal or a crash"
    """The journal names an ending that is not the memory's — a signal, a
    core dump, a unit failed for another reason. Not the machine's hand as
    the plan lists it, so never resumed by the board (finding 4, 2026-09-09)."""
    STOPPED = "it was stopped through its account"
    """`claude stop` ran: the owner's Stop, a verb, or the runtime's release."""
    UNKNOWN = "the cause is not established"
    """Nothing on the machine names it; never a permission to resume."""


MACHINE_ENDED: frozenset[Cause] = frozenset(
    {
        Cause.WALL,
        Cause.LANE_KILLED,
        Cause.DAEMON_KILLED,
        Cause.BOOT,
        Cause.RECOVERED,
        Cause.STRONGER_MODEL,
    }
)
"""The causes that were the machine's hand: each has an end the board can
read, so a lane they interrupted comes back by itself (ruling 1)."""


class Disposition(StrEnum):
    """What the work stood at when the session stopped, from the card's
    record and never from the process (ruling 7)."""

    CLOSED = "closed"
    """The card's close landed in this life of the lane: finished work."""
    OWNERS = "the owner's"
    """A question, an ASK or Q row, a ruling not yet given, or his own move
    out of Executing: nothing resumes until he acts."""
    UNFINISHED = "unfinished"
    """Neither: the record shows no close and no question."""


class Sighting(BaseModel):
    """A session seen alive in a lane, by the loop's own read of /proc: the
    process, the space it ran in and the boot it ran in. What makes a death
    a death — a row that *had* a process and now has none — and what a
    death is named from."""

    session_id: str
    project: str
    card_number: int
    pid: int
    scope: str | None
    boot_id: str | None
    first_seen: datetime
    last_seen: datetime
    released_at: datetime | None = None
    """When the loop stopped this session because its lane folded and closed;
    one stop per life, said once."""
    scoped_at: datetime | None = None
    """When the loop put this session back in its lane's own space; one
    adoption per life, said once."""


class Death(BaseModel):
    """Why a session's process is gone, as the board could establish it."""

    session_id: str
    project: str
    card_number: int
    cause: Cause
    words: str
    """The sentence the card shows, with the evidence in it."""
    evidence: str
    """The line or fact that named the cause, verbatim."""
    last_alive_at: datetime | None
    """When the process was last known alive: the sighting, else the
    transcript's last record."""
    named_at: datetime
    settled: bool
    """False while the cause is not established and evidence may still
    arrive; the loop reads the machine again for it until the horizon."""


class Park(BaseModel):
    """A lane the machine will bring back, waiting on an end it can read:
    a limit's reset, the machine's memory holding above the floor for a
    beat, an account with room, or the hour's count clearing. Never a
    verdict on the owner (ruling 3)."""

    id: int
    project: str
    card_number: int
    session_id: str
    cause: Cause
    words: str
    """What the park waits on, as the card says it."""
    waits_on: str
    """Which end lifts it: `clock` (the hour's count, until `until`),
    `allowance` (a reset, or the rule finding room elsewhere sooner),
    `floor` (the machine's memory held above the floor for a beat), or
    `rule` (an account with room, asked every pass)."""
    until: datetime | None
    """When the wait ends by the clock, when the board knows."""
    held_since: datetime | None
    """For a memory park: the first pass at which the floor read satisfied;
    the park lifts once that has held for a whole beat."""
    started_at: datetime
    lifted_at: datetime | None
    lifted_words: str | None


class Recovery(BaseModel):
    """One attempt by the board to bring an interrupted lane back: written
    before the launch, so a second process — or this one after a restart —
    finds it and never makes a second replacement (item 2). Closed with the
    launch's verdict; a launch that failed counts against the cause's
    once-per-horizon budget, and a wait before any launch is no row."""

    id: int
    project: str
    card_number: int
    session_id: str
    """The interrupted session."""
    cause: Cause
    words: str
    started_at: datetime
    replacement: str | None
    """The session id that lives on, once known."""
    verdict: str | None
    """`alive`, `dead`, `unconfirmed`, `found` (on a restart), or `lost`."""
    ended_at: datetime | None
    note: str | None


class Boot(BaseModel):
    """One boot of the machine as the journal lists it: which one this is
    (0 now, negative before), its id, and when its first and last entries
    were written. A session whose last sighting lies in a previous boot,
    close to that boot's last entry, went down with the machine."""

    index: int
    boot_id: str
    first_entry: datetime
    last_entry: datetime


class Named(BaseModel):
    """What the reader could establish about a session's ending: the cause,
    the sentence, the evidence, when the process was last known alive, and
    whether more evidence may still arrive."""

    cause: Cause
    words: str
    evidence: str
    last_alive_at: datetime | None
    settled: bool


class Ended(BaseModel):
    """Why a session's process is gone, in one line, as one machine's
    runtime answers it over the wire (card #83); None when nothing on that
    machine says."""

    why: str | None
