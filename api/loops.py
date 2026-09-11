"""The loops: the board reading what runs and moving cards on what it reads.

Three loops, one lock, no polling of any session. The lane loop reads the
runtime's one list, the hook events and git, derives every lane and every
card's doors, acts on the wall detector's handoffs, and makes the machine
moves (into Executing on hands, out of it to where the work says). The
signal loop reads each Executed card's signal on the cadence its WATCH row
states — itself for a URL, a file or a command, and through a reading
session it starts in the project's checkout for a `session` signal (plan
09), whose finding comes back through `needle reading`. The trunk loop
keeps every project's main checkout level with origin/develop. Each loop
runs on a floor timer and the lane loop also runs the moment a hook posts
or a registry file moves, so a session's push is on the board within a
second and a quiet machine costs nothing.

This module is the one place the board and the runtime meet: `api/` may
import both, and nothing below it may.
"""

import asyncio
import contextlib
import logging
import shlex
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from watchfiles import awatch

from board.assemble import (
    WAITING_ON_YOU,
    asked_evidence,
    document_of,
    is_trigger_card,
    lane_is_spent,
    routing_for,
    signal_asks_owner,
    signal_wants_reading,
    trigger_asks_owner,
    trigger_signal,
    trigger_wants_reading,
    watch_signal,
)
from board.brief import (
    PLANNING_PREFIX,
    READING_PREFIX,
    needle_command,
    reading_brief,
    reading_name,
)
from board.collision import footprint, verdict
from board.dial import who_is_home
from board.lane import (
    HANDS_ON,
    HOOK_SLACK_SECONDS,
    STARTABLE_COLUMNS,
    LaneFacts,
    after_archive,
    card_of_cwd,
    close_is_current,
    close_landed,
    conversations_alive,
    disposition,
    doors_for,
    entered_executing_at,
    exit_for,
    first_line,
    lane_for,
    last_line,
    should_enter_executing,
    unpark,
    with_footprints,
)
from board.progress import progress_of
from board.sequencing import waits_for
from board.signals import where_after
from board.title import title_hold
from board.triage import already_ruled
from board.word import compose, notes_word
from domain.audit import AuditEntry, AuditKind
from domain.board import MachineState, TrunkState
from domain.call import Call, CallOutcome
from domain.card import Actor, Card, Place
from domain.column import Column
from domain.dial import MEMORY_FLOOR_BYTES, Headroom, ScopeState, headroom
from domain.document import DocumentKind
from domain.ending import (
    MACHINE_ENDED,
    Boot,
    Cause,
    Death,
    Disposition,
    Park,
    Recovery,
    Sighting,
)
from domain.evidence import Evidence
from domain.gate import Gate
from domain.hook import HookEvent, HookKind, HookPosted, Word
from domain.lane import (
    Collision,
    Doors,
    Lane,
    LaneRecord,
    LaneSnapshot,
    LaneState,
    Progress,
    Wait,
)
from domain.launch import LaunchVerdict, WindowlessStart
from domain.machine import MachineRoom
from domain.notice import Moment, Notice
from domain.session import Session, SessionKind, SessionState
from domain.signal import SessionWork, Signal, SignalKind, WindowlessSession
from domain.slot import Handoff, Placement, rung_words
from domain.watercooler import Note
from domain.window import Window, WindowKind
from infrastructure import clock
from infrastructure.live import Live, LiveProject
from infrastructure.store import StoreRefusal
from runtime import codex, discussion, handoffs, launch, limits, machine
from runtime.service import Runtime
from runtime.windows import WindowRefused

log = logging.getLogger("needle")

FLOOR_SECONDS = 30.0
"""The lane loop's floor: a session that dies without a hook (a kill, a
reboot) is on the board within this, whatever else is quiet."""
SIGNAL_SECONDS = 60.0
TRUNK_SECONDS = 300.0
PARTY_HORIZON_SECONDS = 86400.0
"""How long a call keeps a lane party to its note and answer (plan 17)."""
RESCUE_HORIZON_SECONDS = 3600.0
"""One automatic retry per cause: a second interruption of one cause on the
same lane within this window parks the lane, with the reason and the end
of the wait, instead of thrashing. The hour is a chosen retry policy set in
slice 03 (2026-09-04), not evidence that a cause has cleared (plan 68,
ruling 5): an elapsed hour says nothing about whether the machine's memory
came back, so a memory park waits on the floor and a wall park on the
reset, and the hour only bounds how often the board tries. Revisable under
the plan's loop, which counts repeated failures."""
RECOVERY_IN_FLIGHT_SECONDS = 120.0
"""How long an open recovery row is a launch still verifying — `claude --bg`
may take up to a minute, the verify fifteen seconds, a stop eight — before a
server that finds it on restart calls the replacement lost (plan 68, item
2). Inside it the lane is left alone: the replacement is either registered
already, in which case it is found and recorded, or still coming."""
WATCH_DEBOUNCE_MS = 400
READINGS_AT_ONCE = 2
"""Reading sessions alive at once, across every project (plan 09): each is
a whole session on a subscription, and the lanes come first. The rest wait
for the next tick of the signal loop."""
READING_SECONDS = 1800.0
"""A reading session still without a finding past this is stopped and the
card says so: a reading is short by design, and one that asks a question
nobody sees would otherwise run forever."""
READING_STOP_GRACE_SECONDS = 120.0
"""How long a reading session whose finding has landed may keep working
before it is stopped anyway: the verb runs inside its last turn."""
READING_EFFORT = Gate.HIGH
"""Reading evidence is bounded investigation, not open thinking (the Discuss
door's xhigh); the strongest model still does it, by the one rule."""
SWEEP_SECONDS = 30.0
"""How long a group must stand with nobody home — on every read in
between, both guards holding — before the beat asks the manager to end it
(card #99). Reads come as fast as the registry changes, so a count of
reads is no settling time (Codex's reading, 2026-09-09); a Start's
registry row is written in under a second, and thirty seconds is one
floor beat."""


TELL_HORIZON_SECONDS = 3600.0
"""How far back a machine move out of Executing with no `told` row after it
still rings (card #41, item 2). A crash between the move and the ring rings
at the next reconcile; a move older than an hour was on the board through
his next look, and ringing for it now would be 0.1's toast from a poll —
and at the first beat after this shipped every old exit on every board
would have rung at once."""
TOLD_LEDGER = "told.log"
"""Beside the store: one line per popup answered or dismissed, written by
the popup's own shell (card #41, item 4) — the stamp, the project, the
card, and `default` or `dismissed`. The plan's reading pairs it with the
`told` rows to tell a popup dismissed in a minute from one that stood for
hours."""
TELL_GRACE_SECONDS = 60.0
"""How long a running card waits on him before its bell rings (card #41,
item 3): a stop that becomes an exit inside the same minute is one ring,
the exit's."""


def show_command(slug: str, number: int) -> list[str]:
    """What the notification's button runs: `needle show` from the same
    environment the board serves from, so the verb is found where the
    server was."""
    own = Path(sys.executable).parent / "needle"
    head = [str(own)] if own.exists() else shlex.split(needle_command())
    return [*head, "show", slug, str(number)]


class Tended(StrEnum):
    """What tending a windowless session found (plans 09 and 11)."""

    ALIVE = "alive"
    """Still running, or its work already landed and it is being let finish."""
    MOVED = "moved"
    """Hit a limit and was moved; the record follows the new session."""
    TURN_DONE = "turn done"
    """Its turn finished with its process still there; the caller says what
    a finished turn means for its work."""
    ENDED = "ended"
    """Its process is gone, it overran its ceiling and was stopped, or a
    limit could not be moved: the record is ended and the words say why."""


def project_of_cwd(cwd: str, projects: dict[str, LiveProject]) -> LiveProject | None:
    """The registered project whose tree holds the working directory; the
    deepest match wins so a project inside another's tree is its own."""
    best: LiveProject | None = None
    for live in projects.values():
        root = live.project.path.rstrip("/")
        if (cwd == root or cwd.startswith(root + "/")) and (
            best is None or len(root) > len(best.project.path)
        ):
            best = live
    return best


