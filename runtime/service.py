"""The runtime as one typed façade: what the command line and, in slice 03,
the board call. Every method answers with a domain value or raises with a
sentence; nothing here reaches the machine except through the modules that
do so by name.

Since card #83 the façade stands on more than one machine: every verb that
reads or acts on a session, a process group, a journal or a screen goes to
the machine that holds it — here, through the modules by name, or on
another machine through that machine's own `needle` (`runtime.remote`).
Which machine is which is the store's knowledge (`needle machine add`), and
which row is this machine is the kernel's (`machine.machine_id`)."""

import contextlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from domain.call import Call, CallVerdict
from domain.dial import MEMORY_FLOOR_BYTES, Headroom, Meminfo, ScopeHeld, ScopeMemory, headroom
from domain.ending import Boot, Cause, Named, Sighting
from domain.gate import Gate
from domain.handout import Dispatch
from domain.lane import LaneDocs, LaneTip, ReviewText
from domain.launch import Launch, LaunchVerdict, Rescoped, Rescue, Start, Stopped, WindowlessStart
from domain.machine import Machine, MachineRoom, Timing, choose_machine
from domain.notice import Notice, Told
from domain.session import Session, SessionKind, SessionSlot
from domain.signal import Signal
from domain.slot import Handoff, Limits, Placement, Rung, Slot, Where
from domain.watercooler import Note
from domain.window import Focused, Opened, Window, WindowKind
from infrastructure import clock
from infrastructure.store import Store
from runtime import (
    calls,
    codex,
    discussion,
    git,
    handoffs,
    launch,
    limits,
    machine,
    notice,
    reasons,
    registry,
    roles,
    rule,
    signals,
    slots,
    transcripts,
    windows,
)
from runtime.remote import Remote, RemoteRefused, RemoteTimeout

log = logging.getLogger("needle.runtime")

COMMANDS = (
    "claude",
    "claude-acct",
    "busctl",
    "systemctl",
    "git",
    "curl",
    "ssh",
)
"""What the runtime needs on PATH wherever it runs. `journalctl` is asked
for a death's reason and its absence is only a reason unknown; `ssh` is how
another machine is asked (card #83) and its absence is every other machine
unreachable."""
DESKTOP_COMMANDS = ("hyprctl", "omarchy-launch-tui")
"""What the runtime needs on PATH on the machine with the owner's screen,
which is this one until the board runs elsewhere (card #83)."""

HIGH_WATER_DAYS = 14
"""The loop's window: the plan decides 32 or 64 GB on two weeks of marks."""
KILLED_HOURS = 24
"""The loop's daily count: lanes the system killed on a machine in the last day."""

_EPOCH = datetime.min.replace(tzinfo=UTC)
_UNREACHABLE = (machine.Unreachable, RemoteRefused)


class NoSuchSession(Exception):
    """No registry on this machine holds the session named."""


class Ambiguous(NoSuchSession):
    """The ref names more than one session, so it names none (plan 57)."""


