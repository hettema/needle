"""The runtime as one typed façade: what the command line and, in slice 03,
the board call. Every method answers with a domain value or raises with a
sentence; nothing here reaches the machine except through the modules that
do so by name."""

import contextlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from domain.call import Call, CallVerdict
from domain.dial import Meminfo
from domain.gate import Gate
from domain.handout import Dispatch
from domain.launch import Launch, Rescue, Start, Stopped, WindowlessStart
from domain.session import Session, SessionKind
from domain.signal import Signal
from domain.slot import Placement, Rung, Slot, Where
from domain.watercooler import Note
from domain.window import Focused, Opened, Window, WindowKind
from infrastructure.store import Store
from runtime import (
    calls,
    discussion,
    git,
    handoffs,
    launch,
    machine,
    reasons,
    registry,
    roles,
    rule,
    signals,
    slots,
    transcripts,
    windows,
)

COMMANDS = ("claude", "claude-acct", "hyprctl", "omarchy-launch-tui", "busctl", "git", "curl")
"""What the runtime needs on PATH. `journalctl` is asked for a death's reason
and its absence is only a reason unknown."""


_EPOCH = datetime.min.replace(tzinfo=UTC)


class NoSuchSession(Exception):
    """No registry on this machine holds the session named."""


class Runtime:
    def __init__(self, store: Store):
        self.store = store

    # ── reading ────────────────────────────────────────────────────────

    def slots(self) -> list[Slot]:
        return slots.registries()

    def handoffs(self) -> handoffs.Handoffs:
        return handoffs.read_handoffs()

    def sessions(self) -> list[Session]:
        """The one list: every registry, every row checked in /proc, one row
        per session id. Reading it also records the windows the owner has
        closed since the last read."""
        walls = handoffs.read_handoffs().by_session
        rows = registry.sessions(slots.registries(), walls)
        # With no compositor to ask, the windows' state stays as last recorded.
        with contextlib.suppress(windows.WindowRefused):
            windows.reconcile(self.store)
        return rows

    def session(self, ref: str) -> Session:
        """By short id or session id; the live copy before a stale one."""
        matches = [s for s in self.sessions() if ref in (s.short_id, s.session_id)]
        if not matches:
            raise NoSuchSession(f"no session {ref!r} is in any registry on this machine")
        return next((m for m in matches if not m.stale), matches[0])

    def colleague(self, ref: str) -> Session | tuple[str, str] | None:
        """Who a call names (plan 17, item 1): a session by short id or id,
        the most recent background session of a slot named, or — for a
        colleague no registry holds any more — its id and the directory
        its transcript says it ran in; None when nothing on this machine
        answers to the ref."""
        rows = self.sessions()
        matches = [s for s in rows if ref in (s.short_id, s.session_id)]
        if matches:
            return next((m for m in matches if not m.stale), matches[0])
        on_slot = [
            s for s in rows if s.slot == ref and s.kind == SessionKind.BACKGROUND and not s.stale
        ]
        if on_slot:
            return max(on_slot, key=lambda s: s.updated_at or s.created_at or _EPOCH)
        found = transcripts.find(ref)
        return (ref, found[0]) if found else None

    def notes(self) -> list[Note]:
        """The machine's watercooler as it stands, oldest change first."""
        return discussion.notes()

    def where(self, from_slot: str | None, tried: list[Rung], *, cached: bool = True) -> Where:
        return rule.where(from_slot, tried, cached=cached)

    def rescues(self, ref: str) -> list[Rescue]:
        return self.store.rescues(self.session(ref).session_id)

    # ── acting ─────────────────────────────────────────────────────────

    def start(self, request: Start) -> Launch:
        return launch.start(self.store, request)

    def start_windowless(self, request: WindowlessStart) -> Launch:
        """A session in the project's own checkout with no window and no
        worktree — a reading of a signal (plan 09, item 1) or the planning
        of a defect under the dial (plan 11, item 4): never a lane, so it is
        not `start`, which is the owner's click."""
        return launch.windowless(self.store, request)

    def move(self, ref: str, to_slot: str | None) -> Launch:
        session = self.session(ref)
        to: Placement | None = None
        if to_slot is not None:
            asked = rule.where(to_slot, [Rung(slot=session.slot, model=None)], cached=False)
            if asked.placement is None or asked.placement.slot != to_slot:
                why = asked.placement.why if asked.placement else asked.reason
                return launch.dead(
                    session.name,
                    [],
                    f"the rule would not place {session.short_id} on {to_slot}: {why}",
                    None,
                )
            to = asked.placement
        record = self.store.session_slot(session.session_id)
        return launch.move(self.store, session, to=to, card=record.card if record else session.name)

    def stop(self, ref: str) -> Stopped:
        return launch.stop(self.session(ref))

    def window(self, ref: str, kind: WindowKind | None) -> Opened:
        session = self.session(ref)
        record = self.store.session_slot(session.session_id)
        card = record.card if record else session.name
        look: Placement | None = None
        if session.pid is None:
            look = rule.where(session.slot, [], cached=False).placement
        return windows.open_window(self.store, session, kind=kind, card=card, look=look)

    def focus(self, ref: str) -> Focused:
        """Bring the session's open window forward, proved by the compositor."""
        return windows.focus_window(self.store, self.session(ref))

    def resume(self, ref: str, *, prompt: str | None, card: str | None = None) -> Launch:
        """Stop the session where it runs and resume it where the rule says,
        preferring the slot it is on, with the owner's words when given."""
        session = self.session(ref)
        record = self.store.session_slot(session.session_id)
        return launch.move(
            self.store,
            session,
            to=None,
            card=card or (record.card if record else session.name),
            prompt=prompt,
            spent=False,
        )

    def call(self, session: Session | tuple[str, str], *, brief: str, name: str) -> Launch:
        """Call a colleague warm (plan 17, item 1): resume its session with
        the brief through the one launch path, or from its transcript when
        no registry holds it. The verb owns nothing of the session's life
        after this (ruling 5)."""
        if isinstance(session, tuple):
            session_id, cwd = session
            return launch.resume_transcript(self.store, session_id, cwd, brief=brief, name=name)
        return launch.call(self.store, session, brief=brief, name=name)

    def judge_call(self, call: Call, sessions: list[Session] | None = None) -> CallVerdict | None:
        """One reading of a call against the one list and its answer file:
        what `needle wait` and the loop both make (plan 17, item 2)."""
        rows = self.sessions() if sessions is None else sessions
        session = next((s for s in rows if s.session_id == call.session_id and not s.stale), None)
        why = self.why_ended(session) if session is not None and session.pid is None else None
        fork = next(
            (s for s in rows if s.resumed_from == call.session_id and s.pid is not None), None
        )
        moved = None
        if fork is not None:
            history = self.store.rescues(fork.session_id)
            moved = history[-1].reason if history else None
        return calls.judge(call, rows, why_ended=why, moved_words=moved)

    def discuss(
        self,
        *,
        repo: str,
        card: str,
        brief: str,
        effort: Gate | None,
        what: str,
        kind: WindowKind = WindowKind.DISCUSS,
        session_id: str | None = None,
    ) -> tuple[Opened, str, Placement]:
        """A fresh conversation in a window, on the slot and model the rule
        chooses; answers the window, the session id it was given and where it
        runs. `kind` is the window's app-id kind: a card's Discuss, or the
        head's Idea about no card yet. The caller may choose the session id
        when its brief has to name it (an idea's document names the
        conversation it came from)."""
        where = rule.where(None, [], cached=False)
        if where.placement is None:
            raise windows.WindowRefused(f"the rule found nowhere to run: {where.reason}")
        session_id = session_id or str(uuid.uuid4())
        banner, command = windows.discuss_command(
            where.placement, cwd=repo, session_id=session_id, brief=brief, effort=effort, what=what
        )
        opened = windows.open_fresh(
            self.store,
            session_id=session_id,
            kind=kind,
            card=card,
            command=command,
            banner=banner,
            fresh=True,
        )
        return opened, session_id, where.placement

    def open_windows(self) -> list[Window]:
        return self.store.windows(open_only=True)

    def clear_rescues(self, ref: str) -> int:
        return self.store.clear_rescues(self.session(ref).session_id)

    # ── git, signals, reasons ──────────────────────────────────────────

    def worktrees(self, repo: str) -> dict[str, str | None]:
        return git.worktrees(repo)

    def edits(self, checkout: str) -> set[str]:
        return git.changed_files(checkout)

    def lane_files(self, checkout: str, *, birth: str | None, tip: str | None) -> set[str]:
        """Every file a lane touched from its birth to its tip, plus what its
        worktree still holds uncommitted: what the close reads to tell a code
        lane from a docs-only one (plan 11, item 1). Read after the fold, the
        diff against the trunk is empty, so the lane's own birth is the base."""
        return git.lane_files(checkout, birth=birth, tip=tip)

    def reverted(self, repo: str, tip: str) -> bool:
        """Whether a commit on the trunk says it reverts the lane's tip."""
        return git.reverted(repo, tip)

    def branch_tip(self, repo: str, branch: str) -> str | None:
        return git.head_of(repo, branch)

    def lane_folded(
        self, repo: str, branch: str | None, tip: str | None, birth: str | None
    ) -> bool | None:
        return git.lane_folded(repo, branch, tip, birth)

    def in_stable(self, repo: str, tip: str) -> bool:
        """Whether a commit is in origin/main, as last fetched."""
        return git.is_ancestor(repo, tip, f"{git.REMOTE}/{git.STABLE}") is True

    def level(self, repo: str) -> git.Levelled:
        return git.level(repo)

    def fold(self, worktree: str, *, promote_main: bool) -> git.Folded:
        return git.fold(worktree, promote_main=promote_main)

    def read_signal(self, signal: Signal, project_path: str) -> tuple[bool | None, str]:
        return signals.read(signal, project_path)

    def why_ended(self, session: Session) -> str | None:
        record = self.store.session_slot(session.session_id)
        return reasons.why_ended(session, record.scope if record else session.scope)

    def is_repository(self, path: str) -> bool:
        return (Path(path) / ".git").exists()

    def roles(self) -> list[str] | None:
        """The roles the machine names; None when it has no roles file."""
        return roles.roles()

    def dispatches(self, cwd: str) -> list[Dispatch] | None:
        """What every session that ran in `cwd` handed out, from its
        transcripts; None when none exists."""
        return transcripts.dispatches(cwd)

    def meminfo(self) -> Meminfo | None:
        """The machine's memory right now; None when it cannot be read."""
        try:
            return machine.meminfo()
        except (OSError, ValueError):
            return None

    def machine_is_reachable(self) -> list[str]:
        """Which of the commands the runtime needs are missing, by name."""
        missing: list[str] = []
        for name in COMMANDS:
            try:
                machine.which(name)
            except machine.CommandMissing:
                missing.append(name)
        return missing
