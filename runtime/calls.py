"""One reading of a call against the one list and the answer file.

`needle wait` and the loop's tending make the same reading (plan 17, item
2): the answer landed or changed after the call; the colleague was moved
and the record follows the fork; it is blocked on a wall or a question; its
turn or its process ended without the note; or nothing yet. Pure over what
the caller hands in, so the two readers cannot drift apart. The verb owns
nothing of the colleague's life: a wall is the lifecycle owner's, and this
only reports it.
"""

from datetime import UTC, datetime
from pathlib import Path

from domain.call import Call, CallOutcome, CallVerdict
from domain.session import Session, SessionState


def answer_landed(call: Call) -> datetime | None:
    """When the answer file last changed, if after the call; None otherwise."""
    try:
        stat = Path(call.answer).stat()
    except OSError:
        return None
    changed = datetime.fromtimestamp(stat.st_mtime, UTC)
    return changed if changed >= call.called_at and stat.st_size > 0 else None


def judge(
    call: Call,
    sessions: list[Session],
    *,
    why_ended: str | None,
    moved_words: str | None,
) -> CallVerdict | None:
    """What the call's state is on this read; None while the colleague is
    still at work and nothing has landed. `why_ended` is the runtime's
    reason for a dead process, asked only when one is dead; `moved_words`
    the rescue's reason when a live fork of the called session exists."""
    landed = answer_landed(call)
    if landed is not None:
        first = _first_line(call.answer)
        return CallVerdict(
            outcome=CallOutcome.LANDED,
            words=f"{call.answer} landed at {landed.isoformat(timespec='seconds')}: {first}",
            session_id=call.session_id,
            slot=call.slot,
        )
    by_id = {s.session_id: s for s in sessions if not s.stale}
    fork = next(
        (s for s in sessions if s.resumed_from == call.session_id and s.pid is not None), None
    )
    if fork is not None:
        return CallVerdict(
            outcome=CallOutcome.MOVED,
            words=(
                f"{call.name} moved to {fork.slot} as {fork.short_id}"
                + (f": {moved_words}" if moved_words else "")
                + "; the call follows it"
            ),
            session_id=fork.session_id,
            slot=fork.slot,
        )
    session = by_id.get(call.session_id)
    if session is None:
        return CallVerdict(
            outcome=CallOutcome.ENDED,
            words=f"{call.name} ({call.session_id.split('-')[0]}) is in no registry any more",
            session_id=call.session_id,
            slot=call.slot,
        )
    if session.wall is not None:
        return CallVerdict(
            outcome=CallOutcome.BLOCKED,
            words=f"{session.short_id} hit a limit on {session.slot}: {session.wall.reason}",
            session_id=call.session_id,
            slot=call.slot,
        )
    if session.pid is None:
        return CallVerdict(
            outcome=CallOutcome.ENDED,
            words=f"{session.short_id} ended without its note"
            + (f": {why_ended}" if why_ended else ""),
            session_id=call.session_id,
            slot=call.slot,
        )
    if session.state == SessionState.BLOCKED:
        return CallVerdict(
            outcome=CallOutcome.BLOCKED,
            words=f"{session.short_id} is blocked: {session.detail or 'no detail recorded'}",
            session_id=call.session_id,
            slot=call.slot,
        )
    if session.state in (SessionState.DONE, SessionState.IDLE):
        return CallVerdict(
            outcome=CallOutcome.ENDED,
            words=f"{session.short_id} finished its turn without its note ({call.answer})",
            session_id=call.session_id,
            slot=call.slot,
        )
    return None


def _first_line(path: str) -> str:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    return line.strip()
    except OSError:
        pass
    return ""
