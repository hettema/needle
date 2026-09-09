"""Another machine's runtime, asked over the wire (card #83).

The board reads and acts on a machine it does not run on through that
machine's own `needle`: every verb here runs `needle <verb> --json` there
over `ssh` and validates what comes back into the same domain value the
verb answers here, so the typed edge every verb already has is the whole
protocol and there is no second one. Nothing on the other machine is read
as a file or a process from here — the registries, `/proc`, the journal,
the user manager and the multiplexer are that machine's runtime's to read,
and it answers for them.

What is not asked over the wire: the store. The other machine's `needle`
keeps its own ledger of what it started and moved (its default store), and
the board's runtime copies each answer into the one board store as the
record of where the session runs, so the board's records are the board's.
"""

import json
import shlex
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from domain.dial import Headroom, ScopeHeld, ScopePids, ScopeStop
from domain.ending import Boot, Ended, Named, Sighting
from domain.launch import Launch, Rescoped, Start, Stopped, WindowlessStart
from domain.machine import Machine
from domain.notice import Notice, Said, Told
from domain.session import Session
from domain.slot import Expired, Limits, LimitsRead, Rung, Where
from runtime import machine

T = TypeVar("T", bound=BaseModel)

VERB_SECONDS = 60.0
"""A verb that walks the ladder can take a minute; a read answers in a second."""
START_SECONDS = 240.0
"""A start observes the launch for a while before it answers (the walk's
verify window per rung, and there may be several rungs)."""


class RemoteRefused(Exception):
    """The other machine answered, and not with the value asked for: its
    `needle` is missing, refused the verb, or printed something that is not
    the shape. The words say which."""


def _tried_argument(tried: list[Rung]) -> str:
    return ",".join(r.slot if r.model is None else f"{r.slot}:{r.model}" for r in tried)


