"""Reading a card's signal: a URL, a file in the project, a command's output.

The board reads the signals it can and moves the card on what they say
(plan 03, item 5). A reading answers delivered, not delivered, or unreadable
with the reason; it never guesses. A signal only the owner can read is not
read here — the board asks him.
"""

import re
from pathlib import Path

from domain.signal import Signal, SignalKind
from runtime import machine

URL_SECONDS = 20.0
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
COMMAND_SECONDS = 120.0
WORDS_LENGTH = 200


def judge(signal: Signal, *, ok: bool, output: str) -> bool:
    """Did a reading say delivered? `ok` is the reader's own verdict (2xx,
    exit 0, exists); `expect` narrows it to the text or the count."""
    if not ok:
        return False
    if signal.expect is None:
        return True
    expect = signal.expect.strip()
    if expect.startswith(">="):
        wanted = float(expect[2:].strip())
        numbers = [float(n) for n in _NUMBER.findall(output)]
        return any(n >= wanted for n in numbers)
    return expect in output


def _shown(text: str) -> str:
    line = " ".join(text.strip().split())
    return line if len(line) <= WORDS_LENGTH else line[: WORDS_LENGTH - 1] + "…"


def read(signal: Signal, project_path: str) -> tuple[bool | None, str]:
    """(delivered, words). None when the signal could not be read."""
    if signal.kind == SignalKind.OWNER:
        return None, "only the owner can read this signal"
    if signal.kind == SignalKind.FILE:
        target = Path(project_path) / signal.target
        exists = target.exists()
        return (
            exists,
            f"{signal.target} {'exists' if exists else 'does not exist'} in {project_path}",
        )
    if signal.kind == SignalKind.URL:
        try:
            done = machine.run(
                [
                    machine.which("curl"),
                    "-sS",
                    "-L",
                    "-m",
                    str(int(URL_SECONDS)),
                    "-o",
                    "-",
                    "-w",
                    "\n%{http_code}",
                    signal.target,
                ],
                timeout=URL_SECONDS + 5,
            )
        except (OSError, machine.Timeout, machine.CommandMissing) as error:
            return None, f"{signal.target} could not be fetched: {error}"
        if done.returncode != 0:
            return (
                None,
                f"{signal.target} could not be fetched: {_shown(done.stderr or done.stdout)}",
            )
        body, _, code = done.stdout.rpartition("\n")
        ok = code.strip().startswith("2")
        delivered = judge(signal, ok=ok, output=body)
        expect = f", expecting {signal.expect!r}" if signal.expect else ""
        return (
            delivered,
            f"{signal.target} answered {code.strip() or '?'}{expect}: "
            f"{_shown(body) or 'empty body'}",
        )
    try:
        done = machine.run(
            [machine.which("bash"), "-lc", signal.target], cwd=project_path, timeout=COMMAND_SECONDS
        )
    except (OSError, machine.Timeout, machine.CommandMissing) as error:
        return None, f"`{signal.target}` could not run: {error}"
    output = done.stdout + ("\n" + done.stderr if done.stderr else "")
    delivered = judge(signal, ok=done.returncode == 0, output=output)
    expect = f", expecting {signal.expect}" if signal.expect else ""
    return (
        delivered,
        f"`{signal.target}` exited {done.returncode}{expect}: {_shown(output) or 'no output'}",
    )
