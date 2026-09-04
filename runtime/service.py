"""The runtime as one typed façade: what the command line and, in slice 03,
the board call. Every method answers with a domain value or raises with a
sentence; nothing here reaches the machine except through the modules that
do so by name."""

import contextlib

from domain.launch import Launch, Rescue, Start, Stopped
from domain.session import Session
from domain.slot import Placement, Rung, Slot, Where
from domain.window import Opened, WindowKind
from infrastructure.store import Store
from runtime import handoffs, launch, machine, registry, rule, slots, windows


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

    def clear_rescues(self, ref: str) -> int:
        return self.store.clear_rescues(self.session(ref).session_id)

    def machine_is_reachable(self) -> list[str]:
        """Which of the commands the runtime needs are missing, by name."""
        missing: list[str] = []
        for name in ("claude", "claude-acct", "hyprctl", "omarchy-launch-tui", "busctl"):
            try:
                machine.which(name)
            except machine.CommandMissing:
                missing.append(name)
        return missing