class Remote:
    """One machine's runtime as the board's calls it."""

    def __init__(self, machine: Machine):
        self.machine = machine

    def _line(self, argv: list[str]) -> str:
        return f"{self.machine.command} {shlex.join(argv)}"

    def _raw(self, argv: list[str], *, timeout: float = VERB_SECONDS) -> str:
        host = self.machine.host
        if host is None:
            raise machine.Unreachable(f"{self.machine.name} has no host the board can reach it by")
        try:
            done = machine.run_line(host, self._line(argv), timeout=timeout)
        except machine.Timeout as slow:
            raise RemoteRefused(
                f"{self.machine.name} did not answer `needle {argv[0]}` within {timeout:.0f} s"
            ) from slow
        if done.returncode == 127:
            raise RemoteRefused(
                f"{self.machine.name} has no needle at `{self.machine.command}`: "
                f"{(done.stderr or done.stdout).strip()[:200]}"
            )
        # A verb answers its JSON on stdout and exits 1 when the thing asked
        # for did not happen (a refused placement, a dead launch): the value
        # still says why, so it is read; only a non-JSON answer is a refusal.
        if done.returncode not in (0, 1) or not done.stdout.strip():
            raise RemoteRefused(
                f"{self.machine.name} refused `needle {argv[0]}` (exit {done.returncode}): "
                f"{(done.stderr or done.stdout).strip()[:300]}"
            )
        return done.stdout

    def _ask(self, argv: list[str], model: type[T], *, timeout: float = VERB_SECONDS) -> T:
        text = self._raw([*argv, "--json"], timeout=timeout)
        try:
            return model.model_validate_json(text)
        except ValidationError as wrong:
            raise RemoteRefused(
                f"{self.machine.name} answered `needle {argv[0]}` with something that is not a "
                f"{model.__name__}: {wrong.errors()[0].get('msg', '')} at "
                f"{'.'.join(str(p) for p in wrong.errors()[0].get('loc', ()))}"
            ) from wrong

    def _ask_list(self, argv: list[str], model: type[T]) -> list[T]:
        text = self._raw([*argv, "--json"])
        try:
            blob = json.loads(text)
            return [model.model_validate(item) for item in blob]
        except (json.JSONDecodeError, ValidationError, TypeError) as wrong:
            raise RemoteRefused(
                f"{self.machine.name} answered `needle {argv[0]}` with something that is not a "
                f"list of {model.__name__}: {str(wrong)[:200]}"
            ) from wrong

    # ── reading ────────────────────────────────────────────────────────

    def sessions(self) -> list[Session]:
        return self._ask_list(["sessions"], Session)

    def where(self, from_slot: str | None, tried: list[Rung], *, cached: bool) -> Where:
        argv = ["where"]
        if not cached:
            argv.append("--live")
        if from_slot:
            argv += ["--from", from_slot]
        if tried:
            argv += ["--tried", _tried_argument(tried)]
        return self._ask(argv, Where, timeout=120.0)

    def room(self, *, hold: bool) -> Headroom:
        return self._ask(["room", *(["--hold"] if hold else [])], Headroom)

    def scopes(self) -> list[ScopeHeld]:
        return self._ask_list(["scopes", "--held"], ScopeHeld)

    def scope_pids(self, unit: str) -> list[int]:
        return self._ask(["scopes", "--pids", unit], ScopePids).pids

    def boots(self) -> list[Boot]:
        return self._ask_list(["boots"], Boot)

    def limits(self, slot: str) -> Limits | None:
        return self._ask(["limits", slot], LimitsRead).limits

    def why_ended(self, short_id: str) -> str | None:
        return self._ask(["ended", short_id], Ended).why

    def cause_of(self, short_id: str, *, units: list[str], sighting: Sighting | None) -> Named:
        argv = ["cause", short_id]
        for unit in units:
            argv += ["--unit", unit]
        if sighting is not None:
            argv += ["--sighting", sighting.model_dump_json()]
        return self._ask(argv, Named)

    # ── acting ─────────────────────────────────────────────────────────

    def start(self, request: Start | WindowlessStart) -> Launch:
        argv = [
            "start",
            request.repo,
            request.card,
            request.brief,
            "--effort",
            request.effort.value,
        ]
        if isinstance(request, Start):
            if request.from_slot:
                argv += ["--from", request.from_slot]
        else:
            argv.append("--windowless")
        return self._ask(argv, Launch, timeout=START_SECONDS)

    def stop(self, short_id: str, *, keep_handoff: bool) -> Stopped:
        argv = ["stop", short_id, *(["--keep-handoff"] if keep_handoff else [])]
        return self._ask(argv, Stopped, timeout=120.0)

    def move(self, short_id: str, to_slot: str | None) -> Launch:
        argv = ["move", short_id, *(["--to", to_slot] if to_slot else [])]
        return self._ask(argv, Launch, timeout=START_SECONDS)

    def resume(
        self,
        short_id: str,
        *,
        prompt: str | None,
        card: str | None,
        to_slot: str | None,
        reason: str | None,
    ) -> Launch:
        argv = ["resume", short_id]
        if prompt is not None:
            argv += ["--prompt", prompt]
        if card is not None:
            argv += ["--card", card]
        if to_slot is not None:
            argv += ["--to", to_slot]
        if reason is not None:
            argv += ["--reason", reason]
        return self._ask(argv, Launch, timeout=START_SECONDS)

    def rescope(self, short_id: str, card: str) -> Rescoped:
        return self._ask(["rescope", short_id, card], Rescoped)

    def stop_scope(self, unit: str) -> ScopeStop:
        return self._ask(["scopes", "--stop", unit], ScopeStop)

    def expire_handoff(self, session_id: str) -> Expired:
        return self._ask(["expire-handoff", session_id], Expired)

    def show(self, slug: str, number: int) -> Said:
        return self._ask(["show", slug, str(number)], Said)

    def tell(self, notice: Notice, opens: list[str]) -> Told:
        argv = ["tell", "--notice", notice.model_dump_json()]
        for word in opens:
            argv += ["--open", word]
        return self._ask(argv, Told)
