"""Why a session ended, read from the machine at the end rather than guessed
(plan 68, item 1).

A death is named from what took the *latest* life of the process: the wall
detector's file, the journal of the space that held it — its lane's own, or
the account's daemon space when something had resumed it there — inside
this life's window, or the boot it ran in when the machine went down under
it. Never from the registry's recorded state or its progress note, which say
what the session was doing and not why it stopped (ruling 7): on 2026-09-08
the board's "finished its turn" was wrong for fifteen of twenty-one lanes.
An ending nothing names is written as not established, with when the
process was last known alive, and is never a permission to resume.
"""

import re
from datetime import UTC, datetime

from domain.ending import Boot, Cause, Named, Sighting
from domain.session import Session
from runtime import handoffs, machine

JOURNAL_LINES = 400
"""How many lines of a space's journal are read from the life's start: a
lane's space writes a handful a day, the daemon's a few hundred (every
window and probe), and a telling line inside the window is what is wanted,
not the tail."""
_TELLING = ("killed", "oom", "out of memory", "signal", "failed", "dumped core")
"""A scope's accounting lines (`Consumed …`, `Deactivated`) are how every scope
ends and say nothing about why; only these do."""
BOOT_SLACK_SECONDS = 180.0
"""How close to a previous boot's last journal entry a session's last
sighting must lie for the boot to be its death: the loop reads every thirty
seconds, and a transcript is written on every turn, so a process alive
inside this window of the machine going down went down with it. Further
from the end, the process may have died of anything before the boot, and
the boot is not named."""

_STAMPED = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z))\s+(.*)$"
)
_SYSLOG_HEAD = re.compile(r"^\S+\s+\S+\[\d+\]:\s+")
"""The host and the writer (`DH systemd[1288]: `) in front of every
short-iso line; the message after them is what the card shows."""


class JournalLine:
    __slots__ = ("at", "text", "unit")

    def __init__(self, unit: str, at: datetime | None, text: str):
        self.unit = unit
        self.at = at
        self.text = text


def _stamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def journal_of(unit: str, *, since: datetime | None = None) -> list[JournalLine]:
    """The unit's lines from `since` on, each with its time when the line
    carries one."""
    lines: list[JournalLine] = []
    stamp = since.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC") if since else None
    for raw in machine.journal(unit, JOURNAL_LINES, since=stamp):
        match = _STAMPED.match(raw)
        if match:
            text = _SYSLOG_HEAD.sub("", match.group(2).strip(), count=1)
            lines.append(JournalLine(unit, _stamp(match.group(1)), text))
        else:
            lines.append(JournalLine(unit, None, raw))
    return lines


def _micros(value: object) -> datetime | None:
    if isinstance(value, int | float) and value > 0:
        return datetime.fromtimestamp(float(value) / 1_000_000, UTC)
    return None


def boots() -> list[Boot]:
    """The machine's boots, newest first, as the journal lists them."""
    found: list[Boot] = []
    for blob in machine.boots():
        index, boot_id = blob.get("index"), blob.get("boot_id")
        first, last = _micros(blob.get("first_entry")), _micros(blob.get("last_entry"))
        if (
            not isinstance(index, int)
            or not isinstance(boot_id, str)
            or first is None
            or last is None
        ):
            continue
        found.append(Boot(index=index, boot_id=boot_id, first_entry=first, last_entry=last))
    return sorted(found, key=lambda b: -b.index)