class Runtime:
    def __init__(self, store: Store):
        self.store = store
        self.unread: dict[str, str] = {}
        """The machines whose sessions the last read could not reach, by
        name, with the transport's words (card #83): a session on one is
        unread, never ended, and nothing that acts on an ending — a death
        named, a lane released, a group swept — acts on it."""
        self._last_rows: dict[str, list[Session]] = {}
        """Each other machine's rows as last read, so an unreachable
        machine's lanes keep their last known state on the face."""
        self._lane_machines: dict[str, str] = {}
        """Which machine each worktree was last seen on, by path: what
        routes a lane's edits, tip and documents to the machine that has
        them."""

    # ── reading ────────────────────────────────────────────────────────

    def slots(self) -> list[Slot]:
        return slots.registries()

    def handoffs(self) -> handoffs.Handoffs:
        return handoffs.read_handoffs()

    # ── machines ───────────────────────────────────────────────────────
    # The machines the board knows (card #83): the store's rows, and this
    # one by the kernel's identity. A board nobody registered a machine on
    # is a one-machine board whose machine is the desktop, which is what
    # every board was until this card.

    def machines(self) -> list[Machine]:
        """Every machine the board knows, this one included: the registered
        rows, with this machine named from its hostname when no row is it."""
        rows = self.store.machines()
        own = machine.machine_id()
        if any(m.machine_id == own for m in rows):
            return rows
        return [
            Machine(
                name=machine.hostname(),
                machine_id=own,
                host=None,
                desktop=True,
                ground=None,
                command=machine.needle_command(),
                added_at=_EPOCH,
            ),
            *rows,
        ]

    def here(self) -> Machine:
        """The machine this runtime runs on."""
        own = machine.machine_id()
        return next(m for m in self.machines() if m.machine_id == own)

    def is_here(self, m: Machine) -> bool:
        return bool(m.machine_id) and m.machine_id == machine.machine_id()

    def desktop(self) -> Machine:
        """The machine with the owner's screen: the registered desktop, else
        this one."""
        return next((m for m in self.machines() if m.desktop), self.here())

    def desktop_host(self) -> str | None:
        """The host every window, focus and notification goes to; None when
        the screen is on this machine."""
        desktop = self.desktop()
        return None if self.is_here(desktop) else desktop.host

    def machine_named(self, name: str) -> Machine:
        """The machine a row names. An empty name is this one, because every
        row written before this card was this machine's; a name the board
        no longer knows is a machine with no host — everything routed to it
        answers unreachable, by that name, and nothing runs here in its
        stead (Codex's reading of card #83's second pass)."""
        if not name:
            return self.here()
        found = next((m for m in self.machines() if m.name == name), None)
        if found is not None:
            return found
        return Machine(
            name=name,
            machine_id="",
            host=None,
            desktop=False,
            ground=None,
            command=machine.needle_command(),
            added_at=_EPOCH,
        )

    def lane_machine(self, path: str) -> Machine:
        """The machine a worktree was last seen on, by its path; this one
        when no read has placed it."""
        return self.machine_named(self._lane_machines.get(path, ""))

    def machine_of(self, session: Session) -> Machine:
        return self.machine_named(session.machine)

    def _remote(self, m: Machine) -> Remote:
        return Remote(m)

    def _stamped(self, m: Machine, launch_: Launch, card: str) -> Launch:
        """The launch as the board records it: its placement and session
        carry the machine's name, and the board's own store holds where
        the session runs — a launch on another machine wrote that into
        that machine's ledger, not here."""
        placement = (
            launch_.placement.model_copy(update={"machine": m.name})
            if launch_.placement is not None
            else None
        )
        session = (
            launch_.session.model_copy(update={"machine": m.name})
            if launch_.session is not None
            else None
        )
        if session is not None and session.session_id:
            record = self.store.session_slot(session.session_id)
            self.store.record_session_slot(
                SessionSlot(
                    session_id=session.session_id,
                    slot=record.slot if record else session.slot,
                    card=record.card if record else card,
                    scope=record.scope if record else (launch_.scope or ""),
                    recorded_at=clock.now(),
                    machine=m.name,
                )
            )
        return launch_.model_copy(update={"placement": placement, "session": session})

    def room(
        self,
        *,
        hold: bool = False,
        owners: dict[str, tuple[str, int]] | None = None,
        read: set[str] | None = None,
    ) -> Headroom:
        """This machine against the floor: its memory, and what every group
        of ours holds, read by the one rule the head uses. With `hold`,
        every group that stands without the floor as its high mark is given
        it first (card #107), and the reading says which. `owners` names
        the card each unit is, when the caller (the board's loop) knows;
        `read` names the units asked for whether or not the manager lists
        them — every lane with hands on, by the name it was given at Start
        (plan 53, item 1)."""
        try:
            units: set[str] | None = set(machine.units_named(launch.SESSION_UNIT_PREFIX))
        except (OSError, machine.Timeout, machine.CommandMissing):
            units = None
        # Every lane with hands on is asked for by the name it was given at
        # Start, whether or not the manager lists it (plan 53, item 1): a
        # scope with no value is not a lane, and the read is what says so.
        if units is not None and read:
            units |= set(read)
        marked = self.hold_scopes_at(sorted(units), MEMORY_FLOOR_BYTES) if hold and units else []
        held = self.scope_memory(sorted(units)) if units else {}
        named = owners or {}
        scopes = (
            [
                ScopeMemory(
                    unit=unit,
                    held=held[unit],
                    project=named[unit][0] if unit in named else None,
                    card_number=named[unit][1] if unit in named else None,
                )
                for unit in sorted(units)
                if unit in held
            ]
            if held is not None and units is not None
            else None
        )
        return headroom(
            self.meminfo(), MEMORY_FLOOR_BYTES, clock.now(), scopes=scopes, marked=marked
        )

    def rooms(
        self,
        *,
        hold: bool = False,
        owners: dict[str, tuple[str, int]] | None = None,
        read: set[str] | None = None,
    ) -> list[MachineRoom]:
        """Every machine against the floor this pass, with what the board
        has measured on each: the two-week high-water mark and the day's
        kills. A machine that did not answer is a room of None with the
        transport's words, never a machine with room."""
        now = clock.now()
        found: list[MachineRoom] = []
        here = self.here()
        for m in self.machines():
            room: Headroom | None = None
            why: str | None = None
            if self.is_here(m):
                room = self.room(hold=hold, owners=owners, read=read)
            else:
                try:
                    room = self._remote(m).room(hold=hold)
                except _UNREACHABLE as error:
                    why = str(error)
            latest: dict[str, Timing] = {}
            for timing in self.store.timings(m.name):
                latest[timing.what] = timing
            found.append(
                MachineRoom(
                    machine=m,
                    here=self.is_here(m),
                    room=room,
                    why=why,
                    high_water=self.store.high_water(
                        m.name, since=now - timedelta(days=HIGH_WATER_DAYS)
                    ),
                    killed=len(
                        self.store.killed_on(
                            m.name, since=now - timedelta(hours=KILLED_HOURS), here=here.name
                        )
                    ),
                    timings=sorted(latest.values(), key=lambda t: t.what),
                )
            )
        return found

    def place(
        self, repo: str, rooms: list[MachineRoom] | None = None
    ) -> tuple[Machine | None, str]:
        """Which machine a card in `repo` runs on next, and why (the plan's
        item 4): the rule in `domain.machine.choose_machine`, over the rooms
        read this pass or read now."""
        return choose_machine(self.rooms() if rooms is None else rooms, repo)

    def _where_on(
        self, m: Machine, from_slot: str | None, tried: list[Rung], *, cached: bool
    ) -> Where:
        """The one rule, asked on the machine the work would run on: its
        `claude-acct` knows that machine's logins and allowances."""
        if self.is_here(m):
            answer = rule.where(from_slot, tried, cached=cached)
        else:
            try:
                answer = self._remote(m).where(from_slot, tried, cached=cached)
            except _UNREACHABLE as error:
                return Where(placement=None, reason=f"{m.name} could not be asked: {error}")
        if answer.placement is None:
            return answer
        return Where(
            placement=answer.placement.model_copy(update={"machine": m.name}), reason=answer.reason
        )

    def sessions(self) -> list[Session]:
        """The one list: every registry on every machine, every row checked
        in /proc there, one row per session id, each stamped with the
        machine it was read on. Reading it also records the windows the
        owner has closed since the last read. A machine that does not
        answer contributes no rows and is said in the log; its sessions are
        not gone, they are unread, and the lanes they hold read as ended
        only if nothing else knows better."""
        walls = handoffs.read_handoffs().by_session
        rows = registry.sessions(slots.registries(), walls)
        # Codex's sessions are rows of the same list (plan 57, item 3): read
        # from its rollouts, checked in /proc the same way, sorted under the
        # make's name where a Claude row sorts under its slot.
        here = self.here()
        rows = [
            r.model_copy(update={"machine": here.name})
            for r in [*rows, *codex.sessions(clock.now())]
        ]
        for m in self.machines():
            if self.is_here(m):
                continue
            try:
                read = [
                    r.model_copy(update={"machine": m.name}) for r in self._remote(m).sessions()
                ]
            except _UNREACHABLE as error:
                # Unread is not ended: the last rows stand, and the machine
                # is named unread so nothing acts on an ending there.
                log.warning("the sessions on %s could not be read: %s", m.name, error)
                self.unread[m.name] = str(error)
                rows += self._last_rows.get(m.name, [])
                continue
            self.unread.pop(m.name, None)
            self._last_rows[m.name] = read
            rows += read
        rows = registry.merge(rows)
        # With no compositor to ask, the windows' state stays as last recorded.
        with contextlib.suppress(windows.WindowRefused):
            windows.reconcile(self.store, host=self.desktop_host())
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
        answers to the ref. The other make answers to the same refs (plan
        57, item 1): its bare name is its most recent worker, a rollout id
        or its prefix is that rollout, and a prefix that names two is
        refused as naming none."""
        rows = self.sessions()
        matches = [s for s in rows if ref in (s.short_id, s.session_id)]
        named = {m.session_id for m in matches}
        if len(named) > 1:
            raise Ambiguous(
                f"{ref!r} names {len(named)} sessions ({', '.join(sorted(named))}); name one"
            )
        if matches:
            return next((m for m in matches if not m.stale), matches[0])
        on_slot = [
            s for s in rows if s.slot == ref and s.kind == SessionKind.BACKGROUND and not s.stale
        ]
        if on_slot:
            return max(on_slot, key=lambda s: s.updated_at or s.created_at or _EPOCH)
        if ref == codex.SLOT:
            return codex.warm()
        found = transcripts.find(ref)
        if found:
            return (ref, found[0])
        rollouts = codex.find(ref)
        if len(rollouts) > 1:
            named = ", ".join(sorted(r.session_id for r in rollouts))
            raise Ambiguous(f"{ref!r} names {len(rollouts)} Codex sessions ({named}); name one")
        return rollouts[0] if rollouts else None

    def notes(self) -> list[Note]:
        """The machine's watercooler as it stands, oldest change first."""
        return discussion.notes()

    def where(
        self,
        from_slot: str | None,
        tried: list[Rung],
        *,
        cached: bool = True,
        repo: str | None = None,
        rooms: list[MachineRoom] | None = None,
    ) -> Where:
        """Where work runs next. With a repository named, the machine is
        chosen first (the plan's item 4: the project's own machine, else
        the horsepower with room, else the desktop with room) and that
        machine's rule is asked; a full board is #53's refusal with every
        machine's numbers. Without one the rule here answers, stamped with
        this machine's name, which is what every caller before this card
        asked for."""
        if repo is None:
            return self._where_on(self.here(), from_slot, tried, cached=cached)
        chosen, why = self.place(repo, rooms)
        if chosen is None:
            return Where(placement=None, reason=why)
        return self._where_on(chosen, from_slot, tried, cached=cached)

    def rescues(self, ref: str) -> list[Rescue]:
        return self.store.rescues(self.session(ref).session_id)

    # ── acting ─────────────────────────────────────────────────────────

    def start(self, request: Start) -> Launch:
        """Start a lane where the machine rule puts it (card #83): here
        through the launcher, or on another machine through its own
        `needle start`, whose answer the board records as its own."""
        chosen, why = self.place(request.repo)
        if chosen is None:
            return launch.dead(request.card, [], why, None)
        if self.is_here(chosen):
            full = self._full_here()
            if full is not None:
                return launch.dead(request.card, [], full, None)
            return self._stamped(chosen, launch.start(self.store, request), request.card)
        return self._started_elsewhere(chosen, request)

    def _full_here(self) -> str | None:
        """This machine's room read at the moment of a launch, in the head's
        words when it is full: the machine a card was placed on rechecks its
        own floor before it launches, since room consumed between the
        choice and the launch — or a start asked of it directly — is not
        the chooser's to know (Codex's reading of card #83's second pass)."""
        room = self.room()
        return room.sentence if room.full else None

    def _started_elsewhere(self, chosen: Machine, request: Start | WindowlessStart) -> Launch:
        """A start on another machine, as the board records it. A reply that
        never came is unconfirmed, not dead: the launch may have landed
        there, and the next read of that machine's sessions shows it."""
        try:
            return self._stamped(chosen, self._remote(chosen).start(request), request.card)
        except (RemoteTimeout, machine.Unreachable) as lost:
            # A deadline passed or the connection dropped: either way what
            # landed there is unknown until its sessions are read again.
            return Launch(
                card=request.card,
                verdict=LaunchVerdict.UNCONFIRMED,
                session=None,
                placement=None,
                scope=None,
                attempts=[],
                reason=f"{chosen.name} did not answer; the launch may have landed: {lost}",
            )
        except RemoteRefused as error:
            return launch.dead(request.card, [], f"{chosen.name} could not start it: {error}", None)

    def start_windowless(self, request: WindowlessStart) -> Launch:
        """A session in the project's own checkout with no window and no
        worktree — a reading of a signal (plan 09, item 1) or the planning
        of a defect under the dial (plan 11, item 4): never a lane, so it is
        not `start`, which is the owner's click. Placed by the same machine
        rule as a lane, since it is a session on a machine's memory."""
        chosen, why = self.place(request.repo)
        if chosen is None:
            return launch.dead(request.card, [], why, None)
        if self.is_here(chosen):
            full = self._full_here()
            if full is not None:
                return launch.dead(request.card, [], full, None)
            return self._stamped(chosen, launch.windowless(self.store, request), request.card)
        return self._started_elsewhere(chosen, request)

    def move(self, ref: str, to_slot: str | None, *, reason: str | None = None) -> Launch:
        session = self.session(ref)
        on = self.machine_of(session)
        record = self.store.session_slot(session.session_id)
        card = record.card if record else session.name
        if not self.is_here(on):
            return self._moved_elsewhere(on, session, card, reason, self._remote(on).move, to_slot)
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
        return self._stamped(
            on, launch.move(self.store, session, to=to, card=card, reason=reason), card
        )

    def _moved_elsewhere(
        self,
        on: Machine,
        session: Session,
        card: str,
        reason: str | None,
        act,
        *args,
        **kwargs,
    ) -> Launch:
        """A move or resume done by another machine's runtime, recorded here
        as the board's own: the launch stamped and its session's row written,
        and the rescue written under the id that lives with the words the
        launch carries — that machine's ledger holds its own copy, and the
        board's rescue history is what the face reads."""
        try:
            done = act(session.short_id, *args, **kwargs)
        except _UNREACHABLE as error:
            return launch.dead(session.name, [], f"{on.name} could not move it: {error}", None)
        stamped = self._stamped(on, done, card)
        if stamped.session is not None and stamped.placement is not None:
            self.store.record_rescue(
                stamped.session.session_id,
                Rung(slot=session.slot, model=session.model),
                Rung(slot=stamped.placement.slot, model=stamped.placement.model),
                reason or stamped.reason or stamped.placement.why,
                clock.now(),
            )
        return stamped

    def stop(self, ref: str, *, keep_handoff: bool = False) -> Stopped:
        """End a session. A standing handoff is the machine's request to move
        it, and `cause_of` names an ended session with one as a wall to bring
        back — so a stop by the owner (the Stop door, `needle stop`) removes
        the handoff and is his stop, while the board's own stop of a walled
        session that waits for room keeps it (card #107)."""
        session = self.session(ref)
        on = self.machine_of(session)
        if self.is_here(on):
            stopped = launch.stop(session)
        else:
            try:
                stopped = self._remote(on).stop(session.short_id, keep_handoff=keep_handoff)
            except _UNREACHABLE as error:
                stopped = Stopped(
                    short_id=session.short_id,
                    session_id=session.session_id,
                    slot=session.slot,
                    gone=False,
                    seconds=0.0,
                    words=f"{on.name} could not be asked to stop it: {error}",
                )
        if keep_handoff:
            return stopped
        # A death the board already named a wall — the board's own stop on
        # the floor writes one — would still be brought back once the room
        # holds; the owner's stop is written over it, settled, so the lane
        # stays down (Codex's reading of card #107's second pass). The
        # record goes first and the handoff second: a crash between the two
        # leaves a settled stop the loop honours, never a wall it recovers.
        for project in self.store.projects():
            death = self.store.deaths(project.slug).get(session.session_id)
            if death is not None and death.cause is Cause.WALL:
                self.store.record_death(
                    death.model_copy(
                        update={
                            "cause": Cause.STOPPED,
                            "words": Cause.STOPPED.value,
                            "evidence": f"the owner stopped {session.short_id} on {session.slot}",
                            "named_at": clock.now(),
                            "settled": True,
                        }
                    )
                )
        # The other machine's own stop removed its handoff; this one's is here.
        if session.wall is not None and self.is_here(on):
            handoffs.remove(session.wall)
        return stopped

    def window(self, ref: str, kind: WindowKind | None) -> Opened:
        session = self.session(ref)
        record = self.store.session_slot(session.session_id)
        card = record.card if record else session.name
        on = self.machine_of(session)
        look: Placement | None = None
        size: int | None = None
        if session.pid is None:
            look = self._where_on(on, session.slot, [], cached=False).placement
            size = self.transcript_size(session)
        # The window opens on the desktop; it attaches over the tunnel when
        # the session's machine is not the desktop (card #83, item 4).
        via = None if on.machine_id == self.desktop().machine_id else on
        return windows.open_window(
            self.store,
            session,
            kind=kind,
            card=card,
            look=look,
            host=self.desktop_host(),
            via=via,
            size=size,
        )

    def focus(self, ref: str) -> Focused:
        """Bring the session's open window forward, proved by the compositor."""
        return windows.focus_window(self.store, self.session(ref), host=self.desktop_host())

    def resume(
        self,
        ref: str,
        *,
        prompt: str | None,
        card: str | None = None,
        placement: Placement | None = None,
        reason: str | None = None,
    ) -> Launch:
        """Stop the session where it runs and resume it where the rule says,
        preferring the slot it is on, with the owner's words when given.
        The board's own resume after a death it named (plan 68, item 5)
        passes the rung the rule answered now as `placement` — a handoff
        written days ago names a rung that may be spent — and the cause as
        `reason`, so the ledger says what was resumed after."""
        session = self.session(ref)
        on = self.machine_of(session)
        record = self.store.session_slot(session.session_id)
        card = card or (record.card if record else session.name)
        if not self.is_here(on):
            return self._moved_elsewhere(
                on,
                session,
                card,
                reason,
                self._remote(on).resume,
                prompt=prompt,
                card=card,
                to_slot=placement.slot if placement is not None else None,
                reason=reason,
            )
        return self._stamped(
            on,
            launch.move(
                self.store,
                session,
                to=placement,
                card=card,
                prompt=prompt,
                spent=False,
                reason=reason,
            ),
            card,
        )

    def expire_handoff(self, handoff: Handoff, *, machine_name: str = "") -> None:
        """Remove a handoff nothing will act on (plan 68, item 3): one naming
        a lane whose work is finished, or a session that is gone. On the
        machine that wrote it: a handoff is that machine's file."""
        on = self.machine_named(machine_name)
        if self.is_here(on):
            handoffs.remove(handoff)
            return
        with contextlib.suppress(*_UNREACHABLE):
            self._remote(on).expire_handoff(handoff.session_id)

    def boots(self, machine_name: str = "") -> list[Boot]:
        """The machine's boots, newest first; none when another machine
        could not be asked, which names no death a boot."""
        on = self.machine_named(machine_name)
        if self.is_here(on):
            return reasons.boots()
        try:
            return self._remote(on).boots()
        except _UNREACHABLE:
            return []

    def limits(self, slot: str, *, machine_name: str = "") -> Limits | None:
        """A slot's last limits reading on the machine the session runs on:
        each machine holds its own login for the same subscription, and its
        own `claude-acct` cache of what that login last saw."""
        on = self.machine_named(machine_name)
        if self.is_here(on):
            return limits.snapshot(slot)
        try:
            return self._remote(on).limits(slot)
        except _UNREACHABLE:
            return None

    def last_activity(self, session: Session) -> datetime | None:
        return transcripts.last_activity(session.worktree or session.cwd, session.session_id)

    def cause_of(
        self,
        session: Session,
        *,
        units: list[str],
        sighting: Sighting | None,
        boots_seen: list[Boot],
        now: datetime,
    ) -> Named:
        """What took the session's process, from the evidence that held it
        (plan 68, item 1): the journal, the boots and the transcript of the
        machine it ran on, read there."""
        on = self.machine_of(session)
        if not self.is_here(on):
            try:
                return self._remote(on).cause_of(session.short_id, units=units, sighting=sighting)
            except _UNREACHABLE as error:
                return Named(
                    cause=Cause.UNKNOWN,
                    words=f"{on.name} could not be asked what ended it",
                    evidence=str(error),
                    last_alive_at=sighting.last_seen if sighting is not None else None,
                    settled=False,
                )
        return reasons.cause_of(
            session,
            units=units,
            sighting=sighting,
            boots_seen=boots_seen,
            last_activity=self.last_activity(session),
            now=now,
        )

    def call(
        self, session: Session | tuple[str, str], *, brief: str, name: str, answer: str
    ) -> Launch:
        """Call a colleague warm (plan 17, item 1): resume its session with
        the brief through the one launch path, or from its transcript when
        no registry holds it. The verb owns nothing of the session's life
        after this (ruling 5). `answer` is where the reply lands: a Claude
        colleague writes it as the brief says, a Codex worker's last
        message is written there by Codex itself (plan 57, item 2)."""
        if isinstance(session, tuple):
            session_id, cwd = session
            return launch.resume_transcript(self.store, session_id, cwd, brief=brief, name=name)
        on = self.machine_of(session)
        if not self.is_here(on):
            # The note and the answer are files on this machine; a colleague
            # there cannot read the one or write the other yet, and calling
            # it through this machine's launcher would act on this machine's
            # processes and registries (Codex's reading of card #83's second
            # pass). Refused by name until the call travels (item 4's live
            # read names it).
            return launch.dead(
                session.name,
                [],
                f"{session.short_id} runs on {on.name}; a colleague on another machine cannot "
                "be called from here yet",
                None,
            )
        return launch.call(self.store, session, brief=brief, name=name, answer=answer)

    def ask(
        self,
        *,
        cwd: str,
        name: str,
        brief: str,
        answer: str,
        schema: str,
        effort: Gate,
    ) -> Launch:
        """Ask a colleague of the other make in a fresh thread (card #87):
        a cold reading held to `schema`, whose last message Codex writes to
        `answer`. Never a resume — the reading's worth is its independence."""
        return launch.ask_codex(
            self.store,
            cwd=cwd,
            name=name,
            brief=brief,
            answer=answer,
            schema=schema,
            effort=effort,
        )

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
        where = self.where(None, [], cached=False, repo=repo)
        if where.placement is None:
            raise windows.WindowRefused(f"the rule found nowhere to run: {where.reason}")
        session_id = session_id or str(uuid.uuid4())
        banner, command = windows.discuss_command(
            where.placement, cwd=repo, session_id=session_id, brief=brief, effort=effort, what=what
        )
        # The conversation runs where the rule placed it; the window is the
        # desktop's, attached over the tunnel when those differ (card #83).
        on = self.machine_named(where.placement.machine)
        proof: str | None = None
        if on.machine_id != self.desktop().machine_id:
            name = windows.tmux_name(kind, card, session_id[:8])
            command = windows.via_tmux(on, name, command, reattach=False)
            proof = f"{on.host}\t{name}"
        opened = windows.open_fresh(
            self.store,
            session_id=session_id,
            kind=kind,
            card=card,
            command=command,
            banner=banner,
            fresh=True,
            host=self.desktop_host(),
            proof=proof,
        )
        return opened, session_id, where.placement

    def open_windows(self) -> list[Window]:
        return self.store.windows(open_only=True)

    def clear_rescues(self, ref: str) -> int:
        return self.store.clear_rescues(self.session(ref).session_id)

    # ── git, signals, reasons ──────────────────────────────────────────

    def worktrees(self, repo: str) -> dict[str, str | None]:
        """Every checkout of the repository on every machine, path → branch
        (card #83): the lanes live beside each machine's clone, laid out the
        same, and the board remembers which machine each was seen on so its
        edits, its tip and its documents are read there. A machine that
        does not answer keeps the paths it was last seen with."""
        # The board's own record of where each lane was last seen seeds the
        # routing, so a restart while a machine is unreachable still reads
        # its lanes as that machine's (Codex's third pass).
        for path, name in self.store.lane_paths_by_machine().items():
            self._lane_machines.setdefault(path, name)
        found = dict(git.worktrees(repo))
        here = self.here().name
        for path in found:
            self._lane_machines[path] = here
        for m in self.machines():
            if self.is_here(m):
                continue
            try:
                theirs = self._remote(m).worktrees(repo)
            except _UNREACHABLE as error:
                log.warning("the checkouts on %s could not be read: %s", m.name, error)
                self.unread.setdefault(m.name, str(error))
                theirs = {
                    path: None
                    for path, name in self._lane_machines.items()
                    if name == m.name and path not in found
                }
            for path, branch in theirs.items():
                if path in found and self._lane_machines.get(path) == here:
                    # The main checkout is on both; a lane is on one.
                    continue
                found[path] = branch
                self._lane_machines[path] = m.name
        return found

    def branch_tip(self, repo: str, branch: str, *, path: str | None = None) -> str | None:
        """The branch's tip on the machine that holds the worktree named by
        `path`, else here."""
        on = self.lane_machine(path) if path else self.here()
        if self.is_here(on):
            return git.head_of(repo, branch)
        try:
            return self._remote(on).tip(repo, branch).tip
        except _UNREACHABLE:
            return None

    def lane_tip(self, repo: str, branch: str, *, path: str) -> LaneTip:
        """The tip and the birth of a lane's branch where it lives."""
        on = self.lane_machine(path)
        if self.is_here(on):
            return LaneTip(tip=git.head_of(repo, branch), birth=git.branch_birth(repo, branch))
        try:
            return self._remote(on).tip(repo, branch)
        except _UNREACHABLE:
            return LaneTip(tip=None, birth=None)

    def edits(self, checkout: str) -> set[str]:
        on = self.lane_machine(checkout)
        if self.is_here(on):
            return git.changed_files(checkout)
        try:
            return self._remote(on).edits(checkout)
        except _UNREACHABLE:
            return set()

    def lane_files(self, checkout: str, *, birth: str | None, tip: str | None) -> set[str]:
        """Every file a lane touched from its birth to its tip, plus what its
        worktree still holds uncommitted: what the close reads to tell a code
        lane from a docs-only one (plan 11, item 1). Read after the fold, the
        diff against the trunk is empty, so the lane's own birth is the base."""
        on = self.lane_machine(checkout)
        if self.is_here(on):
            return git.lane_files(checkout, birth=birth, tip=tip)
        try:
            return self._remote(on).edits(checkout, birth=birth, tip=tip or "HEAD")
        except _UNREACHABLE:
            return set()

    def lane_docs(self, checkout: str, candidates: list[str], *, reviews: bool = False) -> LaneDocs:
        """The lane's own copies of its plan (the first of `candidates` that
        exists, relative to the worktree) and, only when asked, every review
        record under its docs/reviews/ — the loop asks for those once every
        item is met (plan 13), never before — read on the machine that
        holds the worktree."""
        on = self.lane_machine(checkout)
        if self.is_here(on):
            return read_lane_docs(checkout, candidates, reviews=reviews)
        try:
            return self._remote(on).lane_docs(checkout, candidates, reviews=reviews)
        except _UNREACHABLE:
            return LaneDocs(plan=None, reviews=[])

    def reverted(self, repo: str, tip: str) -> bool:
        """Whether a commit on the trunk says it reverts the lane's tip."""
        return git.reverted(repo, tip)

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
        """Why a session with no lane — a reading, a called colleague —
        ended, in one line: the same reader a lane's death gets, over the
        space the runtime put it in."""
        on = self.machine_of(session)
        if not self.is_here(on):
            try:
                return self._remote(on).why_ended(session.short_id)
            except _UNREACHABLE as error:
                return f"{on.name} could not be asked what ended it: {error}"
        record = self.store.session_slot(session.session_id)
        scope = record.scope if record else session.scope
        named = reasons.cause_of(
            session,
            units=[scope] if scope else [],
            sighting=self.store.sighting(session.session_id),
            boots_seen=reasons.boots(),
            last_activity=self.last_activity(session),
            now=clock.now(),
        )
        return named.words

    def is_repository(self, path: str) -> bool:
        return (Path(path) / ".git").exists()

    def roles(self) -> list[str] | None:
        """The roles the machine names; None when it has no roles file."""
        return roles.roles()

    def dispatches(self, cwd: str) -> list[Dispatch] | None:
        """What every session that ran in `cwd` handed out, from its
        transcripts on the machine that holds the lane; None when none exists."""
        on = self.lane_machine(cwd)
        if self.is_here(on):
            return transcripts.dispatches(cwd)
        try:
            return self._remote(on).dispatches(cwd)
        except _UNREACHABLE:
            return None

    def transcript_size(self, session: Session) -> int | None:
        """How large the session's transcript is on the machine that holds it."""
        on = self.machine_of(session)
        if self.is_here(on):
            return machine.transcript_size(session.worktree or session.cwd, session.session_id)
        try:
            return self._remote(on).transcript_size(session.short_id)
        except _UNREACHABLE:
            return None

    def meminfo(self) -> Meminfo | None:
        """The machine's memory right now; None when it cannot be read."""
        try:
            return machine.meminfo()
        except (OSError, ValueError):
            return None

    def scope_memory(self, units: list[str]) -> dict[str, int] | None:
        """What each lane's scope holds right now, in bytes, for the scopes
        the manager holds; None when the reading could not be made (plan
        53, item 1)."""
        try:
            return machine.scope_memory(units)
        except (OSError, machine.Timeout, machine.CommandMissing):
            return None

    def hold_scopes_at(self, units: list[str], memory_high: int) -> list[str]:
        """The lane scopes among `units` just given the floor as their high
        mark (card #107); empty when the manager could not be asked."""
        try:
            return machine.hold_scopes_at(units, memory_high)
        except (OSError, machine.Timeout, machine.CommandMissing):
            return []

    def rescope(self, session: Session, card: str) -> Rescoped:
        """Put a session with hands on a lane back in the lane's scope
        (plan 53, item 2); the same act as at Start, recorded the same way,
        on the machine the session runs on."""
        on = self.machine_of(session)
        if self.is_here(on):
            scoped = launch.rescope(self.store, session, card)
            done = Rescoped(
                unit=scoped.unit, asked=scoped.asked, verified=scoped.verified, words=scoped.words
            )
        else:
            try:
                done = self._remote(on).rescope(session.short_id, card)
            except _UNREACHABLE as error:
                return Rescoped(
                    unit=launch.lane_unit(card), asked=False, verified=False, words=str(error)
                )
        if done.asked or done.verified:
            self.store.record_session_slot(
                SessionSlot(
                    session_id=session.session_id,
                    slot=session.slot,
                    card=card,
                    scope=done.unit,
                    recorded_at=clock.now(),
                    machine=on.name,
                )
            )
        return done

    def scopes(self) -> list[ScopeHeld] | None:
        """Every process group of ours the manager holds active — the
        prefix every lane's and reading's session is put under at Start —
        with the pids each holds and their command lines (card #99), on
        every machine whose sessions the last read reached; None when this
        machine's manager could not be asked. A machine whose sessions are
        unread contributes no groups: a group with nobody home is what the
        beat stops, and nobody-home is not known until the sessions are
        (Codex's reading of card #83's second pass)."""
        return self._scopes()

    def _scopes(self) -> list[ScopeHeld] | None:
        """Every process group of ours the manager holds active — the
        prefix every lane's and reading's session is put under at Start —
        with the pids each holds and their command lines (card #99); None
        when the manager could not be asked."""
        here = self.here()
        try:
            held: list[ScopeHeld] = []
            for unit in machine.units_named(launch.SESSION_UNIT_PREFIX):
                pids = machine.unit_pids(unit)
                commands = {pid: machine.cmdline_of(pid) or "" for pid in pids}
                lineage = {pid: machine.ancestors_of(pid) for pid in pids}
                held.append(
                    ScopeHeld(
                        unit=unit,
                        pids=pids,
                        commands=commands,
                        lineage=lineage,
                        machine=here.name,
                    )
                )
        except (OSError, machine.Timeout, machine.CommandMissing):
            return None
        for m in self.machines():
            if self.is_here(m) or m.name in self.unread:
                continue
            try:
                held += [
                    group.model_copy(update={"machine": m.name})
                    for group in self._remote(m).scopes()
                ]
            except _UNREACHABLE as error:
                log.warning("the groups on %s could not be read: %s", m.name, error)
        return held

    def scope_pids(self, unit: str, *, machine_name: str = "") -> list[int] | None:
        """What one group of ours holds right now, whatever its state — a
        group the manager is ending still holds what it is killing (card
        #99); None when the manager could not be asked."""
        on = self.machine_named(machine_name)
        try:
            if self.is_here(on):
                return machine.unit_pids(unit)
            return self._remote(on).scope_pids(unit)
        except (OSError, machine.Timeout, machine.CommandMissing, *_UNREACHABLE):
            return None

    def stop_scope(self, unit: str, *, machine_name: str = "") -> tuple[bool, str]:
        """Ask the manager to end a group of ours and everything in it
        (card #99), without waiting for it: whether it took the job, and its
        words. The group reads empty once it is done."""
        on = self.machine_named(machine_name)
        try:
            if self.is_here(on):
                return machine.stop_unit(unit)
            answer = self._remote(on).stop_scope(unit)
            return answer.taken, answer.words
        except (OSError, machine.Timeout, machine.CommandMissing, *_UNREACHABLE) as error:
            return False, str(error)

    def tell(self, what: Notice, opens: list[str], ledger: Path) -> Told:
        """Tell the owner on his screen (card #41, item 1): a notification
        that stays until he dismisses it, a sound, and a button that runs
        `opens`; how it was answered lands as one line in `ledger`. Never
        raises: what it could not do is in the words. On the desktop when
        the screen is another machine's (card #83): that machine's own
        `needle tell` raises it there and keeps the ledger beside its own
        store."""
        desktop = self.desktop()
        if self.is_here(desktop):
            return notice.tell(what, opens, ledger)
        try:
            return self._remote(desktop).tell(what, opens)
        except _UNREACHABLE as error:
            return Told(raised=False, words=f"could not tell you on {desktop.name}: {error}")

    def show(self, slug: str, number: int) -> str:
        """Put a card in front of him: the board's page navigates to it and
        its window comes forward, or opens (card #41, item 1) — on the
        desktop, through its own `needle show` when that is another machine."""
        desktop = self.desktop()
        if self.is_here(desktop):
            return notice.show(slug, number)
        try:
            return self._remote(desktop).show(slug, number).said
        except _UNREACHABLE as error:
            raise windows.WindowRefused(f"{desktop.name} could not show it: {error}") from error

    def machine_is_reachable(self) -> list[str]:
        """Which of the commands the runtime needs are missing, by name: the
        ones every machine needs, and the screen's when the screen is here."""
        wanted = COMMANDS + (DESKTOP_COMMANDS if self.is_here(self.desktop()) else ())
        missing: list[str] = []
        for name in wanted:
            try:
                machine.which(name)
            except machine.CommandMissing:
                missing.append(name)
        return missing


def read_lane_docs(checkout: str, candidates: list[str], *, reviews: bool = False) -> LaneDocs:
    """A lane's plan and, when asked, its review records from its worktree
    on this machine (plan 13's reads, moved here from the loop so the same
    read answers over the wire, card #83)."""
    root = Path(checkout)
    plan: str | None = None
    for candidate in candidates:
        try:
            plan = (root / candidate).read_text(encoding="utf-8", errors="replace")
            break
        except OSError:
            continue
    found: list[ReviewText] = []
    for path in sorted((root / "docs" / "reviews").glob("*.md")) if reviews else []:
        if path.name == "README.md":
            continue
        try:
            found.append(
                ReviewText(
                    path=str(path.relative_to(root)),
                    text=path.read_text(encoding="utf-8", errors="replace"),
                )
            )
        except OSError:
            continue
    return LaneDocs(plan=plan, reviews=found)
