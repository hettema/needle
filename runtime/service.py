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
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from domain.call import Call, CallVerdict
from domain.dial import (
    MEMORY_FLOOR_BYTES,
    Headroom,
    Meminfo,
    ScopeHeld,
    ScopeMemory,
    headroom,
    lane_mark,
)
from domain.ending import Boot, Cause, Named, Sighting
from domain.gate import Gate
from domain.handout import Dispatch
from domain.lane import LaneDocs, LaneTip, ReviewText
from domain.launch import Launch, LaunchVerdict, Rescoped, Rescue, Start, Stopped, WindowlessStart
from domain.machine import (
    Ask,
    LaneAsk,
    LaneSeen,
    Machine,
    MachineRoom,
    Observation,
    Observed,
    Timing,
    choose_machine,
)
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
from runtime.remote import Remote, RemoteBehind, RemoteRefused, RemoteTimeout

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
STALE_QUEUE_SECONDS = 3600
"""An event the sessions' hook still queues after this long is one the board
never answered (card #124): counted on the machine's line of the head."""

_EPOCH = datetime.min.replace(tzinfo=UTC)
_UNREACHABLE = (machine.Unreachable, RemoteRefused)
LANE_READERS = 8
"""How many lanes one observation reads at once: a lane's tip, edits and
documents are three git reads and a file, and a hundred lanes read one after
another are ten seconds on the laptop (card #123)."""


class Answer(NamedTuple):
    """One machine's reply to one question, before the board accepts it:
    the observation, or the transport's words when there is none, and when
    the question went out — so an answer to an older question never
    replaces the answer to a newer one."""

    machine: Machine
    observation: Observation | None
    behind: bool
    error: str | None
    asked_at: datetime
    seconds: float


