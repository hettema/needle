"""Why a session ended, read from the machine rather than guessed.

A lane that dies for any reason other than a limit carries the machine's
reason in one line (plan 03, item 7): the journal of the transient scope
that held it (an out-of-memory kill, a signal, the machine restarting) or
the registry's own record. The wall detector's file is the one reason this
module never reads: a limit is `claude-acct`'s to name.
"""

from domain.session import Session
from runtime import machine

JOURNAL_LINES = 40
_TELLING = ("killed", "oom", "out of memory", "signal", "failed", "dumped core")
"""A scope's accounting lines (`Consumed …`, `Deactivated`) are how every scope
ends and say nothing about why; only these do."""


def journal_of(unit: str) -> list[str]:
    try:
        done = machine.run(
            [
                machine.which("journalctl"),
                "--user",
                "-u",
                unit,
                "-n",
                str(JOURNAL_LINES),
                "--no-pager",
                "-o",
                "cat",
            ],
            timeout=20,
        )
    except (OSError, machine.Timeout, machine.CommandMissing):
        return []
    if done.returncode != 0:
        return []
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def why_ended(session: Session, scope: str | None) -> str | None:
    """One line, from the journal of the session's scope when it says
    anything telling, else from the registry's own words."""
    if scope:
        telling = [line for line in journal_of(scope) if any(t in line.lower() for t in _TELLING)]
        if telling:
            return f"the journal for {scope} says: {telling[-1]}"
    if session.recorded == "stopped":
        said = session.detail if session.detail and session.detail != "stopped" else ""
        return "the session was stopped" + (f": {said}" if said else "")
    if session.recorded == "done":
        return "the session finished its turn and was not resumed"
    if session.detail:
        return f"the registry says: {session.detail}"
    return None