class Loops:
    def __init__(self, live: Live, runtime: Runtime):
        self.live = live
        self.runtime = runtime
        self._lock = asyncio.Lock()
        self._tasks: list[asyncio.Task[None]] = []
        self._stop = asyncio.Event()
        self._nobody_home: dict[tuple[str, str], datetime] = {}
        """Groups found with nobody home and both guards holding, by machine
        and unit, and since when (card #99): the manager is asked to end
        one only after `SWEEP_SECONDS` of such reads, and the clock starts
        again the moment either guard fails. Keyed by the machine too since
        card #83: the same unit name on two machines is two groups."""
        self._ending: dict[tuple[str, str], tuple[ScopeState, datetime]] = {}
        """Groups the manager was asked to end, with what each held and when
        it was asked: the card is told only once the group is empty, and
        the manager is asked again if it is not after another window."""
        self._sweep_said: set[tuple[str, str]] = set()
        """Groups whose refused stop was said on the card, once."""
        self._boots: dict[str, list[Boot]] = {}
        """Each machine's boots as the pass read them, by the board's name
        for the machine (card #83): what a death is dated against. Deaths,
        parks, releases and adoptions live in the store
        (plan 68, item 2), never in a set here: card #196 carried one park
        note seventeen times because each `needle` command and each restart
        of the server began with an empty head."""
        self._notes: list[Note] = []
        """The machine's watercooler as the last read saw it (plan 17)."""
        self._rooms: list[MachineRoom] = []
        """Every machine against the floor as the last read saw it (card
        #83): what places work between passes, and what the head shows."""
        self._parties: dict[tuple[str, int], set[str]] = {}
        """Per lane, the notes its card names: read with the plan's
        footprint, once per beat, so the word never reads a plan."""
        self._pass_asked = False
        self._pass_task: asyncio.Task[None] | None = None
        """The pass a post asks for (card #124): the intake records what was
        posted and answers at once, and the pass runs after the answer as
        this task's work. However many posts arrive while a pass runs, the
        flag is one flag, so one more pass follows it and never one per
        post; a post that arrives while no pass runs starts one. Before,
        the intake awaited the whole pass — 26 s with a hundred lanes and a
        second machine — so no hook heard its answer within the two seconds
        it waits, every firing re-sent a day of events, and the board spent
        the evening answering echoes (2026-09-10)."""
        self._word_lock = asyncio.Lock()
        """The word's own lock (plan 10): a read of a lane's word and the
        move of its heard-mark are one act, so two hooks firing from one
        session's parallel tool calls cannot both carry the same word. Not
        the loops' lock: that one is held through a reconcile's git reads,
        and a word that waited behind it would outlive the hook's half
        second while the server still moved the mark — the word lost."""

    # ── lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._timer(FLOOR_SECONDS, self.reconcile)),
            asyncio.create_task(self._timer(SIGNAL_SECONDS, self.read_signals)),
            asyncio.create_task(self._timer(TRUNK_SECONDS, self.level_trunks)),
            asyncio.create_task(self._watch_registries()),
        ]
        self.live.on_change = self.reconcile

    async def stop(self) -> None:
        self._stop.set()
        pending = [self._pass_task] if self._pass_task is not None else []
        for task in [*self._tasks, *pending]:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def first_read(self) -> None:
        """Every loop once, in order, before the board is served: the lanes,
        the signals, the trunk. The timers then wait their interval first,
        so a caller who saw the server start has seen a complete read."""
        for work in (self.reconcile, self.read_signals, self.level_trunks):
            try:
                await work()
            except Exception as error:  # noqa: BLE001 — a first read never stops the server
                log.warning("the first read failed (%s: %s)", type(error).__name__, error)

    async def _timer(self, seconds: float, work: Callable[[], Awaitable[None]]) -> None:
        while not self._stop.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), seconds)
            if self._stop.is_set():
                return
            try:
                await work()
            except Exception as error:  # noqa: BLE001 — a loop never dies quietly
                log.warning("a loop failed (%s: %s); it runs again", type(error).__name__, error)

    async def _watch_registries(self) -> None:
        """Every registry's `jobs/` and the handoff directory: a state change
        is a file write, and the board hears it instead of asking."""
        roots = [Path(s.config_dir) / "jobs" for s in self.runtime.slots()]
        roots.append(machine.handoff_dir())
        roots.append(machine.discussion_dir())
        existing = [str(p) for p in roots if p.is_dir()]
        if not existing:
            return
        try:
            async for _changes in awatch(
                *existing, stop_event=self._stop, debounce=WATCH_DEBOUNCE_MS
            ):
                await self.reconcile()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001
            log.warning(
                "the board stopped hearing the registries (%s: %s); the floor timer covers it",
                type(error).__name__,
                error,
            )

    # ── the async doors into the loops ─────────────────────────────────

    @property
    def lock(self) -> asyncio.Lock:
        """The one lock every read of the machine and every door takes, so a
        door and a loop never act on the same lane at once."""
        return self._lock

    async def reconcile(self) -> None:
        async with self._lock:
            # A post's ask is met by the first pass that reads the store
            # after it (card #124): cleared here, under the lock, so posts
            # that arrive while a pass waits its turn are read by that pass
            # and not by one more after it — cleared before the wait, three
            # posts during a stall caused two passes.
            self._pass_asked = False
            await asyncio.to_thread(self.reconcile_now)

    async def read_signals(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.read_signals_now)

    async def level_trunks(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.level_trunks_now)
        # The other machines' clones are levelled outside the lock: a
        # stalled machine would otherwise hold every door for the sum of
        # its waits (Codex's eighth pass on card #83, after finding 17).
        await asyncio.to_thread(self.level_clones_now)

    async def hooks(self, posted: list[HookPosted]) -> list[HookEvent]:
        """What a session's hook posted: recorded and answered at once, with
        the pass it causes run after the answer (card #124). The record is
        off the loop's thread and outside the loops' lock, which a pass in
        flight holds for its whole read: the hook's two seconds are the
        bound, and the store's write is milliseconds."""
        recorded = await asyncio.to_thread(self.record_hooks, posted)
        self.ask_for_a_pass()
        return recorded

    def ask_for_a_pass(self) -> None:
        """One more pass after the one in flight, whoever asks and however
        often: the flag is set, and the task that drains it exists once."""
        self._pass_asked = True
        if self._pass_task is None or self._pass_task.done():
            self._pass_task = asyncio.create_task(self._passes_asked_for())

    async def _passes_asked_for(self) -> None:
        while self._pass_asked and not self._stop.is_set():
            try:
                await self.reconcile()
            except Exception as error:  # noqa: BLE001 — a failed pass never ends the asking
                log.warning("the pass a post asked for failed (%s: %s)", type(error).__name__, error)

    async def settled(self) -> None:
        """Every pass posts have asked for has run: what a reader who wants
        the board to show a post waits on, never the post itself."""
        while self._pass_task is not None and not self._pass_task.done():
            await asyncio.shield(self._pass_task)

    async def word(self, cwd: str, wrote: str | None = None) -> Word | None:
        """What the board has not yet told the lane at `cwd` (plan 10, item
        1), and the mark moved so it is told once; None when the directory
        is no lane of a registered project. Reads the loop's last read and
        the store, never git. `wrote` is the file the tool call just wrote,
        when the hook says so: a note the lane wrote on the machine's
        watercooler is stamped as heard, so it never hears its own."""
        project = project_of_cwd(cwd, self.live.projects)
        if project is None:
            return None
        number = card_of_cwd(cwd, project.project.path)
        if number is None:
            return None
        async with self._word_lock:
            return await asyncio.to_thread(self.word_now, project, number, wrote)

    def word_now(self, live: LiveProject, number: int, wrote: str | None = None) -> Word:
        """The word for one lane, and its mark moved. Before the loop's
        first read the board knows no lane's drift and says nothing rather
        than guess. The mark is written by this server's own store, so the
        write stamp counts it as the server's own and the change loop does
        not read the board back to itself (plan 06, item 6)."""
        slug = live.project.slug
        now = clock.now()
        snapshot = live.snapshot
        if snapshot is None or number not in snapshot.lanes:
            return Word(project=slug, card_number=number, sentences=[], read_at=now)
        store = self.live.store
        lane = snapshot.lanes[number]
        record = store.lane(slug, number)
        mark = store.heard_mark(slug, number)
        word, mark = compose(
            slug,
            lane,
            store.watercooler(slug, after=mark.watercooler_id if mark is not None else 0),
            mark,
            since=record.first_seen if record is not None else lane.hands_on_since,
            now=now,
            read_at=snapshot.read_at,
        )
        if mark is not None:
            store.mark_heard(mark)
        party_to = self._party_to(slug, number, lane)
        if party_to:
            stamps = store.heard_notes(slug, number)
            if wrote and discussion.in_directory(wrote):
                own = discussion.note_of(Path(wrote))
                if own is not None:
                    stamps[own.path] = own.at
                    store.stamp_notes(slug, number, {own.path: own.at})
            said, moved = notes_word(self._notes, stamps, party_to=party_to)
            if moved:
                store.stamp_notes(slug, number, moved)
                word = word.model_copy(update={"sentences": [*word.sentences, *said]})
        # Only a word that said something changed what the card shows; a
        # mark that moved silently (the baseline, the lane's own lines
        # going by) would otherwise turn every open page over for a line
        # that reads the same, on every tool call of every lane.
        if word.sentences:
            self.live.bump()
        return word

    def _party_to(self, slug: str, number: int, lane: Lane) -> set[str]:
        """The notes on the machine's watercooler this lane is party to: the
        ones its card names, and the note and answer of every call it made
        or was called with (plan 17, item 2)."""
        named = set(self._parties.get((slug, number), set()))
        session_id = lane.session.session_id if lane.session is not None else None
        # Bounded: this runs on every tool call of every lane, and the calls
        # table only grows. A call older than a day is a thread the lane's
        # card names if it still matters.
        since = clock.now() - timedelta(seconds=PARTY_HORIZON_SECONDS)
        for call in self.live.store.calls(since=since):
            mine = call.caller == lane.path or (
                lane.path is not None and call.caller.startswith(lane.path + "/")
            )
            if mine or (session_id is not None and call.session_id == session_id):
                named.update((call.note, call.answer))
        return named

    def record_hooks(self, posted: list[HookPosted]) -> list[HookEvent]:
        attributed: list[tuple[HookPosted, str | None, int | None]] = []
        for event in posted:
            project = project_of_cwd(event.cwd, self.live.projects)
            slug = project.project.slug if project else None
            number = card_of_cwd(event.cwd, project.project.path) if project else None
            attributed.append((event, slug, number))
        recorded = self.live.store.record_hook_events(attributed)
        if recorded:
            self.live.bump()
        return recorded

    # ── the lane loop ──────────────────────────────────────────────────

    def reconcile_now(self) -> None:
        """One read of the machine, and every move it implies."""
        if not self._rooms:
            self.headroom_now()
        sessions = self.runtime.sessions()
        windows = self.runtime.open_windows()
        self._notes = self.runtime.notes()
        self._boots = {
            reading.machine.name: self.runtime.boots(reading.machine.name)
            for reading in self._rooms
        }
        for live in list(self.live.projects.values()):
            try:
                self._reconcile_project(live, sessions, windows)
            except Exception as error:  # noqa: BLE001 — one project's failure never hides another's
                log.warning(
                    "reconciling %s failed (%s: %s)", live.project.slug, type(error).__name__, error
                )
        self._sweep_scopes()
        self._tend_calls()
        self.headroom_now()

    def headroom_now(self) -> Headroom:
        """The machine against the floor, on every pass and not only at the
        dial's beat (plan 53, item 1): available memory and free swap, and
        beside them what every lane with hands on holds, read from the
        lane's own scope by the name it was given at Start. A lane that
        grows after the beat let it in is seen here before oomd sees it,
        and the head says which lane and how far; the dial's beat and the
        terminal read the machine through this one call."""
        owners = self._busy_owners()
        # Every machine is read on every pass (card #83): the rooms place
        # the next card, the head shows each machine, and the day's
        # high-water mark is kept per machine. Every lane's scope carries
        # the floor as its high mark, whoever made the scope (card #107):
        # set where it is missing on every machine, said once on the card.
        self._rooms = self.runtime.rooms(hold=True, owners=owners, read=set(self._owners()))
        now = clock.now()
        for reading in self._rooms:
            if reading.room is None:
                continue
            for unit in reading.room.marked:
                if unit in owners:
                    slug, number = owners[unit]
                    self.live.note(
                        slug,
                        number,
                        AuditKind.SCOPED,
                        Actor.MACHINE,
                        f"Held {unit} at {reading.room.mark // 1024**3} GB (the high mark for "
                        f"a lane on {reading.machine.name}): the scope stood without it.",
                    )
            if reading.room.total > 0:
                self.live.store.note_high_water(
                    reading.machine.name,
                    available=reading.room.available,
                    total=reading.room.total,
                    at=now,
                )
        self.live.set_machine(
            MachineState(
                missing=self.runtime.machine_is_reachable(),
                roles=self.runtime.roles(),
                machines=self._rooms,
            )
        )
        here = next((r for r in self._rooms if r.here), None)
        room = (
            here.room
            if here is not None and here.room is not None
            else headroom(None, MEMORY_FLOOR_BYTES, now)
        )
        # The head's word is the board's: full only when no machine has
        # room, since that is when the beat takes nothing; the sentence
        # names each full machine so the dial's refusal and its rule agree
        # (Codex's reading of card #83's second pass).
        others = [r for r in self._rooms if not r.here]
        if room.full and any(r.room is not None and not r.room.full for r in others):
            room = room.model_copy(update={"full": False, "sentence": None})
        elif room.full and others:
            said = [room.sentence or "full"] + [
                f"{r.machine.name}: {r.room.sentence if r.room is not None else 'did not answer'}"
                for r in others
            ]
            room = room.model_copy(update={"sentence": "; ".join(said)})
        self.live.set_headroom(room)
        return room

    def _sweep_scopes(self) -> None:
        """A group nobody is home in is ended, and the card says so once it
        is empty (card #99). Every lane's and reading's session runs in a
        group of its own, and the board stops the *session* only when its
        lane folded and closed (`_release_finished`); every other ending
        left the group standing with whatever the session had started — on
        2026-09-09, forty wait loops from three sessions a day gone, each
        spawning a `sleep` every few seconds while the laptop paged, and a
        `uvicorn` a reading had left at 1.9 GB. So the beat reads every
        group of ours and, when one has held processes no live session owns
        — by pid or by ancestry — and whose card has no live session, on
        every read for `SWEEP_SECONDS`, asks the manager to end it, without
        waiting: a stubborn process takes the manager's whole stop timeout,
        and the beat holds the lock every door takes. The card is told when
        the group reads empty, never before; a refusal is said once and
        asked again after another window; a group still not empty after a
        window is asked again. The groups are read before the sessions, so
        a session the registry knew before its group existed is home on the
        first read; an empty group is left (Start's settle window); a
        session whose turn is done but whose process still stands is home,
        and what it left is its own until `_release_finished` ends it."""
        held = self.runtime.scopes()
        if held is None:
            return
        states = who_is_home(held, self.runtime.sessions())
        owners = self._lanes_by_unit()
        now = clock.now()
        for key, (state, asked_at) in list(self._ending.items()):
            machine_name, unit = key
            still = self.runtime.scope_pids(unit, machine_name=machine_name)
            if still is None:
                continue  # the manager could not be asked: nothing is established
            if still:
                if (now - asked_at).total_seconds() >= SWEEP_SECONDS:
                    self.runtime.stop_scope(unit, machine_name=machine_name)
                    self._ending[key] = (state, now)
                continue
            del self._ending[key]
            self._nobody_home.pop(key, None)
            self._sweep_said.discard(key)
            self._say_swept(owners.get(unit), unit, self._what_it_held(state, "Stopped"))
        eligible: dict[tuple[str, str], ScopeState] = {}
        for state in states:
            owner = owners.get(state.unit)
            # The owner is alive only where the group is: a lane's session
            # on the laptop does not keep a like-named group on the rented
            # machine (Codex's reading of card #83's second pass).
            owner_alive = (
                owner is not None
                and owner[2].session is not None
                and bool(owner[2].session.pid)
                and owner[2].session.machine == state.machine
            )
            if state.nobody_home and not owner_alive:
                eligible[(state.machine, state.unit)] = state
        for key in list(self._nobody_home):
            if key not in eligible:
                del self._nobody_home[key]
                self._sweep_said.discard(key)
        for key, state in eligible.items():
            if key in self._ending:
                continue
            machine_name, unit = key
            since = self._nobody_home.setdefault(key, now)
            if (now - since).total_seconds() < SWEEP_SECONDS:
                continue
            taken, words = self.runtime.stop_scope(unit, machine_name=machine_name)
            if taken:
                self._ending[key] = (state, now)
                continue
            self._nobody_home[key] = now
            if key in self._sweep_said:
                continue
            self._sweep_said.add(key)
            self._say_swept(
                owners.get(unit),
                unit,
                self._what_it_held(state, "Asked the machine to end")
                + f"; it refused: {words}. The beat asks again.",
            )

    @staticmethod
    def _what_it_held(state: ScopeState, verb: str) -> str:
        count = len(state.pids)
        heads = ", ".join(sorted(set(state.strangers))[:3])
        return (
            f"{verb} what a finished session left in {state.unit}: {count} "
            f"process{'es' if count != 1 else ''} nobody owned ({heads})"
        )

    def _say_swept(self, owner: tuple[str, int, Lane] | None, unit: str, said: str) -> None:
        if said.startswith("Stopped"):
            said += "; nothing a finished session started keeps running."
        if owner is None:
            log.info("%s (%s names no card on any board)", said, unit)
            return
        self.live.note(owner[0], owner[1], AuditKind.STOPPED, Actor.MACHINE, said)

    def _room_of(self, machine_name: str) -> Headroom:
        """The room of the machine a session runs on, read fresh (card #83):
        a lane comes back where its worktree is, so its admission is that
        machine's floor — a full rented machine is not admitted because the
        laptop has room, nor held because the laptop is full (Codex's
        reading of the second pass)."""
        rooms = self.runtime.rooms(owners=self._busy_owners(), read=set(self._owners()))
        self._rooms = rooms
        wanted = self.runtime.machine_named(machine_name).name
        reading = next((r for r in rooms if r.machine.name == wanted), None)
        if reading is None or reading.room is None:
            return headroom(None, MEMORY_FLOOR_BYTES, clock.now())
        return reading.room

    def _names(self) -> dict[str, tuple[str, int]]:
        """Every unit a card's sessions may run under — its lane's, its
        reading's, its planning's — to the card, so a group the machine
        lists is named by its card on the head, whatever kind it is."""
        return {unit: (slug, number) for unit, (slug, number, _) in self._lanes_by_unit().items()}

    def _busy_owners(self) -> dict[str, tuple[str, int]]:
        """The names handed to every machine's room, on the pass and on a
        parked lane's fresh read alike: the units of the cards with hands
        on, in their three kinds, and not every card the board ever had —
        480 cards' worth was a line of 135 KB, more than one argument may
        carry to `ssh` (E2BIG at 128 KB; the first live move, 2026-09-10).
        The park's read handed every name until 2026-09-10 evening, so a
        lane parked on the rented machine read its room as unreadable for
        twenty-five minutes and never came back. A group with no card among
        these is named by its unit, which is what it is."""
        busy = set(self._owners().values())
        return {unit: card for unit, card in self._names().items() if card in busy}

    def _owners(self) -> dict[str, tuple[str, int]]:
        """Every lane with hands on, by the unit it was given at Start: what
        the room reads by name and holds at the floor (plan 53, card #107)."""
        found: dict[str, tuple[str, int]] = {}
        for slug, live in self.live.projects.items():
            if live.snapshot is None:
                continue
            for number, lane in live.snapshot.lanes.items():
                if lane.state in HANDS_ON:
                    found[launch.lane_unit(lane.name)] = (slug, number)
        return found

    def _repo_of(self, session: Session) -> str | None:
        """The registered project a session works in, by its directory."""
        home = session.worktree or session.cwd
        for live in self.live.projects.values():
            root = live.project.path.rstrip("/")
            if home == root or home.startswith(root + "/"):
                return live.project.path
        return None

    def _lanes_by_unit(self) -> dict[str, tuple[str, int, Lane]]:
        """Every unit a card's sessions run under — its lane's, its
        reading's, its planning's — to the card, from the last snapshot."""
        found: dict[str, tuple[str, int, Lane]] = {}
        for slug, live in self.live.projects.items():
            if live.snapshot is None:
                continue
            for number, lane in live.snapshot.lanes.items():
                for name in (lane.name, READING_PREFIX + lane.name, PLANNING_PREFIX + lane.name):
                    found[launch.lane_unit(name)] = (slug, number, lane)
        return found

    def _tend_calls(self) -> None:
        """Every open call against the one list (plan 17): the record
        follows the fork when the runtime moved the colleague — the
        registry says which session resumed which — and ends with the
        runtime's words when the colleague ends without its note, or when
        the note landed. A wall is moved once, by whoever tends the
        session: a lane's by the lane loop, a reading's by its tending, and
        a colleague that is nobody's by this loop, with the same one hop
        and the same park on a second wall within the hour (ruling 5);
        the record follows the session that lives either way."""
        store = self.live.store
        open_calls = store.calls(open_only=True)
        if not open_calls:
            return
        sessions = self.runtime.sessions()
        now = clock.now()
        tended = self._tended_elsewhere()
        for call in open_calls:
            verdict = self.runtime.judge_call(call, sessions)
            if verdict is None:
                continue
            if verdict.outcome == CallOutcome.MOVED:
                store.move_call(call.id, verdict.session_id, verdict.slot, verdict.words)
                continue
            if verdict.outcome == CallOutcome.BLOCKED:
                session = next((s for s in sessions if s.session_id == call.session_id), None)
                if session is None or session.wall is None or session.session_id in tended:
                    # A question, or a wall that is another loop's to move:
                    # the call stays open and a waiter is told the state.
                    continue
                self._move_called(call, session, now)
                continue
            store.end_call(call.id, now, verdict.words)

    def _tended_elsewhere(self) -> set[str]:
        """The sessions another loop moves on a wall: every lane's, and
        every open windowless session's."""
        held: set[str] = set()
        for live in self.live.projects.values():
            snapshot = live.snapshot
            if snapshot is not None:
                # Any lane with a live session, whatever its state: a wall
                # reads as MOVING, which is exactly the one the lane loop moves.
                held.update(
                    lane.session.session_id
                    for lane in snapshot.lanes.values()
                    if lane.session is not None and lane.session.pid is not None
                )
            for work in SessionWork:
                held.update(
                    r.session_id
                    for r in self.live.store.open_windowless_sessions(
                        live.project.slug, work
                    ).values()
                )
        return held

    def _move_called(self, call: Call, session: Session, now: datetime) -> None:
        """One hop for a called colleague that hit a limit and is nobody
        else's: the lane loop's rule, one automatic retry per run-out."""
        store = self.live.store
        assert session.wall is not None
        recent = [
            r
            for r in store.rescues(session.session_id)
            if (now - r.at).total_seconds() < RESCUE_HORIZON_SECONDS and launch.on_a_wall(r)
        ]
        if recent:
            store.end_call(
                call.id,
                now,
                f"{session.short_id} hit a limit again within the hour ({session.wall.reason}); "
                "one automatic retry per run-out, so this one is the owner's",
            )
            return
        moved = self.runtime.move(session.short_id, None)
        if moved.verdict != LaunchVerdict.ALIVE or moved.session is None:
            store.end_call(
                call.id,
                now,
                f"{session.short_id} hit a limit on {session.slot} ({session.wall.reason}) and "
                f"could not be moved: {moved.reason}",
            )
            return
        placement = moved.placement
        where = rung_words(placement.model, placement.slot) if placement else moved.session.slot
        store.move_call(
            call.id,
            moved.session.session_id,
            moved.session.slot,
            f"{call.name} moved to {where} as {moved.session.short_id}: {session.wall.reason}; "
            "the call follows it",
        )

    def _placement(self, repo: str | None = None) -> tuple[Placement | None, str]:
        """Where a card in `repo` runs next, over the rooms read this pass
        (card #83): the machine first, then that machine's rule. On a
        one-machine board the placement carries no machine name, so the
        Start door reads as it always has."""
        where = self.runtime.where(None, [], cached=True, repo=repo, rooms=self._rooms or None)
        placement = where.placement
        if placement is not None and len(self._rooms) <= 1:
            placement = placement.model_copy(update={"machine": ""})
        return placement, where.reason

    def _reconcile_project(
        self,
        live: LiveProject,
        sessions: list[Session],
        windows: list[Window],
    ) -> None:
        slug, project = live.project.slug, live.project
        store = self.live.store
        now = clock.now()
        placement, placement_note = self._placement(project.path)
        cards = store.cards(slug)
        worktrees = (
            self.runtime.worktrees(project.path) if self.runtime.is_repository(project.path) else {}
        )
        records = self._keep_lane_records(slug, project.path, worktrees, now)
        facts = self._facts(live, sessions, windows, records, worktrees, now)
        lanes = {c.number: lane_for(c, facts) for c in cards}
        self._sightings(slug, lanes, now)
        if self._name_deaths(slug, cards, lanes, now):
            facts = self._facts(live, sessions, windows, records, worktrees, now)
            lanes = {c.number: lane_for(c, facts) for c in cards}
        # A recovery moved or resumed a session, so the lanes read here are
        # stale until the re-read below; the scope check waits for the next
        # pass rather than adopt a pid that is gone (a move scopes its new
        # session).
        if self._recover(live, cards, lanes, records, facts.events) or self._keep_in_scope(
            lanes, slug
        ):
            sessions = self.runtime.sessions()
            windows = self.runtime.open_windows()
            facts = self._facts(live, sessions, windows, records, worktrees, now)
            lanes = {c.number: lane_for(c, facts) for c in cards}
        cards = self._machine_moves(slug, cards, lanes, records)
        self._tell_owner(live, cards, lanes)
        if self._release_finished(slug, cards, lanes, records):
            sessions = self.runtime.sessions()
            windows = self.runtime.open_windows()
            facts = self._facts(live, sessions, windows, records, worktrees, now)
            lanes = {c.number: lane_for(c, facts) for c in cards}
        lanes = with_footprints(lanes, *self._footprints(live, cards, lanes))
        doors = self._doors(live, cards, lanes, placement, placement_note, now)
        conversations = conversations_alive(facts.sessions, facts.discussions)
        self.live.set_snapshot(
            slug,
            LaneSnapshot(lanes=lanes, doors=doors, conversations=conversations, read_at=now),
        )

    def _facts(
        self,
        live: LiveProject,
        sessions: list[Session],
        windows: list[Window],
        records: list[LaneRecord],
        worktrees: dict[str, str | None],
        now: datetime,
    ) -> LaneFacts:
        slug, path = live.project.slug, live.project.path
        here = [
            s for s in sessions if s.cwd.startswith(path) or (s.worktree or "").startswith(path)
        ]
        rescues = {s.session_id: self.live.store.rescues(s.session_id) for s in here}
        store = self.live.store
        return LaneFacts(
            project_path=path,
            sessions=sessions,
            events=store.hook_events(slug),
            discussions=store.discussions(slug),
            records=records,
            windows=windows,
            rescues=rescues,
            deaths=store.deaths(slug),
            parks={p.card_number: p for p in store.parks(slug, standing_only=True)},
            worktrees=worktrees,
            now=now,
            many_machines=len(self._rooms) > 1,
        )

    def _current_boot(self, machine_name: str = "") -> Boot | None:
        """The boot a machine is in now, by the board's name for it; an
        unnamed row's machine is this one (card #83)."""
        if not machine_name:
            machine_name = self.runtime.here().name
        # A named machine with no boots read is unknown, never this
        # machine's boot: a sighting stamped with the wrong boot would name
        # a death "the laptop went down" that was nothing of the kind
        # (Codex's reading of card #83's second pass).
        return next((b for b in self._boots.get(machine_name, []) if b.index == 0), None)

    def _sightings(self, slug: str, lanes: dict[int, Lane], now: datetime) -> None:
        """Every session with a live process in a lane, seen on this pass
        (plan 68, item 1): its process, the space it runs in and the boot
        it runs in, so its death — a row that had a process and now has
        none — is named from what actually held it, and a row not yet born
        is never given an epitaph."""
        deaths = self.live.store.deaths(slug)
        for number, lane in lanes.items():
            session = lane.session
            if session is None or session.pid is None or session.stale:
                continue
            if session.machine in self.runtime.unread:
                # The row stands from the last read that reached the
                # machine; a sighting written from it now would be an
                # observation nobody made (Codex's third pass).
                continue
            boot = self._current_boot(session.machine)
            if session.session_id in deaths:
                self.live.store.forget_death(session.session_id)
            self.live.store.record_sighting(
                Sighting(
                    session_id=session.session_id,
                    project=slug,
                    card_number=number,
                    pid=session.pid,
                    scope=session.scope,
                    boot_id=boot.boot_id if boot is not None else None,
                    first_seen=now,
                    last_seen=now,
                    machine=session.machine,
                )
            )

    def _units_of(self, lane: Lane, session: Session) -> list[str]:
        """The spaces the session may have run in: the lane's own first,
        the account's daemon space after (a session something resumed by
        hand lands there)."""
        return [
            launch.lane_unit(lane.name),
            machine.unit_name(launch.DAEMON_UNIT_PREFIX, session.slot),
        ]

    def _name_deaths(
        self, slug: str, cards: list[Card], lanes: dict[int, Lane], now: datetime
    ) -> bool:
        """Name the death of every ended lane's session at the end, from the
        evidence that held the process (plan 68, item 1), and revise an
        epitaph that was not settled while evidence may still arrive. A
        row with no sighting younger than the verify window is a session
        being born, not one that died (the 127 ms window that wrote `the
        registry says: starting…` on a live lane); a lane whose card closed
        is finished work, and its session's ending is the normal end of
        that work, not a death to name (item 4). Returns whether any death
        was written, so the caller re-reads the lanes."""
        store = self.live.store
        deaths = store.deaths(slug)
        closed = {c.number for c in cards if close_landed(c)}
        changed = False
        for lane in lanes.values():
            session = lane.session
            if lane.state != LaneState.ENDED or session is None or session.pid is not None:
                continue
            if lane.card_number in closed or session.machine in self.runtime.unread:
                continue
            death = deaths.get(session.session_id)
            if death is not None and (
                death.settled
                or (now - (death.last_alive_at or death.named_at)).total_seconds()
                > RESCUE_HORIZON_SECONDS
            ):
                continue
            sighting = store.sighting(session.session_id)
            if (
                sighting is None
                and session.created_at is not None
                and (now - session.created_at).total_seconds() < launch.VERIFY_SECONDS
            ):
                continue
            named = self.runtime.cause_of(
                session,
                units=self._units_of(lane, session),
                sighting=sighting,
                boots_seen=self._boots.get(session.machine)
                or self._boots.get(self.runtime.here().name, []),
                now=now,
            )
            if death is not None and (death.cause, death.words) == (named.cause, named.words):
                continue
            store.record_death(
                Death(
                    session_id=session.session_id,
                    project=slug,
                    card_number=lane.card_number,
                    cause=named.cause,
                    words=named.words,
                    evidence=named.evidence,
                    last_alive_at=named.last_alive_at,
                    named_at=death.named_at if death is not None else now,
                    settled=named.settled,
                )
            )
            changed = True
        return changed

    def _keep_lane_records(
        self, slug: str, project_path: str, worktrees: dict[str, str | None], now: datetime
    ) -> list[LaneRecord]:
        """The board's record of each lane follows the worktrees on disk: a
        new one is recorded, a present one's tip is refreshed, a gone one is
        stamped gone, and a lane's fold is proved against origin/develop."""
        store = self.live.store
        records = {r.card_number: r for r in store.lanes(slug)}
        for path, branch in worktrees.items():
            number = card_of_cwd(path, project_path)
            if number is None:
                continue
            record = records.get(number)
            on = self.runtime.lane_machine(path).name
            tip = self.runtime.branch_tip(project_path, branch, path=path) if branch else None
            if record is None:
                record = LaneRecord(
                    project=slug,
                    card_number=number,
                    name=Path(path).name,
                    path=path,
                    branch=branch,
                    birth=tip,
                    tip=tip,
                    first_seen=now,
                    last_seen=now,
                    gone_at=None,
                    folded_at=None,
                    trunk_synced_at=None,
                    main_synced_at=None,
                    machine=on,
                )
            else:
                record = record.model_copy(
                    update={
                        "path": path,
                        "branch": branch or record.branch,
                        "birth": record.birth or tip,
                        "tip": tip or record.tip,
                        "last_seen": now,
                        "gone_at": None,
                        "machine": on,
                    }
                )
            records[number] = record
        for number, record in list(records.items()):
            # A worktree on a machine whose sessions are unread is unread,
            # not gone: the disk that wins is the disk that was read.
            unread = record.machine in self.runtime.unread
            if record.path not in worktrees and record.gone_at is None and not unread:
                record = record.model_copy(update={"gone_at": now})
            if record.folded_at is None and record.tip:
                folded = self.runtime.lane_folded(
                    project_path, record.branch, record.tip, record.birth
                )
                if folded:
                    record = record.model_copy(update={"folded_at": now})
                    store.note(
                        slug,
                        number,
                        AuditKind.FOLDED,
                        Actor.MACHINE,
                        now,
                        f"Folded: {record.tip[:10]} is in origin/develop",
                    )
            records[number] = record
            store.record_lane(record)
        return list(records.values())

    def _recover(
        self,
        live: LiveProject,
        cards: list[Card],
        lanes: dict[int, Lane],
        records: list[LaneRecord],
        events: list[HookEvent],
    ) -> bool:
        """Bring back every lane the machine interrupted, once per cause
        within the horizon, through the gate Start passes; park the rest
        with an end the board reads (plan 68, items 3 to 5).

        Disposition first (item 4): a lane whose card closed, or whose
        session put a decision to the owner, is finished or his whatever
        its row and its handoff say — its handoff expires, its park lifts,
        and nothing resumes. Then the cause: a handoff on a live session
        (a wall, the connection back, the stronger model back), a blocked
        turn its own stop-failure event names as a limit with no handoff,
        or a death the reader named as the machine's. A cause nothing names
        is never resumed. The count follows the card and the cause, not the
        session id, so a replacement's new id is not a fresh budget; a
        launch that fails counts; a wait before any launch does not. The
        row is written before the launch, so a server that dies between
        the two finds it on restart. Returns whether anything moved, so
        the caller re-reads the machine."""
        slug = live.project.slug
        store = self.live.store
        now = clock.now()
        by_record = {r.card_number: r for r in records}
        by_card = {c.number: c for c in cards}
        parks = {p.card_number: p for p in store.parks(slug, standing_only=True)}
        moved_any = False
        changed = False
        """Whether a park was opened or lifted, or a handoff expired: the
        lanes read before this pass no longer say what the store says, so
        the caller re-reads them (the park on the face was a pass behind
        on the floor without this)."""
        for number, lane in lanes.items():
            session, card = lane.session, by_card.get(number)
            if session is None or card is None or card.folded_into is not None:
                continue
            attempts = store.recoveries(slug, number)
            in_flight = next((r for r in attempts if r.verdict is None), None)
            if in_flight is not None:
                self._settle_recovery(slug, number, in_flight, lane, now)
                continue
            park = parks.get(number)
            if session.machine in self.runtime.unread:
                continue  # unread is not ended: nothing is brought back or parked
            interruption = self._interruption(lane, session, events)
            if interruption is None and park is None and session.wall is None:
                continue
            record = by_record.get(number)
            history = store.history(slug, number)
            since = (
                record.first_seen
                if record is not None
                else lane.hands_on_since or entered_executing_at(history)
            )
            # Disposition first (item 4): finished or his, whatever the
            # interruption; and a park with nothing left to bring back lifts.
            stood, why_stood = disposition(card, lane, history, since)
            if stood != Disposition.UNFINISHED:
                changed = self._leave(slug, number, session, park, stood, why_stood, now) or changed
                continue
            if interruption is None:
                if park is not None:
                    store.lift_park(park.id, now, "nothing is left to bring back")
                    self.live.note(
                        slug,
                        number,
                        AuditKind.RESCUED,
                        Actor.MACHINE,
                        "The wait ended: nothing is left to bring back.",
                    )
                    changed = True
                continue
            cause, words = interruption
            if park is not None:
                if park.waits_on == "floor" and self._holds_room_it_waits_for(session, cause):
                    # Parked on the floor before this rule landed, or a stop
                    # that did not take: the memory is asked back each pass
                    # until the process is gone (card #107); a stop that took
                    # changes the machine, so the caller re-reads it.
                    changed = self._give_memory_back(slug, number, session, history) or changed
                lifted = self._park_lifts(park, session, now)
                if lifted is None:
                    continue
                store.lift_park(park.id, now, lifted)
                self.live.note(
                    slug, number, AuditKind.RESCUED, Actor.MACHINE, f"The wait ended: {lifted}."
                )
                park = None
                changed = True
            # An attempt recorded after the clock keeps its count (item 5):
            # only the horizon's start bounds the window, never the present.
            floor_at = now - timedelta(seconds=RESCUE_HORIZON_SECONDS)
            recent = [r for r in attempts if r.cause == cause and r.started_at > floor_at]
            if recent:
                changed = (
                    self._park(slug, number, session, cause, words, now, recent=recent) or changed
                )
                continue
            # The gate Start passes, for a hop and a resume alike (item 5,
            # finding 2 of the review): a rung with room and the floor on a
            # fresh read. A handoff younger than the horizon names the rung
            # the wall detector chose at the wall, which is fresher than the
            # rule's cache about the account that just ran out, so it is
            # kept whether or not the walled process still stands — the
            # board itself stops it while it waits for room (card #107), and
            # only while the account's own latest reading says its allowance
            # is there, read on every pass so a wait or a restart between
            # passes cannot reuse a rung that ran out; an older handoff asks
            # the rule now.
            placement: Placement | None = None
            wall = session.wall
            young = (
                wall is not None
                and (now - wall.at).total_seconds() < RESCUE_HORIZON_SECONDS
                and self._rung_open(wall, now, session.machine)
            )
            if not young:
                placement, note = self._placement(live.project.path)
                if placement is None:
                    changed = (
                        self._park(slug, number, session, cause, words, now, nowhere=note)
                        or changed
                    )
                    continue
            room = self._room_of(session.machine)
            if room.full:
                # The park is the claim, written once by whichever process
                # gets there first, and the stop follows it: a server that
                # dies between the two leaves a parked lane whose process the
                # next pass stops, and a second server reading the standing
                # park stops a process that is already gone and says nothing.
                wrote = self._park(slug, number, session, cause, words, now, full=room)
                if wrote and self._holds_room_it_waits_for(session, cause):
                    self._give_memory_back(slug, number, session, history)
                changed = wrote or changed
                continue
            try:
                row = store.open_recovery(
                    slug,
                    number,
                    session_id=session.session_id,
                    cause=cause,
                    words=words,
                    at=now,
                    horizon_seconds=RESCUE_HORIZON_SECONDS,
                )
            except StoreRefusal:
                continue  # another process claimed this interruption first; it reports
            count = len(recent) + 1
            had_window = lane.window_open
            reason = f"brought back by the board: {words}"
            result = self.runtime.resume(
                session.short_id,
                prompt=None
                if wall is not None or cause == Cause.WALL
                else self._resume_words(words),
                card=lane.name,
                placement=placement,
                reason=reason,
            )
            alive = result.verdict == LaunchVerdict.ALIVE and result.session is not None
            store.close_recovery(
                row.id,
                verdict=result.verdict.value,
                replacement=result.session.session_id if alive and result.session else None,
                at=clock.now(),
                note=result.reason,
            )
            if not alive:
                self.live.note(
                    slug,
                    number,
                    AuditKind.RESCUED,
                    Actor.MACHINE,
                    f"Could not bring it back after {words}: {result.reason}. Attempt {count} "
                    "for this cause in the last hour; one is made per hour, then it waits.",
                )
                continue
            moved_any = True
            assert result.session is not None
            placed = result.placement
            where = rung_words(placed.model, placed.slot) if placed else result.session.slot
            said = f"Brought back after {words}: now {result.session.short_id}, {where}"
            if had_window:
                # The stop ended the attach window (`claude attach` exits with
                # its session); recording that is not closing one, and the
                # record has to say so before a new window may open.
                for window in store.windows(session.session_id, open_only=True):
                    store.window_closed(window.id, clock.now())
                try:
                    self.runtime.window(result.session.short_id, WindowKind.LANE)
                    said += ", new window opened"
                except WindowRefused as refusal:
                    said += f"; the new window did not open: {refusal}"
            self.live.note(
                slug,
                number,
                AuditKind.RESCUED,
                Actor.MACHINE,
                f"{said}. Attempt {count} for this cause in the last hour; one is made per "
                "hour, then it waits.",
            )
        return moved_any or changed

    def _interruption(
        self, lane: Lane, session: Session, events: list[HookEvent]
    ) -> tuple[Cause, str] | None:
        """What interrupted this lane, when the machine's hand did: the
        cause and the words the card shows. None for a lane at work, one
        that ended by its own hand, one whose ending nothing names, and
        one the runtime cannot resume — the owner's own terminal, or a
        worker of the other make, which has no transcript to resume from
        (plan 57): both are named truly on the card and left to him."""
        if session.kind == SessionKind.INTERACTIVE or session.slot == codex.SLOT:
            return None
        if lane.state == LaneState.MOVING and session.wall is not None:
            cause = handoffs.cause_of(session.wall)
            reason = (
                session.wall.reason.strip().splitlines()[0] if session.wall.reason.strip() else ""
            )
            return cause, f"{cause.value} on {session.slot}" + (f" ({reason})" if reason else "")
        if lane.state == LaneState.BLOCKED and session.wall is None:
            limit = self._limit_without_a_handoff(session, events)
            if limit is not None:
                return Cause.WALL, f"{Cause.WALL.value} on {session.slot} ({limit})"
            return None
        if lane.state == LaneState.ENDED and lane.cause in MACHINE_ENDED and lane.died:
            return lane.cause, lane.died
        return None

    def _limit_without_a_handoff(self, session: Session, events: list[HookEvent]) -> str | None:
        """A turn that died on a limit with nowhere to go: `claude-acct`
        writes no handoff when no account has room (its "no headroom
        anywhere" return), so the only trace is the session's own
        stop-failure event naming the error class (item 3). Read from the
        event, never from the registry's detail text."""
        stamp = session.updated_at
        for event in sorted(events, key=lambda e: -e.id):
            if event.session_id != session.session_id or event.kind != HookKind.STOP_FAILURE:
                continue
            if stamp is not None and event.at < stamp - timedelta(seconds=HOOK_SLACK_SECONDS):
                return None
            if event.error == "rate_limit":
                return (event.message or "").strip().splitlines()[0] if event.message else "a limit"
            return None
        return None

    def _resume_words(self, words: str) -> str:
        """What a session the machine ended is told when it comes back
        (item 1): the truth, never `CONTINUE`'s "the subscription ran out",
        which is true of a wall alone (#85's four lanes were told it after a
        reboot)."""
        return (
            f"Continue where you stopped. Your last turn was cut: {words}. Your last tool "
            "call may have run without its result reaching you, and the clock may have "
            "moved: read your worktree and the card before trusting your memory of them, "
            "and check what landed before doing it again."
        )

    def _leave(
        self,
        slug: str,
        number: int,
        session: Session,
        park: Park | None,
        stood: Disposition,
        why: str,
        now: datetime,
    ) -> bool:
        """A lane that is finished or the owner's: nothing resumes, a
        handoff naming it expires, and a park on it lifts (items 3 and 4).
        Said once, because each act removes its own evidence. Answers
        whether anything was removed."""
        acted = False
        if session.wall is not None:
            acted = True
            self.runtime.expire_handoff(session.wall, machine_name=session.machine)
            self.live.note(
                slug,
                number,
                AuditKind.RESCUED,
                Actor.MACHINE,
                f"A request to move {session.short_id} expired unacted: the work is "
                f"{stood.value} ({why}).",
            )
        if park is not None:
            acted = True
            self.live.store.lift_park(park.id, now, f"the work is {stood.value}: {why}")
            self.live.note(
                slug,
                number,
                AuditKind.RESCUED,
                Actor.MACHINE,
                f"The wait ended without a resume: the work is {stood.value} ({why}).",
            )
        return acted

    def _holds_room_it_waits_for(self, session: Session, cause: Cause) -> bool:
        """A walled session whose process still stands while its lane waits
        for room — and only one with a standing handoff: that file is what
        names its ending a wall to bring back (`runtime/reasons.py::cause_of`).
        A limit read from a stop-failure event with no handoff is left
        running; stopped, its ending would read as a plain stop and the
        park would lift with nothing to bring back."""
        return cause == Cause.WALL and session.wall is not None and session.pid is not None

    def _give_memory_back(
        self, slug: str, number: int, session: Session, history: list[AuditEntry]
    ) -> bool:
        """A walled background session has ended its turn with nothing in
        flight; while the board waits for room it holds only memory, which
        is part of the room it waits for (card #107: six lanes walled
        together on 2026-09-09 held 1.1 GB for an hour on a machine 1 GB
        short of the floor). Stopped through its own slot after the park is
        written; the handoff is kept, so the ending is named a wall and the
        lane is brought back on the handoff's rung once the room holds. Each
        outcome is said once: a stop that did not take is asked again each
        pass in silence, and a second server stopping a process the first
        already ended adds no second line. Answers whether the process is
        gone, so the caller re-reads the machine."""
        stopped = self.runtime.stop(session.short_id, keep_handoff=True)
        if stopped.gone:
            said = (
                f"Stopped {session.short_id} on {session.slot} to give its memory back while "
                "it waits for room"
            )
        else:
            said = (
                f"Asked {session.short_id} on {session.slot} to stop, to give its memory back "
                f"while it waits for room; it had not gone within {stopped.seconds:.0f} s: "
                f"{stopped.words}"
            )
        newest = next((h for h in history if h.kind == AuditKind.RESCUED), None)
        first_word = said.split(" ", 1)[0]
        if newest is not None and newest.detail.startswith(f"{first_word} {session.short_id} "):
            return stopped.gone
        self.live.note(slug, number, AuditKind.RESCUED, Actor.MACHINE, f"{said}.")
        return stopped.gone

    def _rung_open(self, wall: Handoff, now: datetime, machine_name: str = "") -> bool:
        """Whether the account the wall chose still has its allowance, by
        that account's own latest reading: a lane that waited for room may
        have waited past the hour in which the rung was fresh. Every spent
        allowance counts, and one spent with no time for its return cannot
        be read as back (Codex's reading of card #107's second pass)."""
        reading = self.runtime.limits(wall.account, machine_name=machine_name)
        if reading is None:
            return True
        for label, share in reading.spent.items():
            if share < 1.0:
                continue
            when = reading.resets.get(label)
            if when is None:
                return False
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            if when > now:
                return False
        return True

    def _park_lifts(self, park: Park, session: Session, now: datetime) -> str | None:
        """Whether the park's end has come, in words when it has (item 3),
        by what it waits on: the clock alone for the hour's count; a reset
        or, sooner, the rule finding room on another account for an
        allowance; the machine's memory held above the floor for a whole
        beat; the rule alone for a wait on any account with room."""
        store = self.live.store
        if park.until is not None and now >= park.until:
            return f"the wait ran to its end at {park.until.strftime('%Y-%m-%d %H:%MZ')}"
        if park.waits_on == "clock":
            return None
        if park.waits_on == "floor":
            room = self._room_of(session.machine)
            if room.full:
                if park.held_since is not None:
                    store.hold_park(park.id, None)
                return None
            if park.held_since is None:
                store.hold_park(park.id, now)
                return None
            if (now - park.held_since).total_seconds() >= FLOOR_SECONDS:
                return "the machine's memory has held above the floor for a whole beat"
            return None
        placement, _ = self._placement(self._repo_of(session))
        if placement is None:
            return None
        if park.waits_on == "allowance" and placement.slot == session.slot:
            return None
        return f"the rule found room on {placement.slot} ({placement.why})"

    def _park(
        self,
        slug: str,
        number: int,
        session: Session,
        cause: Cause,
        words: str,
        now: datetime,
        *,
        recent: list[Recovery] | None = None,
        nowhere: str | None = None,
        full: Headroom | None = None,
    ) -> bool:
        """Park the lane with what it waits on and until when, as a machine
        fact with its evidence (item 3, ruling 3): the allowance's reset
        from the account's own last reading, the floor's numbers, the
        account with room the rule has yet to find, or the hour's count.
        Written once: the store refuses a second standing park, so a
        restart or a second process says nothing more."""
        store = self.live.store
        until: datetime | None = None
        parts: list[str] = []
        waits_on = "rule"
        if recent:
            waits_on = "clock"
            first = min(recent, key=lambda r: r.started_at)
            oldest = first.started_at
            until = oldest + timedelta(seconds=RESCUE_HORIZON_SECONDS)
            outcome = (
                "it came back" if first.verdict in ("alive", "found") else "it did not come back"
            )
            parts.append(
                f"the board tried once already in the last hour after {cause.value} (at "
                f"{oldest.strftime('%H:%MZ')}, {outcome}); one attempt is made per hour, so it "
                f"waits until {until.strftime('%Y-%m-%d %H:%MZ')}"
            )
            ahead = [r for r in recent if r.started_at > now]
            if ahead:
                parts.append(
                    f"that attempt is recorded at {ahead[0].started_at.strftime('%H:%MZ')}, "
                    f"after the clock's {now.strftime('%H:%MZ')}: the clock moved, and the "
                    "count stands"
                )
        if cause == Cause.WALL:
            reading = self.runtime.limits(session.slot, machine_name=session.machine)
            reset = limits.next_reset(reading) if reading is not None else None
            if reset is not None:
                label, when = reset
                if until is None or when > until:
                    until = when
                if not recent:
                    waits_on = "allowance"
                parts.append(
                    f"{label} on {session.slot} comes back at {when.strftime('%Y-%m-%d %H:%MZ')} "
                    f"(the account's own reading of "
                    f"{reading.fetched_at.strftime('%H:%MZ') if reading else '?'})"
                    + ("" if recent else ", or an account has room sooner")
                )
            elif not recent:
                parts.append(
                    f"no reading of {session.slot} says when its allowance comes back, so the "
                    "rule is asked on every pass"
                )
        if nowhere is not None:
            parts.append(f"no account has room to run it ({nowhere}); the rule is asked every pass")
        if full is not None:
            waits_on = "floor"
            parts.append(f"{full.sentence}; it comes back once the room has held for a whole beat")
        what = "; ".join(parts) or "the rule is asked every pass"
        try:
            store.open_park(
                slug,
                number,
                session_id=session.session_id,
                cause=cause,
                words=f"it waits: {what}; then it comes back by itself",
                waits_on=waits_on,
                until=until,
                held_since=None,
                at=now,
            )
        except StoreRefusal:
            return False
        self.live.note(
            slug,
            number,
            AuditKind.RESCUED,
            Actor.MACHINE,
            f"Waiting to bring it back after {words}: {what}.",
        )
        return True

    def _settle_recovery(
        self, slug: str, number: int, row: Recovery, lane: Lane, now: datetime
    ) -> None:
        """An attempt written before a launch that nothing closed: this
        server died between the launch and its record, or another process
        is still verifying (item 2). The replacement is found by the
        registry's own word — the session that says it resumed the
        interrupted one — or, for a session started fresh because its
        transcript was too large to resume, by a live background session
        in the lane born after the attempt; recorded either way. Past the
        in-flight window with none found, the attempt is lost and counts;
        an attempt recorded after the clock is still in flight."""
        store = self.live.store
        for session in self.runtime.sessions():
            born_here = (
                session.pid is not None
                and not session.stale
                and session.kind == SessionKind.BACKGROUND
                and lane.path is not None
                and (session.worktree == lane.path or session.cwd == lane.path)
                and session.created_at is not None
                and session.created_at >= row.started_at
            )
            if (session.resumed_from == row.session_id and session.pid is not None) or born_here:
                store.close_recovery(
                    row.id,
                    verdict="found",
                    replacement=session.session_id,
                    at=now,
                    note="the replacement was found registered after the board restarted",
                )
                self.live.note(
                    slug,
                    number,
                    AuditKind.RESCUED,
                    Actor.MACHINE,
                    f"Found {session.short_id} on {session.slot} already brought back after "
                    f"{row.words}; the board had restarted before it could say so.",
                )
                return
        if (now - row.started_at).total_seconds() < RECOVERY_IN_FLIGHT_SECONDS:
            return  # still verifying, or recorded after the clock: not lost
        store.close_recovery(
            row.id,
            verdict="lost",
            replacement=None,
            at=now,
            note="no replacement was found registered within the in-flight window",
        )
        self.live.note(
            slug,
            number,
            AuditKind.RESCUED,
            Actor.MACHINE,
            f"An attempt to bring it back after {row.words} left no session behind; it "
            "counts as one for this cause in the last hour.",
        )

    def _keep_in_scope(self, lanes: dict[int, Lane], slug: str) -> bool:
        """A session with hands on a lane runs in the lane's scope, whoever
        put it back (plan 53, item 2). The machine's recover unit resumes a
        killed session into the subscription's daemon scope, and so does a
        hand `claude --bg --resume`; there, the next kill takes every lane
        on that subscription at once (17:59Z on 2026-09-05: four Hello
        Revenue lanes in one second). Every background session found
        outside its lane's scope is put back in it through the runtime's
        one adopt, once per session, and the card says so in one row; an
        interactive session is the owner's own terminal and stays where his
        terminal put it. Returns whether anything was moved, so the caller
        re-reads the machine."""
        moved_any = False
        for number, lane in lanes.items():
            session = lane.session
            if (
                session is None
                or session.pid is None
                or session.stale
                or session.kind != SessionKind.BACKGROUND
                or session.scope is None
            ):
                continue
            unit = launch.lane_unit(lane.name)
            if session.scope == unit:
                continue
            sighting = self.live.store.sighting(session.session_id)
            if sighting is None or sighting.scoped_at is not None:
                continue  # not sighted yet this pass, or adopted once already this life
            scoped = self.runtime.rescope(session, lane.name)
            # Recorded after the act, so a server that dies between the two
            # asks again on restart; a second reader adopting the same pid
            # is a repeat the manager answers "already there".
            self.live.store.record_sighting(sighting.model_copy(update={"scoped_at": clock.now()}))
            if scoped.verified:
                words = (
                    f"Put {session.short_id} back in the lane's own scope ({unit}); it was "
                    f"running in {session.scope}, where a kill would take every session there."
                )
                moved_any = True
            elif scoped.asked:
                words = (
                    f"Asked the machine to put {session.short_id} back in {unit} from "
                    f"{session.scope}; the move is not verified in /proc yet: {scoped.words}"
                )
            else:
                words = (
                    f"Could not put {session.short_id} back in {unit} from {session.scope}: "
                    f"{scoped.words}"
                )
            self.live.note(slug, number, AuditKind.SCOPED, Actor.MACHINE, words)
        return moved_any

    def _machine_moves(
        self,
        slug: str,
        cards: list[Card],
        lanes: dict[int, Lane],
        records: list[LaneRecord],
    ) -> list[Card]:
        """Into Executing on hands, out of it to where the work says; and a
        card whose document was archived while nothing had hands on it goes
        where the write-up says (plan 06, item 1)."""
        by_record = {r.card_number: r for r in records}
        changed = False
        for card in cards:
            if card.folded_into is not None:
                continue
            lane = lanes[card.number]
            signal, _ = watch_signal(card)
            leaving = None
            if lane.state != LaneState.NONE:
                history = self.live.store.history(slug, card.number)
                record = by_record.get(card.number)
                since = (
                    record.first_seen
                    if record is not None
                    else lane.hands_on_since or entered_executing_at(history)
                )
                reason = should_enter_executing(card, lane, history)
                if reason is not None:
                    self.live.move(
                        slug,
                        card.number,
                        Place(column=Column.EXECUTING, group=None, position=0),
                        actor=Actor.MACHINE,
                        detail=reason,
                        evidence=Evidence.HANDS_ON,
                    )
                    changed = True
                    continue
                if card.place.column == Column.EXECUTING and lane.state in HANDS_ON:
                    continue
                folded = record.folded_at is not None if record is not None else None
                if folded is False and record is not None and record.tip is None:
                    folded = None
                leaving = exit_for(card, lane, history, folded=folded, signal=signal, since=since)
            if leaving is None:
                leaving = after_archive(card, lane, signal)
            if (
                leaving is None
                and card.place.column == Column.DECISION_MOMENT
                and card.link is not None
                and not card.link.archived
            ):
                leaving = unpark(card, lane, self.live.store.history(slug, card.number))
            if leaving is None:
                continue
            try:
                self.live.move(
                    slug,
                    card.number,
                    Place(column=leaving.column, group=None, position=0),
                    actor=Actor.MACHINE,
                    detail=leaving.reason,
                    evidence=leaving.evidence,
                )
                changed = True
            except Exception as error:  # noqa: BLE001 — refused, and the card says why
                self.live.note(
                    slug,
                    card.number,
                    AuditKind.MOVED,
                    Actor.MACHINE,
                    f"Could not move the card out of {card.place.column}: {error}",
                )
        return self.live.store.cards(slug) if changed else cards

    def _release_finished(
        self,
        slug: str,
        cards: list[Card],
        lanes: dict[int, Lane],
        records: list[LaneRecord],
    ) -> bool:
        """A lane that folded and closed gives its memory back (the plan "as
        many lanes as the machine can hold", item 4): its card is out of
        Executing on a fold the board recorded and a close it took, its turn
        is over, and its background session is still resident — on the
        dial's first night five such lanes held about a gigabyte for hours
        while the machine sat at its ceiling. Stopped through the runtime,
        as a finished reading is, with the card saying so. Every other
        ending — died, walled, asking, stopped by the owner — is left as it
        is: its state is evidence (ruling 5). Returns whether anything was
        stopped, so the caller re-reads the machine."""
        by_record = {r.card_number: r for r in records}
        stopped_any = False
        for card in cards:
            lane = lanes[card.number]
            session = lane.session
            record = by_record.get(card.number)
            if (
                session is None
                or session.pid is None
                or session.machine in self.runtime.unread
                or session.kind != SessionKind.BACKGROUND
                or record is None
                or record.folded_at is None
                or card.place.column == Column.EXECUTING
                or not close_landed(card)
            ):
                continue
            sighting = self.live.store.sighting(session.session_id)
            if sighting is None or sighting.released_at is not None:
                continue  # not sighted yet, or stopped once already this life
            # Its turn is over: the lane reads stopped while the worktree
            # stands, and ended with the process still resident once the
            # fold has removed the worktree (Hello Revenue's fold does; the
            # nine finished lanes on 2026-09-05 all read "its worktree is
            # gone from disk" with a live process behind each). A session
            # blocked on a prompt, or asking, is left: its state is evidence.
            turn_over = lane.state == LaneState.STOPPED or (
                lane.state == LaneState.ENDED
                and lane.path is None
                and session.state == SessionState.DONE
            )
            if not turn_over:
                continue
            history = self.live.store.history(slug, card.number)
            if not close_is_current(card, history, record.first_seen):
                continue
            stopped = self.runtime.stop(session.short_id)
            # Recorded after the act (finding 12): a stop that never ran is
            # asked again on restart; a stop twice is "no process" the second time.
            self.live.store.record_sighting(
                sighting.model_copy(update={"released_at": clock.now()})
            )
            for window in self.live.store.windows(session.session_id, open_only=True):
                self.live.store.window_closed(window.id, clock.now())
            words = (
                f"Stopped {session.short_id} on {session.slot}: the lane folded and closed, "
                "so its session gives its memory back"
                + ("." if stopped.gone else f" (not gone: {stopped.words}).")
            )
            self.live.note(slug, card.number, AuditKind.STOPPED, Actor.MACHINE, words)
            stopped_any = True
        return stopped_any

    def _tell_owner(self, live: LiveProject, cards: list[Card], lanes: dict[int, Lane]) -> None:
        """Tell the owner on his screen, once per thing (card #41): a card
        the machine moved out of Executing whose last such move has no
        `told` row after it, and a running card that started waiting on him
        since he was last told. The ring is owed by the record, not by this
        pass having made the move, so a crash before the `told` row lands
        rings at the next reconcile, a crash after it loses that one ring,
        and the same exit read twice rings once."""
        slug = live.project.slug
        now = clock.now()
        for card in cards:
            lane = lanes.get(card.number)
            if lane is None or lane.state == LaneState.NONE or card.folded_into is not None:
                continue
            history = self.live.store.history(slug, card.number)
            told = next((h for h in history if h.kind == AuditKind.TOLD), None)
            notice = self._exit_owed(live, card, lane, history, told, now) or self._wait_owed(
                live, card, lane, told, now
            )
            if notice is None:
                continue
            # The row before the popup: a crash between the two loses one
            # ring rather than ringing twice for one thing (the plan's
            # ruling; Codex's reading of the other order, 2026-09-09).
            self.live.note(
                slug,
                card.number,
                AuditKind.TOLD,
                Actor.MACHINE,
                f"Told you ({notice.moment}): {notice.words}",
            )
            ledger = Path(self.live.store.path).parent / TOLD_LEDGER
            outcome = self.runtime.tell(notice, show_command(slug, card.number), ledger)
            if not outcome.raised:
                words = outcome.words[0].upper() + outcome.words[1:]
                log.warning("#%s on %s: %s", card.number, slug, outcome.words)
                self.live.note(slug, card.number, AuditKind.TOLD, Actor.MACHINE, words)

    @staticmethod
    def _exit_owed(
        live: LiveProject,
        card: Card,
        lane: Lane,
        history: list[AuditEntry],
        told: AuditEntry | None,
        now: datetime,
    ) -> Notice | None:
        """The card's newest move, when it is the machine's out of
        Executing, no `told` row follows it, it is recent, the lane is not
        parked to come back by itself, and it was not the owner's own Stop
        written down. `history` is newest first. A newer move of any kind
        — his drag, a resume's hands-on — supersedes the exit: an old exit
        never rings over a card that is working again."""
        move = next((h for h in history if h.kind == AuditKind.MOVED), None)
        if (
            move is None
            or move.actor != Actor.MACHINE
            or move.from_place is None
            or move.from_place.column != Column.EXECUTING
            or move.to_place is None
        ):
            return None
        if told is not None and told.id > move.id:
            return None
        if (now - move.at).total_seconds() > TELL_HORIZON_SECONDS:
            return None
        if lane.park is not None:
            return None  # the machine brings it back by itself (#68): not his moment
        # His Stop in this life of the lane — after the move that put the
        # card in Executing and before the exit — makes the exit his: he
        # was there. A Stop before a resume is another life's.
        entry = next(
            (
                h
                for h in history
                if h.kind == AuditKind.MOVED
                and h.id < move.id
                and h.to_place is not None
                and h.to_place.column == Column.EXECUTING
            ),
            None,
        )
        first = entry.id if entry is not None else 0
        his = any(
            h.actor == Actor.OWNER and h.kind == AuditKind.STOPPED and first < h.id < move.id
            for h in history
        )
        if his:
            return None
        return Notice(
            project=live.project.slug,
            project_name=live.project.name,
            card_number=card.number,
            title=card.title,
            words=move.detail,
            moment=Moment.MOVED_ON,
        )

    @staticmethod
    def _wait_owed(
        live: LiveProject, card: Card, lane: Lane, told: AuditEntry | None, now: datetime
    ) -> Notice | None:
        """A running card in a state the board shows as waiting on him,
        that the board does not call spent, whose wait began after he was
        last told and has lasted the grace."""
        if card.place.column != Column.EXECUTING or lane.state not in WAITING_ON_YOU:
            return None
        if lane_is_spent(card, lane):
            return None
        if lane.session is not None and lane.session.kind == SessionKind.INTERACTIVE:
            return None  # his own terminal: he is there
        # A question or a stop began when the hook said so; a prompt is the
        # registry's word, and its own stamp is the wait's start — an older
        # hook message's stamp would hide a new prompt behind an old ring.
        if lane.state == LaneState.BLOCKED:
            since = lane.session.updated_at if lane.session is not None else None
        else:
            since = lane.said_at
        if since is None:
            return None
        waited = (now - since).total_seconds()
        if waited < TELL_GRACE_SECONDS or waited > TELL_HORIZON_SECONDS:
            return None
        if told is not None and told.at >= since:
            return None
        if lane.state == LaneState.ASKING:
            words = f"Asking you: {last_line(lane.question) or last_line(lane.said)}"
        elif lane.state == LaneState.STOPPED:
            words = "Stopped without a question" + (
                f": {last_line(lane.said)}" if lane.said else ""
            )
        else:
            detail = first_line(lane.session.detail) if lane.session is not None else None
            words = "Waiting on a prompt" + (f": {detail}" if detail else "")
        return Notice(
            project=live.project.slug,
            project_name=live.project.name,
            card_number=card.number,
            title=card.title,
            words=words,
            moment=Moment.NEEDS_YOU,
        )

    def _plan_footprint(self, live: LiveProject, card: Card) -> set[str]:
        """The files the card's live plan names in backticks and that exist."""
        root = Path(live.project.path)
        if card.link is None:
            return set()
        document = live.index.find(card.link.kind, card.link.stem)
        if document is None or document.archived:
            return set()
        try:
            text = (root / document.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return set()
        self._parties[(live.project.slug, card.number)] = discussion.named_in(text)
        return footprint(text, lambda path: (root / path).is_file())

    def _footprints(
        self, live: LiveProject, cards: list[Card], lanes: dict[int, Lane]
    ) -> tuple[dict[int, set[str]], dict[int, set[str]], dict[int, Progress | None]]:
        """For every lane with hands on its worktree: what the worktree has
        actually changed (git, re-read on every read), what its plan names,
        and how far it has come by its own copy of the plan (plan 13). Read
        once here for the lanes, the drift and the doors."""
        edits: dict[int, set[str]] = {}
        declared: dict[int, set[str]] = {}
        progress: dict[int, Progress | None] = {}
        for card in cards:
            lane = lanes[card.number]
            if lane.state in HANDS_ON and lane.path:
                edits[card.number] = self.runtime.edits(lane.path)
                declared[card.number] = self._plan_footprint(live, card)
                progress[card.number] = self._lane_progress(live, card, lane.path)
        return edits, declared, progress

    def _lane_progress(self, live: LiveProject, card: Card, lane_path: str) -> Progress | None:
        """The card's plan as the lane's worktree carries it, and — once every
        item is met — the review record there whose `Plan:` names it. One
        file per lane per beat while items are open; the reviews folder is
        listed only in the review loop. Never the main checkout's copy: that
        is the plan as it stood at Start (plan 13, ruling 3). A plan the lane
        has already archived is read from `done/`, so the count holds through
        the close."""
        if card.link is None or card.link.kind != DocumentKind.PLAN:
            return None
        document = live.index.find(card.link.kind, card.link.stem)
        if document is None:
            return None
        docs = self.runtime.lane_docs(
            lane_path, [document.path, f"docs/plans/done/{document.stem}.md"]
        )
        if docs.plan is None:
            return None

        def read_reviews() -> list[tuple[str, str]]:
            # Read only once every item is met (plan 13): a second read of
            # the lane's documents, on the machine that holds them.
            records = self.runtime.lane_docs(lane_path, [], reviews=True).reviews
            return [(r.path, r.text) for r in records]

        return progress_of(
            docs.plan, plan_stem=document.stem, read_reviews=read_reviews, now=clock.now()
        )

    def _doors(
        self,
        live: LiveProject,
        cards: list[Card],
        lanes: dict[int, Lane],
        placement: Placement | None,
        placement_note: str,
        now: datetime,
    ) -> dict[int, Doors]:
        live_lanes = [n for n, lane in lanes.items() if lane.state in HANDS_ON and lane.path]
        editing = {n: set(lanes[n].edits) for n in live_lanes}
        declared = {n: set(lanes[n].declared) for n in live_lanes}
        readings = self.live.store.last_readings(live.project.slug)
        names = {slug: p.project.name for slug, p in self.live.projects.items()}
        triages = self.live.store.latest_triages(live.project.slug)
        titles = self.live.store.latest_title_readings(live.project.slug)
        sources = self.live.sources(live.project.slug)
        answers = self.live.store.answers(live.project.slug)
        doors: dict[int, Doors] = {}
        for card in cards:
            lane = lanes[card.number]
            document = (
                live.index.find(card.link.kind, card.link.stem) if card.link is not None else None
            )
            gate = document.gate if document is not None and document.gate else card.gate
            collision: Collision | None = None
            waits: list[Wait] = []
            if (
                gate is not None
                and card.place.column in STARTABLE_COLUMNS
                and lane.state == LaneState.NONE
            ):
                mine = self._plan_footprint(live, card)
                collision = verdict(mine, editing=editing, declared=declared)
                if document is not None and document.sequenced:
                    waits = waits_for(
                        document.sequenced,
                        here=live.project.slug,
                        projects=names,
                        find=self.live.store.card,
                    )
            signal, _ = watch_signal(card)
            last = readings.get(card.number)
            asks_owner = signal_asks_owner(card, signal, last, now)
            if not asks_owner:
                # A Backlog defect's trigger asks him the same way (plan 11, item 5).
                trigger, _ = trigger_signal(document)
                if trigger_asks_owner(card, trigger, last, now):
                    signal, asks_owner = trigger, True
            doors[card.number] = doors_for(
                card,
                lane,
                gate_named=gate is not None,
                placement=placement,
                placement_note=placement_note,
                collision=collision,
                signal=signal,
                signal_due_for_owner=asks_owner,
                signal_evidence=asked_evidence(signal, last),
                suggestion_live=document is not None
                and document.kind == DocumentKind.SUGGESTION
                and not document.archived,
                waits=waits,
                routed=routing_for(card, document, triages.get(card.number), sources),
                ruled=already_ruled(triages.get(card.number), answers.get(card.number)),
                title_hold=title_hold(titles.get(card.number), document),
            )
        return doors

    # ── the signal loop ────────────────────────────────────────────────

    def read_signals_now(self) -> None:
        """Read every Executed card's signal whose cadence asks for it, and
        move the card on what it says; and every Backlog defect's `Fix: when`
        trigger on the same cadence by the same readers (plan 11, item 5),
        which moves nothing — a delivered trigger makes the defect eligible
        for the dial. A `session` signal is read by a session the loop starts
        (plan 09, item 1): at most READINGS_AT_ONCE alive at a time, one per
        card, and the finding comes back through the reading door."""
        projects = list(self.live.projects.values())
        sessions = self.runtime.sessions()
        for live in projects:
            self._tend_readings(live, sessions)
        alive = sum(
            len(self.live.store.open_windowless_sessions(p.project.slug, SessionWork.READING))
            for p in projects
        )
        for live in projects:
            slug = live.project.slug
            now = clock.now()
            readings = self.live.store.last_readings(slug)
            in_flight = self.live.store.open_windowless_sessions(slug, SessionWork.READING)
            for card in self.live.store.cards(slug):
                if card.folded_into is not None:
                    continue  # a folded card's loop is its leader's
                last = readings.get(card.number)
                signal, _ = watch_signal(card)
                trigger = False
                if not signal_wants_reading(card, signal, last, now):
                    document = document_of(card, live.index)
                    signal, _ = trigger_signal(document)
                    if not (
                        is_trigger_card(card, document)
                        and trigger_wants_reading(card, signal, last, now)
                    ):
                        continue
                    trigger = True
                assert signal is not None
                if signal.kind == SignalKind.SESSION:
                    if card.number in in_flight or alive >= READINGS_AT_ONCE:
                        continue
                    if self._start_reading(live, card, signal, now, trigger=trigger):
                        alive += 1
                    continue
                delivered, words = self.runtime.read_signal(signal, live.project.path)
                self._land(slug, card.number, signal, delivered, words, now, trigger=trigger)

    def _land(
        self,
        slug: str,
        number: int,
        signal: Signal,
        delivered: bool | None,
        words: str,
        now: datetime,
        *,
        trigger: bool = False,
    ) -> None:
        """A machine reading on the card, and the move it implies. A trigger's
        reading implies none: the card stays on the rail, eligible from a
        delivered reading (plan 11, item 5)."""
        self.live.store.record_reading(slug, number, now, delivered, words, Actor.MACHINE)
        self.live.bump()
        if trigger:
            return
        landing = where_after(signal, delivered, now)
        if landing.column is not None:
            self.live.move(
                slug,
                number,
                Place(column=landing.column, group=None, position=0),
                actor=Actor.MACHINE,
                detail=landing.reason,
                evidence=landing.evidence,
            )

    def _start_reading(
        self, live: LiveProject, card: Card, signal: Signal, now: datetime, *, trigger: bool
    ) -> bool:
        """Start the session that reads this card's signal — or its `Fix:
        when` trigger — in the project's own checkout, and record it on the
        card; a start that fails is a machine reading that could not be read,
        so the cadence moves on and the card says why."""
        slug = live.project.slug
        detail = self.live.detail(slug, card.number)
        brief = reading_brief(detail, live.project, signal, now.date().isoformat(), trigger=trigger)
        launch = self.runtime.start_windowless(
            WindowlessStart(
                repo=live.project.path,
                card=reading_name(card.number, card.title),
                brief=brief,
                effort=READING_EFFORT,
            )
        )
        if launch.verdict != LaunchVerdict.ALIVE or launch.session is None:
            self._land(
                slug,
                card.number,
                signal,
                None,
                f"the reading session could not start: {launch.reason}",
                now,
                trigger=trigger,
            )
            return False
        session = launch.session
        self.live.store.open_windowless_session(
            slug, card.number, SessionWork.READING, session.session_id, session.slot, now
        )
        placement = launch.placement
        where = rung_words(placement.model, placement.slot) if placement else session.slot
        self.live.note(
            slug,
            card.number,
            AuditKind.SIGNAL,
            Actor.MACHINE,
            f"Reading started: {session.short_id}, {where}, in {live.project.path}; never "
            "hands on the tree",
        )
        return True

    def tend_windowless(
        self,
        live: LiveProject,
        record: WindowlessSession,
        session: Session | None,
        now: datetime,
        *,
        ceiling_seconds: float,
        what: str,
        without: str,
    ) -> tuple[Tended, str]:
        """One windowless session against the one list (plans 09 and 11):
        a record already ended is let finish its turn and then stopped, so
        a finished session leaves no process behind; a limit mid-work is the
        same move a lane gets, one hop to where the rule says, with the
        record following the new id; a process gone, or one still running
        past the ceiling (stopped here), ends the record with the words that
        say why; a turn finished with the process still there is the
        caller's to judge. `what` names the session in the words ("reading",
        "planning") and `without` what it never produced ("without a
        finding", "without a plan")."""
        slug = live.project.slug
        store = self.live.store
        alive = session is not None and session.pid is not None
        if record.ended_at is not None:
            if alive and session is not None:
                turn_over = session.state != SessionState.WORKING
                overdue = (now - record.ended_at).total_seconds() >= READING_STOP_GRACE_SECONDS
                if turn_over or overdue:
                    self.runtime.stop(session.short_id)
            return Tended.ALIVE, ""
        if alive and session is not None and session.wall is not None:
            moved = self.runtime.move(session.short_id, None)
            if moved.verdict == LaunchVerdict.ALIVE and moved.session is not None:
                store.move_windowless_session(
                    record.id, moved.session.session_id, moved.session.slot
                )
                self.live.note(
                    slug,
                    record.card_number,
                    AuditKind.SIGNAL,
                    Actor.MACHINE,
                    f"{what.capitalize()} moved: hit a limit on {session.slot} "
                    f"({session.wall.reason}); now {moved.session.short_id} on "
                    f"{moved.session.slot}",
                )
                return Tended.MOVED, ""
            store.end_windowless_session(record.id, now)
            return (
                Tended.ENDED,
                f"the {what} session hit a limit on {session.slot} ({session.wall.reason}) "
                f"and could not be moved: {moved.reason}",
            )
        turn_done = session is not None and session.state == SessionState.DONE
        overran = (now - record.started_at).total_seconds() >= ceiling_seconds
        if alive and not overran:
            return (Tended.TURN_DONE if turn_done else Tended.ALIVE), ""
        store.end_windowless_session(record.id, now)
        if alive and session is not None:
            stopped = self.runtime.stop(session.short_id)
            return (
                Tended.ENDED,
                f"the {what} session {session.short_id} ran {ceiling_seconds / 60:.0f} min "
                f"{without} and was stopped"
                + ("" if stopped.gone else f" (not gone: {stopped.words})"),
            )
        why = self.runtime.why_ended(session) if session is not None else None
        return Tended.ENDED, f"the {what} session ended {without}" + (f" ({why})" if why else "")

    def _tend_readings(self, live: LiveProject, sessions: list[Session]) -> None:
        """The reading sessions the board started: one that ended without a
        finding is recorded as unreadable so the cadence moves on and the
        card says why. A turn that finished without the verb will never
        write one — the registry's `done` is that fact — so it is stopped
        and recorded the same way; the ceiling is for a session that stops
        at a question nobody sees."""
        by_id = {s.session_id: s for s in sessions if not s.stale}
        now = clock.now()
        records = self.live.store.windowless_sessions(live.project.slug, work=SessionWork.READING)
        for record in records:
            session = by_id.get(record.session_id)
            tended, words = self.tend_windowless(
                live,
                record,
                session,
                now,
                ceiling_seconds=READING_SECONDS,
                what="reading",
                without="without a finding",
            )
            if tended == Tended.TURN_DONE and session is not None:
                self.live.store.end_windowless_session(record.id, now)
                stopped = self.runtime.stop(session.short_id)
                words = (
                    f"the reading session {session.short_id} finished its turn without a "
                    "finding and was stopped"
                    + ("" if stopped.gone else f" (not gone: {stopped.words})")
                )
                tended = Tended.ENDED
            if tended == Tended.ENDED:
                self._reading_ended(live, record.card_number, words, now)

    def _reading_ended(self, live: LiveProject, number: int, words: str, now: datetime) -> None:
        """A reading that produced no finding, on the card: a machine reading
        that could not be read while the card still waits on its signal or
        its trigger, a note otherwise."""
        slug = live.project.slug
        card = self.live.store.card(slug, number)
        if card is None:
            return
        signal, _ = watch_signal(card)
        if signal is not None and card.place.column == Column.EXECUTED:
            self._land(slug, number, signal, None, words, now)
            return
        document = document_of(card, live.index)
        trigger, _ = trigger_signal(document)
        if trigger is not None and is_trigger_card(card, document):
            self._land(slug, number, trigger, None, words, now, trigger=True)
            return
        self.live.note(slug, number, AuditKind.SIGNAL, Actor.MACHINE, words)

    # ── the trunk loop ─────────────────────────────────────────────────

    def level_trunks_now(self) -> None:
        """Keep every project's main checkout level with origin/develop, and
        stamp each folded lane's trunk and main facts as they become true."""
        for live in list(self.live.projects.values()):
            self.level_project(live)

    def level_clones_now(self) -> None:
        """Keep every other machine's clone of every project level with the
        trunk (card #83, item 3), and record per machine and project which
        clone was not — in the store, so the head's machine line and the
        terminal's `needle machines` read the one record (Codex's ninth
        pass) — never as the trunk's own state, which is the board's
        checkout's alone (the eighth)."""
        # Every other machine gets its whole set written, an empty one when
        # the board has no projects, so no row outlives the project it was
        # about (Codex's eleventh pass).
        stale: dict[str, dict[str, str | None]] = {
            m.name: {} for m in self.runtime.machines() if not self.runtime.is_here(m)
        }
        for live in list(self.live.projects.values()):
            for m, levelled in self.runtime.level_elsewhere(live.project.path):
                words = (
                    None if levelled.level is True else levelled.note or f"{levelled.behind} behind"
                )
                stale.setdefault(m.name, {})[live.project.slug] = words
        changed = False
        for name, projects in stale.items():
            changed = self.live.store.record_clones(name, projects, clock.now()) or changed
        if changed:
            self.live.bump()

    def level_project(self, live: LiveProject) -> TrunkState:
        slug, path = live.project.slug, live.project.path
        now = clock.now()
        if not self.runtime.is_repository(path):
            state = TrunkState(
                level=None, behind=0, note=f"{path} is not a git repository", read_at=now
            )
        else:
            result = self.runtime.level(path)
            state = TrunkState(
                level=result.level, behind=result.behind, note=result.note, read_at=now
            )
        before = self.live.store.trunk(slug)
        self.live.store.record_trunk(slug, state)
        if (before.level, before.behind, before.note) != (state.level, state.behind, state.note):
            self.live.bump()
        if state.level:
            for record in self.live.store.lanes(slug):
                if record.folded_at is None or record.tip is None:
                    continue
                update = {}
                if record.trunk_synced_at is None:
                    update["trunk_synced_at"] = now
                    self.live.note(
                        slug,
                        record.card_number,
                        AuditKind.SYNCED,
                        Actor.MACHINE,
                        "Trunk synced: the main checkout is level with origin/develop",
                    )
                if record.main_synced_at is None and self.runtime.in_stable(path, record.tip):
                    update["main_synced_at"] = now
                    self.live.note(
                        slug,
                        record.card_number,
                        AuditKind.SYNCED,
                        Actor.MACHINE,
                        f"Main synced: {record.tip[:10]} is in origin/main",
                    )
                if update:
                    self.live.store.record_lane(record.model_copy(update=update))
        return state
