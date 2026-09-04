"""The WATCH row's grammar: a signal the board can read, or a written decline.

A card enters Executed only with a WATCH row naming what will be observed,
where, and by when (plan 03, item 5). The grammar is small and the parse is
lenient about everything but those three:

    WATCH: <what will be observed> — <kind> <target> [expect <value>]
        by <YYYY-MM-DD> [every <N>h|<N>d]

Kinds: `url <URL>` (2xx, and the text when `expect "..."` is given), `file
<path>` (exists in the project), `command <cmd>` (exit 0, and the text or a
count when `expect "..."` / `expect >= N` is given), `owner [<question>]`
(only the owner can read it; the board asks him at the due time). Anything
else is refused with this grammar in the message, never guessed at.
"""

import re
from datetime import date, datetime

from domain.column import Column
from domain.signal import Signal, SignalKind

_KIND = re.compile(r"(?:^|\s|—|-|:)\s*(url|file|command|owner)\b", re.I)
_BY = re.compile(r"\bby\s+(\d{4}-\d{2}-\d{2})\b")
_EVERY = re.compile(r"\bevery\s+(\d+(?:\.\d+)?)\s*(h|d|hours?|days?)\b", re.I)
_EXPECT = re.compile(r"\bexpect\s+(>=\s*\d+|\"[^\"]*\"|'[^']*'|\S+)")

GRAMMAR = (
    "WATCH: <what> — url|file|command|owner <target> [expect <value>] by <YYYY-MM-DD> "
    "[every <N>h|<N>d]"
)
DEFAULT_EVERY_HOURS = 24.0


class SignalUnreadable(Exception):
    """The WATCH row names no signal the board can read; the message says what is missing."""


def parse_watch(text: str) -> Signal:
    kinds = list(_KIND.finditer(text))
    if not kinds:
        raise SignalUnreadable(
            f"the WATCH row names no reader (url, file, command or owner). The grammar: {GRAMMAR}"
        )
    match = kinds[0]
    kind = SignalKind(match.group(1).lower())
    what = text[: match.start()].strip().rstrip("—-: ").strip() or text.strip()
    tail = text[match.end() :]
    by = _BY.search(tail)
    if by is None:
        raise SignalUnreadable(
            f"the WATCH row names no due date (`by YYYY-MM-DD`). The grammar: {GRAMMAR}"
        )
    try:
        due = date.fromisoformat(by.group(1))
    except ValueError as error:
        raise SignalUnreadable(f"the WATCH row's due date {by.group(1)!r} is not a date") from error
    every = _EVERY.search(tail)
    expect = _EXPECT.search(tail)
    cut = min(m.start() for m in (by, every, expect) if m is not None)
    target = tail[:cut].strip().rstrip("—-,;: ").strip()
    if kind != SignalKind.OWNER and not target:
        raise SignalUnreadable(
            f"the WATCH row names a {kind.value} reader but no target. The grammar: {GRAMMAR}"
        )
    every_hours = DEFAULT_EVERY_HOURS
    if every is not None:
        amount = float(every.group(1))
        every_hours = amount if every.group(2).lower().startswith("h") else amount * 24
        if every_hours <= 0:
            raise SignalUnreadable("the WATCH row's cadence must be above zero")
    expected: str | None = None
    if expect is not None:
        raw = expect.group(1).strip()
        expected = raw[1:-1] if raw[0] in "\"'" and raw[-1] == raw[0] else raw
    return Signal(
        what=what,
        kind=kind,
        target=target or what,
        expect=expected,
        due=due,
        every_hours=every_hours,
    )


def read_or_decline(text: str | None) -> tuple[Signal | None, str | None]:
    """The signal a WATCH row names, or why it names none."""
    if text is None:
        return None, "no WATCH row names a signal"
    try:
        return parse_watch(text), None
    except SignalUnreadable as why:
        return None, str(why)


def is_due(signal: Signal, *, last_read: datetime | None, now: datetime) -> bool:
    """Whether the cadence asks for a reading now."""
    if last_read is None:
        return True
    return (now - last_read).total_seconds() >= signal.every_hours * 3600


def past_due(signal: Signal, now: datetime) -> bool:
    return now.date() > signal.due


def where_after(signal: Signal, delivered: bool | None, now: datetime) -> tuple[Column | None, str]:
    """Where a reading sends an Executed card, with the reason in a sentence."""
    if delivered:
        return Column.DONE, f"the signal says delivered: {signal.what}"
    if past_due(signal, now):
        if delivered is None:
            return Column.DECISION_MOMENT, (
                f"the signal could not be read and its due date {signal.due.isoformat()} has passed"
            )
        return Column.DECISION_MOMENT, (
            f"the signal says not delivered and its due date {signal.due.isoformat()} has passed"
        )
    return None, "not delivered yet, and not yet due"
