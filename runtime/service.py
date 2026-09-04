"""The runtime as one typed façade: what the command line and, in slice 03,
the board call. Every method answers with a domain value or raises with a
sentence; nothing here reaches the machine except through the modules that
do so by name."""

import contextlib
import uuid
from pathlib import Path

from domain.gate import Gate
from domain.launch import Launch, Rescue, Start, Stopped
from domain.session import Session
from domain.signal import Signal
from domain.slot import Placement, Rung, Slot, Where
from domain.window import Focused, Opened, Window, WindowKind
from infrastructure.store import Store
from runtime import git, handoffs, launch, machine, reasons, registry, rule, signals, slots, windows

COMMANDS = ("claude", "claude-acct", "hyprctl", "omarchy-launch-tui", "busctl", "git", "curl")
"""What the runtime needs on PATH. `journalctl` is asked for a death's reason
and its absence is only a reason unknown."""


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

    def where(self, from_slot: str | None, tried: list[Rung], *, cached: bool = True) -> Where:
        return rule.where(from_slot, tried, cached=cached)

    def rescues(self, ref: str) -> list[Rescue]:
        return self.store.rescues(self.session(ref).session_id)

    # ── acting ─────────────────────────────────────────────────────────

    def start(self, request: Start) -> Launch:
        return launch.start(self.store, request)

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

    def machine_is_reachable(self) -> list[str]:
        """Which of the commands the runtime needs are missing, by name."""
        missing: list[str] = []
        for name in COMMANDS:
            try:
                machine.which(name)
            except machine.CommandMissing:
                missing.append(name)
        return missing