def _when(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%d %H:%MZ")


def cause_of(
    session: Session,
    *,
    units: list[str],
    sighting: Sighting | None,
    boots_seen: list[Boot],
    last_activity: datetime | None,
    now: datetime,
) -> Named:
    """What took this session's process. `units` are the spaces it may have
    run in, the lane's own first and the account's daemon space after; a
    telling journal line counts only inside this life's window — after the
    first sighting, or the registry's birth of this session id — so a kill
    that took a previous life is never named for this one (#435's second
    ending at 20:29Z on 2026-09-05 was read as the lane space's 18:37Z kill,
    which took its first). The newest telling line wins, and its unit says
    which space was killed."""
    if session.wall is not None and handoffs.cause_of(session.wall) is Cause.WALL:
        reason = session.wall.reason.strip().splitlines()[0] if session.wall.reason.strip() else ""
        return Named(
            cause=Cause.WALL,
            words=f"{Cause.WALL.value} on {session.slot}"
            + (f" ({reason})" if reason else "")
            + f", at {_when(session.wall.at)}",
            evidence=session.wall.reason,
            last_alive_at=session.wall.at,
            settled=True,
        )
    if session.recorded == "stopped" and session.detail in ("", "stopped"):
        # `claude stop` writes exactly `stopped`; the daemon writes the same
        # state with its own words for a session it lost ("ended while the
        # background service was off", Hello Revenue #435), which is a death
        # it is reporting, not a stop it made — read on for the cause.
        return Named(
            cause=Cause.STOPPED,
            words=Cause.STOPPED.value,
            evidence="the registry reads stopped",
            last_alive_at=sighting.last_seen if sighting else last_activity,
            settled=True,
        )
    life_start = sighting.first_seen if sighting else session.created_at
    last_alive = sighting.last_seen if sighting else last_activity
    # A telling line counts only after the life began *and* after the
    # process was last known alive: a kill the process outlived — the
    # daemon space's kill of 2026-09-05 sits in the journal of every lane
    # that ran under it, before and after — is not this death's cause.
    known = [t for t in (life_start, last_alive) if t is not None]
    window = max(known) if known else None
    telling: list[JournalLine] = []
    if window is not None:
        for unit in units:
            for line in journal_of(unit, since=window):
                if line.at is None or line.at < window:
                    continue
                if any(t in line.text.lower() for t in _TELLING):
                    telling.append(line)
    if telling:
        # Stable, so of two lines at one second the later in the journal wins.
        newest = sorted(telling, key=lambda line: line.at or window)[-1]
        assert newest.at is not None
        cause = Cause.LANE_KILLED if newest.unit == units[0] else Cause.DAEMON_KILLED
        return Named(
            cause=cause,
            words=f"{cause.value} at {_when(newest.at)} ({newest.unit}: {newest.text})",
            evidence=f"{newest.unit} {newest.at.isoformat()} {newest.text}",
            last_alive_at=last_alive,
            settled=True,
        )
    current = next((b for b in boots_seen if b.index == 0), None)
    if last_alive is not None and current is not None:
        held = next((b for b in boots_seen if b.first_entry <= last_alive <= b.last_entry), None)
        if held is not None and held.index != 0:
            gap = (held.last_entry - last_alive).total_seconds()
            if gap <= BOOT_SLACK_SECONDS:
                return Named(
                    cause=Cause.BOOT,
                    words=(
                        f"{Cause.BOOT.value} at {_when(held.last_entry)} and came back at "
                        f"{_when(current.first_entry)}; the session's last turn is cut at "
                        f"{_when(last_alive)}"
                    ),
                    evidence=f"boot {held.boot_id} ended {held.last_entry.isoformat()}; "
                    f"boot {current.boot_id} began {current.first_entry.isoformat()}; "
                    f"last alive {last_alive.isoformat()}",
                    last_alive_at=last_alive,
                    settled=True,
                )
            return Named(
                cause=Cause.UNKNOWN,
                words=(
                    f"the process disappeared after its last activity at {_when(last_alive)}, "
                    f"in a boot that ended {gap / 3600:.1f} h later; {Cause.UNKNOWN.value}"
                ),
                evidence=f"boot {held.boot_id} ended {held.last_entry.isoformat()}; "
                f"last alive {last_alive.isoformat()}"
                + (
                    f"; the registry reads {session.recorded}: {session.detail}"
                    if session.detail
                    else ""
                ),
                last_alive_at=last_alive,
                settled=True,
            )
    when = f" after its last activity at {_when(last_alive)}" if last_alive else ""
    registry = (
        f"the registry reads {session.recorded}: {session.detail}"
        if session.recorded and session.detail
        else ""
    )
    return Named(
        cause=Cause.UNKNOWN,
        words=f"the process disappeared{when}; {Cause.UNKNOWN.value}",
        evidence=registry,
        last_alive_at=last_alive,
        settled=False,
    )
