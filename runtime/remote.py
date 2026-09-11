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
from domain.handout import Dispatch
from domain.lane import Checkouts, Edited, LaneDocs, LaneTip
from domain.launch import Launch, Rescoped, Start, Stopped, WindowlessStart
from domain.machine import Machine
from domain.notice import Notice, Said, Told
from domain.session import LaneTokens, Session, TranscriptSize
from domain.slot import Expired, Limits, LimitsRead, Rung, Where
from runtime import git, machine

T = TypeVar("T", bound=BaseModel)

READ_SECONDS = 45.0
"""A read answers in a second, and the bound is what a stalled machine can
hold the board's beat for, per read (Codex's reading of card #83's second
pass: the beat holds the door lock, so every remote read is a bound on
the doors). Twenty was the first bound; the laptop under its memory floor
answered `sessions` and `worktrees` in more than twenty seconds in bursts
on the moved board's first afternoon (2026-09-10, 16:38–17:25Z, the same
reads answering in a second between), and every such miss read the
laptop as unread and its lanes as unchanged — worse for the board than a
door held a little longer."""
VERB_SECONDS = 60.0
"""A verb that walks the ladder can take a minute."""
START_SECONDS = 240.0
"""A start observes the launch for a while before it answers (the walk's
verify window per rung, and there may be several rungs)."""


class RemoteRefused(Exception):
    """The other machine answered, and not with the value asked for: its
    `needle` is missing, refused the verb, or printed something that is not
    the shape. The words say which."""


class RemoteTimeout(RemoteRefused):
    """The other machine did not answer within the deadline. What it did is
    unknown — a launch may have landed there — so a caller says unconfirmed,
    never dead (Codex's reading of card #83's second pass)."""


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
            raise RemoteTimeout(
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

    def _ask(self, argv: list[str], model: type[T], *, timeout: float = READ_SECONDS) -> T:
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
        text = self._raw([*argv, "--json"], timeout=READ_SECONDS)
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
        """Every session there, without the brief each opened with: the
        board never reads it from another machine, and with it the answer
        was megabytes (the first live move, 2026-09-10)."""
        return self._ask_list(["sessions", "--lean"], Session)

    def where(self, from_slot: str | None, tried: list[Rung], *, cached: bool) -> Where:
        argv = ["where"]
        if not cached:
            argv.append("--live")
        if from_slot:
            argv += ["--from", from_slot]
        if tried:
            argv += ["--tried", _tried_argument(tried)]
        return self._ask(argv, Where, timeout=VERB_SECONDS)

    def room(self, *, hold: bool, owners: dict[str, tuple[str, int]] | None = None) -> Headroom:
        argv = ["room", *(["--hold"] if hold else [])]
        for unit, (slug, number) in (owners or {}).items():
            argv += ["--owner", f"{unit}={slug}:{number}"]
        return self._ask(argv, Headroom)

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

    # ── a lane's ground: its worktree, its edits, its documents ────────

    def worktrees(self, repo: str) -> dict[str, str | None]:
        return self._ask(["worktrees", repo], Checkouts).checkouts

    def tip(self, repo: str, branch: str) -> LaneTip:
        return self._ask(["tip", repo, branch], LaneTip)

    def edits(self, checkout: str, *, birth: str | None = None, tip: str | None = None) -> set[str]:
        argv = ["edits", checkout]
        if birth is not None or tip is not None:
            argv.append("--lane")
        if birth is not None:
            argv += ["--birth", birth]
        if tip is not None:
            argv += ["--tip", tip]
        return set(self._ask(argv, Edited).files)

    def lane_docs(self, checkout: str, candidates: list[str], *, reviews: bool) -> LaneDocs:
        argv = ["lane-docs", checkout]
        for candidate in candidates:
            argv += ["--plan", candidate]
        if reviews:
            argv.append("--reviews")
        return self._ask(argv, LaneDocs)

    def dispatches(self, cwd: str) -> list[Dispatch] | None:
        text = self._raw(["dispatches", cwd, "--json"], timeout=READ_SECONDS)
        if text.strip() == "null":
            return None
        try:
            return [Dispatch.model_validate(item) for item in json.loads(text)]
        except (json.JSONDecodeError, ValidationError, TypeError) as wrong:
            raise RemoteRefused(
                f"{self.machine.name} answered `needle dispatches` with something that is not a "
                f"list of Dispatch: {str(wrong)[:200]}"
            ) from wrong

    def transcript_size(self, short_id: str) -> int | None:
        return self._ask(["transcript-size", short_id], TranscriptSize).size

    def tokens(self, cwd: str) -> int | None:
        """What the lane's sessions cost there, counted once (card #58)."""
        return self._ask(["tokens", cwd], LaneTokens).tokens

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

    def push(self, worktree: str, *, promote_main: bool) -> git.Folded:
        """The lane's fold, run where the lane is: its branch pushed to the
        trunk from the checkout that holds it (card #83, item 3)."""
        argv = ["push", "--worktree", worktree, *(["--main"] if promote_main else [])]
        return self._ask(argv, git.Folded, timeout=START_SECONDS)

    def level(self, repo: str) -> git.Levelled:
        """That machine's clone of a project brought level with the trunk:
        a fetch and a fast-forward, bounded like any verb — a stalled
        machine costs the beat a minute per project, not four (Codex's
        eighth pass on card #83)."""
        return self._ask(["level", repo], git.Levelled, timeout=VERB_SECONDS)

    def stop(self, short_id: str, *, keep_handoff: bool) -> Stopped:
        argv = ["stop", short_id, *(["--keep-handoff"] if keep_handoff else [])]
        return self._ask(argv, Stopped, timeout=VERB_SECONDS)

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
        return self._ask(["rescope", short_id, card], Rescoped, timeout=VERB_SECONDS)

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