def _unlevelled(note: str) -> git.Levelled:
    """A clone that could not be levelled, with the words why."""
    return git.Levelled(level=None, behind=0, note=note, fetched=False, main_updated=False)


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
        self.observed: dict[str, Observed] = {}
        """What the board holds of every machine, this one included, by
        name (card #123): the newest observation each answered, kept
        between passes. Every read below answers from it when one stands,
        so under the lock nothing waits on a wire or a walk; a runtime in
        its own process (a terminal verb) holds none and reads as before."""
        self._asking: dict[str, Future[Answer]] = {}
        """The question out to each machine, by name, until the board
        accepts its answer: a machine is never asked twice at once, so a
        slow one costs one thread and one ssh, however many passes wait."""
        self._asking_lock = threading.Lock()
        self._acted: dict[str, list[tuple[datetime, Session]]] = {}
        """Each session an act changed on a machine since its observation
        was asked, as the act left it, by machine: a launch's new session,
        and a stopped or moved session with no process. A door's re-read
        sees the act at once, and an observation asked before the act does
        not undo it when it is accepted after (the plan's second ruling:
        the newest reading stands, and an act is newer than a question
        asked before it)."""

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
        rows, with this machine named from its hostname when no row is it.
        On a machine that is not the board's (`needle board NAME` written)
        the rows are the ledger's history and this runtime answers for this
        machine alone: the board asks it `sessions`, and a runtime that
        fanned out over its rows would ask the board's machine, which would
        ask back (Codex's eighth pass on card #83, the copied store's
        topology)."""
        own = machine.machine_id()
        rows = self.store.machines()
        if machine.board_elsewhere() is not None:
            # Its own row stays, by the name the board's records use for it
            # — a lane recorded as the laptop's must still route here — and
            # every other row goes (Codex's ninth pass on card #83).
            rows = [m for m in rows if m.machine_id == own]
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
        """The machine a worktree was last seen on, by its path: the pass's
        read, else the board's own record of where it was last seen — a
        verb in its own process has read no lane yet, and a fold asked
        through the board must push where the lane is (Codex's eighth pass
        on card #83; the same seed as #110's close) — else this one."""
        if path not in self._lane_machines:
            for known, name in self.store.lane_paths_by_machine().items():
                self._lane_machines.setdefault(known, name)
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
            self._put_acted(m, session)
        return launch_.model_copy(update={"placement": placement, "session": session})

    def _replaced(self, old: Session, m: Machine, launch_: Launch, card: str) -> Launch:
        """A move or resume on this machine, as the board records it: the
        launch stamped, and the session it replaced put into the standing
        observation with no process, so a door's apply says the old one
        ended without reading the machine again (card #123)."""
        stamped = self._stamped(m, launch_, card)
        if stamped.session is not None and stamped.session.session_id != old.session_id:
            self._put_acted(m, old.model_copy(update={"pid": None}))
        return stamped

    def _put_acted(self, m: Machine, session: Session) -> None:
        """A session as an act just left it on a machine — launched, or
        stopped with no process — read into the standing observation (card
        #123): the door's re-read sees it without a wire, and the machine's
        next answer to a question asked after the act replaces it."""
        self._acted.setdefault(m.name, []).append((clock.now(), session))
        seen = self.observed.get(m.name)
        if seen is not None and seen.observation is not None:
            seen.observation = self._laid_by_acts(m, seen.observation, [session])

    def _laid_by_acts(
        self, m: Machine, observation: Observation, acted: list[Session]
    ) -> Observation:
        """The observation with every act newer than it written in: each
        acted session's row in place of the one read, and the worktree a
        launch laid among the checkouts until the machine lists it — a lane
        whose worktree the answer predates reads as gone, and a gone lane
        moves its card (card #123). The branch is the machine's to say on
        its next answer."""
        replaced = {a.session_id for a in acted}
        rows = [r for r in observation.sessions if r.session_id not in replaced] + acted
        checkouts = {repo: dict(paths) for repo, paths in observation.checkouts.items()}
        for session in acted:
            if not session.worktree or session.pid is None:
                continue
            repo = next(
                (r for r in checkouts if session.worktree.startswith(r.rstrip("/") + "/")), None
            )
            if repo is not None:
                checkouts[repo].setdefault(session.worktree, None)
                self._lane_machines[session.worktree] = m.name
        return observation.model_copy(update={"sessions": rows, "checkouts": checkouts})

    def room(
        self,
        *,
        hold: bool = False,
        owners: dict[str, tuple[str, int]] | None = None,
        read: set[str] | None = None,
    ) -> Headroom:
        """This machine against the floor: its memory, and what every group
        of ours holds, read by the one rule the head uses. With `hold`,
        every group that stands without this machine's mark as its high
        mark is given it first (card #107; the mark is `lane_mark`'s — the
        floor on the desktop, what the machine has above it on the
        horsepower, since the desktop's 5 GB slowed Hello Revenue #503 for
        two hours on a machine with 24 GB free, 2026-09-10), and the
        reading says which. `owners` names
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
        info = self.meminfo()
        mark = lane_mark(self.here().desktop, info.total if info is not None else 0)
        marked = self.hold_scopes_at(sorted(units), mark) if hold and units else []
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
        now = clock.now()
        # The hook's queue in this machine's data folder (card #124): an event
        # still there after an hour is one the board never answered, and a
        # queue that could not be read is said as not read, never as zero.
        moments = machine.hook_queue_moments()
        stale = (
            None
            if moments is None
            else sum(1 for at in moments if now.timestamp() - at > STALE_QUEUE_SECONDS)
        )
        return headroom(
            info,
            MEMORY_FLOOR_BYTES,
            now,
            scopes=scopes,
            marked=marked,
            mark=mark,
            stale_queue=stale,
        )

    # ── the one question a pass (card #123) ────────────────────────────

    def observe_here(self, ask: Ask) -> Observation:
        """Everything the board asks this machine on one pass, read here and
        answered once (card #123, item 1): what `needle observe` prints for
        another board, and what the board's own pass reads of its own
        machine — one function, whichever side of the wire it runs on."""
        began = clock.now()
        clock_started = time.monotonic()
        here = self.here()
        walls = handoffs.read_handoffs().by_session
        rows = [
            r.model_copy(update={"machine": here.name, "intent": ""})
            for r in [
                *registry.sessions(slots.registries(), walls),
                *codex.sessions(began),
            ]
        ]
        try:
            boots = reasons.boots()
        except (OSError, machine.Timeout, machine.CommandMissing):
            boots = []
        room = self.room(hold=ask.hold, owners=ask.owners or None, read=set(ask.read) or None)
        checkouts = {repo: git.worktrees(repo) for repo in ask.repos}
        with ThreadPoolExecutor(max_workers=LANE_READERS) as readers:
            lanes = list(readers.map(self._lane_seen, ask.lanes))
        held: list[str] | None = None
        if here.desktop:
            with contextlib.suppress(windows.WindowRefused):
                held = windows.addresses(None)
        return Observation(
            at=began,
            seconds=time.monotonic() - clock_started,
            sessions=rows,
            boots=boots,
            room=room,
            scopes=self._scopes_here(),
            placement=rule.where(None, [], cached=True),
            limits={s.name: limits.snapshot(s.name) for s in slots.registries()},
            checkouts=checkouts,
            lanes=lanes,
            windows=held,
        )

    @staticmethod
    def _lane_seen(ask: LaneAsk) -> LaneSeen:
        return LaneSeen(
            checkout=ask.checkout,
            tip=LaneTip(
                tip=git.head_of(ask.repo, ask.branch) if ask.branch else None,
                birth=git.branch_birth(ask.repo, ask.branch) if ask.branch else None,
            ),
            edits=sorted(git.changed_files(ask.checkout)),
            docs=read_lane_docs(ask.checkout, ask.plans, reviews=ask.reviews),
            plans=ask.plans,
            reviews=ask.reviews,
        )

    def observe(self, m: Machine, ask: Ask) -> tuple[Observation, bool]:
        """One machine's answer to the one question: read here for this
        machine, over the wire for another; a machine whose `needle` is
        older than the verb is read the old way, one verb at a time, and
        the second value says so."""
        if self.is_here(m):
            return self.observe_here(ask), False
        r = self._remote(m)
        try:
            return r.observe(ask), False
        except RemoteBehind as behind:
            log.warning("%s is read the old way: %s", m.name, behind)
        return self._observe_old_way(r, ask), True

    @staticmethod
    def _observe_old_way(r: Remote, ask: Ask) -> Observation:
        """The observation composed from the per-verb reads that were the
        pass before this card: what a machine whose `needle` predates the
        verb still answers. The first read that fails fails the whole."""
        began = clock.now()
        clock_started = time.monotonic()
        rows = r.sessions()
        try:
            boots = r.boots()
        except _UNREACHABLE:
            boots = []
        room = r.room(hold=ask.hold, owners=ask.owners or None)
        try:
            scopes: list[ScopeHeld] | None = r.scopes()
        except _UNREACHABLE:
            scopes = None
        placement = r.where(None, [], cached=True)
        checkouts = {repo: r.worktrees(repo) for repo in ask.repos}
        lanes = [
            LaneSeen(
                checkout=a.checkout,
                tip=r.tip(a.repo, a.branch) if a.branch else LaneTip(tip=None, birth=None),
                edits=sorted(r.edits(a.checkout)),
                docs=r.lane_docs(a.checkout, a.plans, reviews=a.reviews),
                plans=a.plans,
                reviews=a.reviews,
            )
            for a in ask.lanes
        ]
        return Observation(
            at=began,
            seconds=time.monotonic() - clock_started,
            sessions=rows,
            boots=boots,
            room=room,
            scopes=scopes,
            placement=placement,
            checkouts=checkouts,
            lanes=lanes,
            windows=None,
        )

    def _answer(self, m: Machine, ask: Ask) -> Answer:
        """Ask one machine and wait for its reply, never raising for a
        machine that does not answer: the reply says why."""
        asked_at = clock.now()
        started = time.monotonic()
        try:
            observation, behind = self.observe(m, ask)
        except (*_UNREACHABLE, machine.Timeout, OSError) as error:
            return Answer(m, None, False, str(error), asked_at, time.monotonic() - started)
        return Answer(m, observation, behind, None, asked_at, time.monotonic() - started)

    def ask_machines(
        self, asks: dict[str, Ask], *, only: set[str] | None = None
    ) -> dict[str, Future[Answer]]:
        """Every machine asked its one question, each on a thread of its own
        so one never waits on another (card #123, item 2). A machine whose
        question is still out, or whose answer the board has not accepted
        yet, is not asked again: the answer that comes is the pass's. The
        threads are daemons, so a machine stalled at shutdown never holds
        the server's exit. Answers the question out to each machine."""
        machines = [m for m in self.machines() if only is None or m.name in only]
        out: dict[str, Future[Answer]] = {}
        with self._asking_lock:
            for m in machines:
                pending = self._asking.get(m.name)
                if pending is None:
                    pending = Future()
                    pending.set_running_or_notify_cancel()
                    threading.Thread(
                        target=self._answer_into,
                        args=(pending, m, asks.get(m.name, Ask())),
                        name=f"needle-ask-{m.name}",
                        daemon=True,
                    ).start()
                    self._asking[m.name] = pending
                out[m.name] = pending
        return out

    def _answer_into(self, future: Future[Answer], m: Machine, ask: Ask) -> None:
        try:
            future.set_result(self._answer(m, ask))
        except BaseException as error:  # noqa: BLE001 — a fault is an answer, never a dead thread
            future.set_exception(error)

    def accept_ready(self) -> dict[str, float]:
        """Every answer that has arrived becomes what the board holds of its
        machine; answers how long each accepted one took. Called under the
        loop's lock, so acceptance never races a pass that reads."""
        with self._asking_lock:
            ready = {name: f for name, f in self._asking.items() if f.done()}
            for name in ready:
                del self._asking[name]
        seconds: dict[str, float] = {}
        for name, future in ready.items():
            error = future.exception()
            if error is not None:
                log.warning("asking %s failed (%s: %s)", name, type(error).__name__, error)
                answer = Answer(self.machine_named(name), None, False, str(error), clock.now(), 0.0)
            else:
                answer = future.result()
            if self._accept(answer):
                seconds[name] = answer.seconds
        return seconds

    def collect(self, asks: dict[str, Ask], *, only: set[str] | None = None) -> dict[str, float]:
        """Every machine named asked now and waited for, in the caller's
        thread: a door's re-read of its own machine after its act, and a
        terminal verb's pass, which has no loop to hand answers to. Answers
        how long each accepted answer took."""
        machines = [m for m in self.machines() if only is None or m.name in only]
        if not machines:
            return {}
        with ThreadPoolExecutor(max_workers=len(machines)) as askers:
            answers = list(askers.map(lambda m: self._answer(m, asks.get(m.name, Ask())), machines))
        return {a.machine.name: a.seconds for a in answers if self._accept(a)}

    def _accept(self, answer: Answer) -> bool:
        """One machine's answer becomes what the board holds of it: the
        sessions stamped with its name, a launch newer than the question
        kept beside them, the lanes' machines remembered, and unread set or
        cleared by whether the machine answered. A machine that did not
        answer keeps its last observation, marked not fresh with the
        transport's words; one that never answered holds None and reads as
        unread. An answer to a question older than the one the board holds
        is dropped, and False says so."""
        m = answer.machine
        old = self.observed.get(m.name)
        if old is not None and old.asked_at is not None and answer.asked_at < old.asked_at:
            return False
        if answer.observation is None:
            seen = Observed(
                machine=m.name,
                observation=old.observation if old is not None else None,
                read_at=old.read_at if old is not None else None,
                asked_at=answer.asked_at,
                fresh=False,
                why=answer.error or f"{m.name} did not answer",
                behind=old.behind if old is not None else False,
                seconds=answer.seconds,
            )
        else:
            rows = [r.model_copy(update={"machine": m.name}) for r in answer.observation.sessions]
            kept = [(at, s) for at, s in self._acted.get(m.name, []) if at > answer.asked_at]
            self._acted[m.name] = kept
            observation = self._laid_by_acts(
                m,
                answer.observation.model_copy(update={"sessions": rows}),
                [s for _, s in kept],
            )
            for checkouts in observation.checkouts.values():
                for path in checkouts:
                    if not self.is_here(m) and self._lane_machines.get(path) == self.here().name:
                        continue  # the main checkout is on both; a lane is on one
                    self._lane_machines[path] = m.name
            seen = Observed(
                machine=m.name,
                observation=observation,
                read_at=clock.now(),
                asked_at=answer.asked_at,
                fresh=True,
                why=None,
                behind=answer.behind,
                seconds=answer.seconds,
            )
        self.observed[m.name] = seen
        if seen.fresh:
            self.unread.pop(m.name, None)
        else:
            self.unread[m.name] = seen.why or f"{m.name} did not answer"
        return True

    def _seen(self, m: Machine) -> Observed | None:
        """What the board holds of the machine, when it has asked it."""
        return self.observed.get(m.name)

    def _seen_lane(self, m: Machine, checkout: str) -> LaneSeen | None:
        seen = self._seen(m)
        if seen is None or seen.observation is None:
            return None
        return next((lane for lane in seen.observation.lanes if lane.checkout == checkout), None)

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
        transport's words, never a machine with room — unless an earlier
        observation of it stands (card #123): then its last room, with when
        it was read and why nothing newer came."""
        now = clock.now()
        found: list[MachineRoom] = []
        here = self.here()
        for m in self.machines():
            room: Headroom | None = None
            why: str | None = None
            observed_at: datetime | None = None
            behind = False
            seen = self._seen(m)
            if seen is not None:
                room = seen.observation.room if seen.observation is not None else None
                why = None if seen.fresh else seen.why
                observed_at = seen.read_at
                behind = seen.behind
            elif self.is_here(m):
                room = self.room(hold=hold, owners=owners, read=read)
            else:
                try:
                    room = self._remote(m).room(hold=hold, owners=owners)
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
                    # The board's own checkout is the trunk's state, never a
                    # clone: a row about this machine from before it was the
                    # board's is history (Codex's tenth pass).
                    clones=[] if self.is_here(m) else self.store.clones(m.name),
                    observed_at=observed_at,
                    behind=behind,
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
        seen = self._seen(m)
        if seen is not None and from_slot is None and not tried and cached:
            # The pass's placement read: the machine's rule as it answered
            # the one question (card #123); a walk with a rung tried, or a
            # live ask, is a door's and goes to the machine.
            if seen.observation is None:
                return Where(
                    placement=None, reason=f"{m.name} could not be asked: {seen.why or 'unread'}"
                )
            answer = seen.observation.placement
        elif self.is_here(m):
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
        here = self.here()
        seen_here = self._seen(here)
        if seen_here is not None and seen_here.observation is not None:
            # The board's own machine as the pass observed it (card #123):
            # the registry walk ran outside the lock, and a launch since is
            # in the observation already.
            rows = list(seen_here.observation.sessions)
        else:
            walls = handoffs.read_handoffs().by_session
            rows = registry.sessions(slots.registries(), walls)
            # Codex's sessions are rows of the same list (plan 57, item 3):
            # read from its rollouts, checked in /proc the same way, sorted
            # under the make's name where a Claude row sorts under its slot.
            rows = [
                r.model_copy(update={"machine": here.name})
                for r in [*rows, *codex.sessions(clock.now())]
            ]
        held: list[str] | None = None
        held_at: datetime | None = None
        for m in self.machines():
            if self.is_here(m):
                continue
            seen = self._seen(m)
            if seen is not None:
                # What the board holds of the machine (card #123): its last
                # observation whether or not it answered this pass — unread
                # when it did not, so nothing acts on an ending there.
                if seen.observation is not None:
                    rows += seen.observation.sessions
                    if m.desktop and seen.observation.windows is not None:
                        held = seen.observation.windows
                        held_at = seen.asked_at
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
        if seen_here is not None and seen_here.observation is not None and here.desktop:
            held = seen_here.observation.windows
            held_at = seen_here.asked_at
        if held is not None:
            windows.reconcile_with(self.store, held, asked_at=held_at)
        elif seen_here is None or self.desktop_host() is None:
            # With no compositor to ask, the windows' state stays as last
            # recorded. A board that observes (seen_here stands) never asks
            # a desktop elsewhere on a read: the desktop's observation
            # carries its windows, and none means it did not answer.
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
            return self._moved_elsewhere(
                on, session, card, reason, lambda: self._remote(on).move(session.short_id, to_slot)
            )
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
        return self._replaced(
            session, on, launch.move(self.store, session, to=to, card=card, reason=reason), card
        )

    def _moved_elsewhere(
        self,
        on: Machine,
        session: Session,
        card: str,
        reason: str | None,
        act: Callable[[], Launch],
    ) -> Launch:
        """A move or resume done by another machine's runtime, recorded here
        as the board's own: the launch stamped and its session's row written,
        and the rescue written under the id that lives with the words the
        launch carries — that machine's ledger holds its own copy, and the
        board's rescue history is what the face reads. `act` is the wire
        call with its arguments already bound: forwarding them through this
        helper's own parameters made a resume's `card` and `reason` collide
        with the helper's, and the board's first comeback on the rented
        machine died on the TypeError (Hello Revenue #503, 2026-09-10)."""
        try:
            done = act()
        except _UNREACHABLE as error:
            return launch.dead(session.name, [], f"{on.name} could not move it: {error}", None)
        stamped = self._stamped(on, done, card)
        if stamped.session is not None and stamped.session.session_id != session.session_id:
            # The session moved from has ended there (card #123): the card
            # says so at once, not a pass later.
            self._put_acted(on, session.model_copy(update={"pid": None}))
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
            if stopped.gone:
                self._put_acted(on, session.model_copy(update={"pid": None}))
        else:
            try:
                stopped = self._remote(on).stop(session.short_id, keep_handoff=keep_handoff)
                if stopped.gone:
                    # Proven gone there (card #123): the card says so at
                    # once, not when the machine next answers.
                    self._put_acted(on, session.model_copy(update={"pid": None}))
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
            to_slot = placement.slot if placement is not None else None
            return self._moved_elsewhere(
                on,
                session,
                card,
                reason,
                lambda: self._remote(on).resume(
                    session.short_id, prompt=prompt, card=card, to_slot=to_slot, reason=reason
                ),
            )
        return self._replaced(
            session,
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
        seen = self._seen(on)
        if seen is not None:
            return seen.observation.boots if seen.observation is not None else []
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
        seen = self._seen(on)
        if seen is not None and not seen.behind:
            # As the machine last answered (card #123): a park is checked
            # under the lock, and never over the wire there.
            if seen.observation is None:
                return None
            return seen.observation.limits.get(slot)
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
        if why is not None and why.endswith(Cause.UNKNOWN.value):
            # An ending the runtime could not establish is no reason to
            # stand above the log's own words (pass two's reader asked that
            # an established reason — a signal, a boot — never be replaced
            # by an earlier, recovered tool error; an unestablished one is
            # not a reason).
            why = None
        fork = next(
            (s for s in rows if s.resumed_from == call.session_id and s.pid is not None), None
        )
        moved = None
        if fork is not None:
            history = self.store.rescues(fork.session_id)
            moved = history[-1].reason if history else None
        # A Codex worker's own log sits beside its answer; the last tool
        # error in it is how a turn that ended on one is told from a turn
        # that finished with nothing to say (card #110, item 5).
        error = codex.last_error(codex.log_path(call.answer)) if call.slot == codex.SLOT else None
        return calls.judge(call, rows, why_ended=why, moved_words=moved, tool_error=error)

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
        seen_here = self._seen(self.here())
        if seen_here is not None and seen_here.observation is not None:
            # This machine as the pass observed it (card #123); a project
            # the question did not name yet is read here, cheaply.
            found = dict(seen_here.observation.checkouts.get(repo) or git.worktrees(repo))
        else:
            found = dict(git.worktrees(repo))
        here = self.here().name
        for path in found:
            self._lane_machines[path] = here
        for m in self.machines():
            if self.is_here(m):
                continue
            seen = self._seen(m)
            if seen is not None:
                # The machine's standing observation (card #123): what it
                # answered when it did, and the paths last seen on it when
                # this pass brought nothing new — a project the question did
                # not name is the same, until the next pass asks.
                theirs = (
                    seen.observation.checkouts.get(repo) if seen.observation is not None else None
                )
                if theirs is None:
                    theirs = {
                        path: None
                        for path, name in self._lane_machines.items()
                        if name == m.name and path not in found
                    }
                for path, branch in theirs.items():
                    if path in found and self._lane_machines.get(path) == here:
                        continue
                    found[path] = branch
                    self._lane_machines[path] = m.name
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
        seen = self._seen_lane(on, path) if path else None
        if seen is not None:
            return seen.tip.tip
        if self.is_here(on):
            return git.head_of(repo, branch)
        if self._seen(on) is not None:
            return None  # a lane the question did not name yet: next pass
        try:
            return self._remote(on).tip(repo, branch).tip
        except _UNREACHABLE:
            return None

    def lane_tip(self, repo: str, branch: str, *, path: str) -> LaneTip:
        """The tip and the birth of a lane's branch where it lives."""
        on = self.lane_machine(path)
        seen = self._seen_lane(on, path)
        if seen is not None:
            return seen.tip
        if self.is_here(on):
            return LaneTip(tip=git.head_of(repo, branch), birth=git.branch_birth(repo, branch))
        try:
            return self._remote(on).tip(repo, branch)
        except _UNREACHABLE:
            return LaneTip(tip=None, birth=None)

    def edits(self, checkout: str) -> set[str]:
        on = self.lane_machine(checkout)
        seen = self._seen_lane(on, checkout)
        if seen is not None:
            return set(seen.edits)
        if self.is_here(on):
            return git.changed_files(checkout)
        if self._seen(on) is not None:
            return set()  # a lane the question did not name yet: next pass
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
        seen = self._seen_lane(on, checkout)
        if seen is not None and seen.plans == candidates and (seen.reviews or not reviews):
            # As the question asked it (card #123): the same candidates,
            # and the records only when they were asked for.
            return seen.docs
        if self.is_here(on):
            return read_lane_docs(checkout, candidates, reviews=reviews)
        if self._seen(on) is not None:
            return LaneDocs(plan=None, reviews=[])  # not asked yet: next pass
        try:
            return self._remote(on).lane_docs(checkout, candidates, reviews=reviews)
        except _UNREACHABLE:
            return LaneDocs(plan=None, reviews=[])

    def reverted(self, repo: str, tip: str) -> bool:
        """Whether a commit on the trunk says it reverts the lane's tip."""
        return git.reverted(repo, tip)

    def fixes_after(self, repo: str, tip: str, number: int) -> int:
        """Trunk commits naming the card within a week of the lane's tip
        (card #58, item 2)."""
        return git.fixes_after(repo, tip, number)

    def lane_folded(
        self, repo: str, branch: str | None, tip: str | None, birth: str | None
    ) -> bool | None:
        return git.lane_folded(repo, branch, tip, birth)

    def in_stable(self, repo: str, tip: str) -> bool:
        """Whether a commit is in origin/main, as last fetched."""
        return git.is_ancestor(repo, tip, f"{git.REMOTE}/{git.STABLE}") is True

    def level(self, repo: str) -> git.Levelled:
        return git.level(repo)

    def level_elsewhere(self, repo: str) -> list[tuple[Machine, git.Levelled]]:
        """The project's clone brought level with the trunk on every other
        machine (card #83, item 3): each machine's clone is what its
        `needle` reads and its lanes are born from — a fold that changed the
        wire was not live on the rented machine until its clone was pulled
        by hand (2026-09-10). The board's own checkout is `level`, kept
        apart because the loop levels it under its lock and the others
        outside it. A machine that did not answer this pass's reads is not
        asked (its wait was paid once); one that fails is a note under its
        name, never a stop for the rest."""
        found: list[tuple[Machine, git.Levelled]] = []
        for m in self.machines():
            if self.is_here(m):
                continue
            # One read of the shared dict: the locked session read rewrites
            # it while this runs outside the lock (Codex's ninth pass).
            unread = self.unread.get(m.name)
            if unread is not None:
                found.append((m, _unlevelled(f"not levelled: {unread}")))
                continue
            try:
                found.append((m, self._remote(m).level(repo)))
            except _UNREACHABLE as error:
                found.append((m, _unlevelled(str(error))))
        return found

    def fold(self, worktree: str, *, promote_main: bool) -> git.Folded:
        """The lane's branch pushed to the trunk from the machine that holds
        the lane: a fold asked of the board runs its git where the worktree
        is (card #83, item 3). A reply that never came is not a push that
        never happened — the machine may have pushed and lost the line — so
        the words say so and the loop's next read of the lane's tip against
        the trunk settles it, as it settles every fold."""
        on = self.lane_machine(worktree)
        if not self.is_here(on):
            try:
                return self._remote(on).push(worktree, promote_main=promote_main)
            except _UNREACHABLE as error:
                return git.Folded(
                    pushed=False,
                    words=(
                        f"{on.name} holds the lane and did not answer the push ({error}); "
                        "whether it pushed is unknown until the board reads the lane's tip "
                        "against origin/develop"
                    ),
                    tip=None,
                    main_pushed=None,
                )
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

    def tokens(self, cwd: str) -> int | None:
        """What every session that ran in `cwd` cost in tokens, counted
        once by request, from the transcripts on the machine that holds the
        lane (card #58); None when none exists or the machine is silent."""
        on = self.lane_machine(cwd)
        if self.is_here(on):
            return transcripts.tokens(cwd)
        try:
            return self._remote(on).tokens(cwd)
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
        """The lane scopes among `units` just given this machine's mark as
        their high mark (card #107); empty when the manager could not be
        asked."""
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
        if done.verified:
            # Verified in /proc there (card #123): the card reads the group
            # it is in now, not when the machine next answers.
            self._put_acted(on, session.model_copy(update={"scope": done.unit}))
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

    def _scopes_here(self) -> list[ScopeHeld] | None:
        """This machine's groups alone; None when the manager could not be
        asked."""
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
        return held

    def _scopes(self) -> list[ScopeHeld] | None:
        """Every process group of ours the manager holds active — the
        prefix every lane's and reading's session is put under at Start —
        with the pids each holds and their command lines (card #99); None
        when the manager could not be asked."""
        here = self.here()
        seen_here = self._seen(here)
        if seen_here is not None and seen_here.observation is not None:
            held = seen_here.observation.scopes
            if held is None:
                return None
            held = list(held)
        else:
            held_here = self._scopes_here()
            if held_here is None:
                return None
            held = held_here
        for m in self.machines():
            if self.is_here(m) or m.name in self.unread:
                continue
            seen = self._seen(m)
            if seen is not None:
                # A group of a machine read this pass, from its observation
                # (card #123); an unread machine was skipped above.
                if seen.observation is not None and seen.observation.scopes is not None:
                    held += [
                        group.model_copy(update={"machine": m.name})
                        for group in seen.observation.scopes
                    ]
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
