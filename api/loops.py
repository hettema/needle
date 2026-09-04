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
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

from watchfiles import awatch

from board.assemble import asked_evidence, signal_asks_owner, signal_wants_reading, watch_signal
from board.brief import reading_brief, reading_name
from board.collision import footprint, verdict
from board.lane import (
    HANDS_ON,
    STARTABLE_COLUMNS,
    LaneFacts,
    after_archive,
    card_of_cwd,
    conversations_alive,
    doors_for,
    entered_executing_at,
    exit_for,
    lane_for,
    should_enter_executing,
    with_footprints,
)
from board.signals import where_after
from domain.audit import AuditKind
from domain.board import MachineState, TrunkState
from domain.card import Actor, Card, Place
from domain.column import Column
from domain.document import DocumentKind
from domain.evidence import Evidence
from domain.gate import Gate
from domain.hook import HookEvent, HookPosted
from domain.lane import Collision, Doors, Lane, LaneRecord, LaneSnapshot, LaneState
from domain.launch import LaunchVerdict, ReadingStart
from domain.session import Session, SessionState
from domain.signal import Signal, SignalKind
from domain.slot import Placement
from domain.window import Window, WindowKind
from infrastructure import clock
from infrastructure.live import Live, LiveProject
from infrastructure.paths import data_dir
from runtime import machine
from runtime.service import Runtime
from runtime.windows import WindowRefused

log = logging.getLogger("needle")

FLOOR_SECONDS = 30.0
"""The lane loop's floor: a session that dies without a hook (a kill, a
reboot) is on the board within this, whatever else is quiet."""
SIGNAL_SECONDS = 60.0
TRUNK_SECONDS = 300.0
RESCUE_HORIZON_SECONDS = 3600.0
"""One automatic retry per run-out: a second wall on the same lane within
this window parks the lane with the reason instead of thrashing."""
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
        self._deaths: dict[str, str] = {}
        self._parked: set[str] = set()
        """Session ids whose second wall was parked, so the card is told once."""

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
        for task in self._tasks:
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
            await asyncio.to_thread(self.reconcile_now)

    async def read_signals(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.read_signals_now)

    async def level_trunks(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.level_trunks_now)

    async def hooks(self, posted: list[HookPosted]) -> list[HookEvent]:
        recorded = self.record_hooks(posted)
        await self.reconcile()
        return recorded

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
        self.live.set_machine(MachineState(missing=self.runtime.machine_is_reachable()))
        sessions = self.runtime.sessions()
        windows = self.runtime.open_windows()
        placement, note = self._placement()
        for live in list(self.live.projects.values()):
            try:
                self._reconcile_project(live, sessions, windows, placement, note)
            except Exception as error:  # noqa: BLE001 — one project's failure never hides another's
                log.warning(
                    "reconciling %s failed (%s: %s)", live.project.slug, type(error).__name__, error
                )

    def _placement(self) -> tuple[Placement | None, str]:
        where = self.runtime.where(None, [], cached=True)
        return where.placement, where.reason

    def _reconcile_project(
        self,
        live: LiveProject,
        sessions: list[Session],
        windows: list[Window],
        placement: Placement | None,
        placement_note: str,
    ) -> None:
        slug, project = live.project.slug, live.project
        store = self.live.store
        now = clock.now()
        cards = store.cards(slug)
        worktrees = (
            self.runtime.worktrees(project.path) if self.runtime.is_repository(project.path) else {}
        )
        records = self._keep_lane_records(slug, project.path, worktrees, now)
        facts = self._facts(live, sessions, windows, records, worktrees, now)
        lanes = {c.number: lane_for(c, facts) for c in cards}
        if self._rescue(lanes, slug):
            sessions = self.runtime.sessions()
            windows = self.runtime.open_windows()
            facts = self._facts(live, sessions, windows, records, worktrees, now)
            lanes = {c.number: lane_for(c, facts) for c in cards}
        cards = self._machine_moves(slug, cards, lanes, records)
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
        for session in here:
            if session.pid is None and session.session_id not in self._deaths:
                why = self.runtime.why_ended(session)
                if why:
                    self._deaths[session.session_id] = why
        return LaneFacts(
            project_path=path,
            sessions=sessions,
            events=self.live.store.hook_events(slug),
            discussions=self.live.store.discussions(slug),
            records=records,
            windows=windows,
            rescues=rescues,
            deaths=dict(self._deaths),
            worktrees=worktrees,
            now=now,
        )

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
            tip = self.runtime.branch_tip(project_path, branch) if branch else None
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
                    }
                )
            records[number] = record
        for number, record in list(records.items()):
            if record.path not in worktrees and record.gone_at is None:
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

    def _rescue(self, lanes: dict[int, Lane], slug: str) -> bool:
        """Act on the wall detector's handoff: move the lane where it names,
        once per run-out, and say so on the card."""
        moved_any = False
        store = self.live.store
        for number, lane in lanes.items():
            session = lane.session
            if lane.state != LaneState.MOVING or session is None or session.wall is None:
                continue
            now = clock.now()
            recent = [
                r
                for r in store.rescues(session.session_id)
                if (now - r.at).total_seconds() < RESCUE_HORIZON_SECONDS
            ]
            if recent:
                if session.session_id not in self._parked:
                    self._parked.add(session.session_id)
                    self.live.note(
                        slug,
                        number,
                        AuditKind.RESCUED,
                        Actor.MACHINE,
                        f"Parked: hit a limit again within the hour ({session.wall.reason}); "
                        "one automatic retry per run-out, so this one is yours (Resume).",
                    )
                continue
            had_window = lane.window_open
            result = self.runtime.move(session.short_id, None)
            if result.verdict != LaunchVerdict.ALIVE or result.session is None:
                self.live.note(
                    slug,
                    number,
                    AuditKind.RESCUED,
                    Actor.MACHINE,
                    f"The move after the limit failed: {result.reason}",
                )
                continue
            moved_any = True
            placement = result.placement
            model = placement.model.value if placement else "fable"
            slot = placement.slot if placement else result.session.slot
            said = f"Moved to {model} on {slot}"
            if had_window:
                # The stop ended the attach window (`claude attach` exits with
                # its session); recording that is not closing one, and the
                # record has to say so before a new window may open.
                for window in self.live.store.windows(session.session_id, open_only=True):
                    self.live.store.window_closed(window.id, clock.now())
                try:
                    self.runtime.window(result.session.short_id, WindowKind.LANE)
                    said += ", new window opened"
                except WindowRefused as refusal:
                    said += f"; the new window did not open: {refusal}"
            self.live.note(slug, number, AuditKind.RESCUED, Actor.MACHINE, said + ".")
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
        return footprint(text, lambda path: (root / path).is_file())

    def _footprints(
        self, live: LiveProject, cards: list[Card], lanes: dict[int, Lane]
    ) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
        """For every lane with hands on its worktree: what the worktree has
        actually changed (git, re-read on every read) and what its plan
        names. Read once here for the lanes, the drift and the doors."""
        edits: dict[int, set[str]] = {}
        declared: dict[int, set[str]] = {}
        for card in cards:
            lane = lanes[card.number]
            if lane.state in HANDS_ON and lane.path:
                edits[card.number] = self.runtime.edits(lane.path)
                declared[card.number] = self._plan_footprint(live, card)
        return edits, declared

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
        doors: dict[int, Doors] = {}
        for card in cards:
            lane = lanes[card.number]
            document = (
                live.index.find(card.link.kind, card.link.stem) if card.link is not None else None
            )
            gate = document.gate if document is not None and document.gate else card.gate
            collision: Collision | None = None
            if (
                gate is not None
                and card.place.column in STARTABLE_COLUMNS
                and lane.state == LaneState.NONE
            ):
                mine = self._plan_footprint(live, card)
                collision = verdict(mine, editing=editing, declared=declared)
            signal, _ = watch_signal(card)
            last = readings.get(card.number)
            asks_owner = signal_asks_owner(card, signal, last, now)
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
            )
        return doors

    # ── the signal loop ────────────────────────────────────────────────

    def read_signals_now(self) -> None:
        """Read every Executed card's signal whose cadence asks for it, and
        move the card on what it says. A `session` signal is read by a
        session the loop starts (plan 09, item 1): at most READINGS_AT_ONCE
        alive at a time, one per card, and the finding comes back through
        the reading door."""
        projects = list(self.live.projects.values())
        sessions = self.runtime.sessions()
        for live in projects:
            self._tend_readings(live, sessions)
        alive = sum(len(self.live.store.open_reading_sessions(p.project.slug)) for p in projects)
        for live in projects:
            slug = live.project.slug
            now = clock.now()
            readings = self.live.store.last_readings(slug)
            in_flight = self.live.store.open_reading_sessions(slug)
            for card in self.live.store.cards(slug):
                if card.folded_into is not None:
                    continue  # a folded card's loop is its leader's
                signal, _ = watch_signal(card)
                if not signal_wants_reading(card, signal, readings.get(card.number), now):
                    continue
                assert signal is not None
                if signal.kind == SignalKind.SESSION:
                    if card.number in in_flight or alive >= READINGS_AT_ONCE:
                        continue
                    if self._start_reading(live, card, signal, now):
                        alive += 1
                    continue
                delivered, words = self.runtime.read_signal(signal, live.project.path)
                self._land(slug, card.number, signal, delivered, words, now)

    def _land(
        self,
        slug: str,
        number: int,
        signal: Signal,
        delivered: bool | None,
        words: str,
        now: datetime,
    ) -> None:
        """A machine reading on the card, and the move it implies."""
        self.live.store.record_reading(slug, number, now, delivered, words, Actor.MACHINE)
        self.live.bump()
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

    def _start_reading(self, live: LiveProject, card: Card, signal: Signal, now: datetime) -> bool:
        """Start the session that reads this card's signal, in the project's
        own checkout, and record it on the card; a start that fails is a
        machine reading that could not be read, so the cadence moves on and
        the card says why."""
        slug = live.project.slug
        detail = self.live.detail(slug, card.number)
        brief = reading_brief(detail, live.project, signal, now.date().isoformat())
        launch = self.runtime.read_by_session(
            ReadingStart(
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
            )
            return False
        session = launch.session
        self.live.store.open_reading_session(
            slug, card.number, session.session_id, session.slot, now
        )
        placement = launch.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else session.slot
        self.live.note(
            slug,
            card.number,
            AuditKind.SIGNAL,
            Actor.MACHINE,
            f"Reading started: {session.short_id}, {where}, in {live.project.path}; never "
            "hands on the tree",
        )
        return True

    def _tend_readings(self, live: LiveProject, sessions: list[Session]) -> None:
        """The reading sessions the board started, against the one list: one
        whose process is gone without a finding is recorded as unreadable so
        the cadence moves on and the card says why; one still running past
        READING_SECONDS is stopped and recorded the same way; one whose
        finding has landed is stopped once its turn is over, so a finished
        reading leaves no process behind."""
        slug = live.project.slug
        by_id = {s.session_id: s for s in sessions if not s.stale}
        now = clock.now()
        for record in self.live.store.reading_sessions(slug):
            session = by_id.get(record.session_id)
            alive = session is not None and session.pid is not None
            if record.ended_at is not None:
                if not alive or session is None:
                    continue
                turn_over = session.state != SessionState.WORKING
                overdue = (now - record.ended_at).total_seconds() >= READING_STOP_GRACE_SECONDS
                if turn_over or overdue:
                    self.runtime.stop(session.short_id)
                continue
            if alive and session is not None and session.wall is not None:
                # A limit mid-reading: the same move a lane gets, one hop to
                # where the rule says, and the record follows the new id.
                moved = self.runtime.move(session.short_id, None)
                if moved.verdict == LaunchVerdict.ALIVE and moved.session is not None:
                    self.live.store.move_reading_session(
                        record.id, moved.session.session_id, moved.session.slot
                    )
                    self.live.note(
                        slug,
                        record.card_number,
                        AuditKind.SIGNAL,
                        Actor.MACHINE,
                        f"Reading moved: hit a limit on {session.slot} ({session.wall.reason}); "
                        f"now {moved.session.short_id} on {moved.session.slot}",
                    )
                    continue
                self.live.store.end_reading_session(record.id, now)
                self._reading_ended(
                    live,
                    record.card_number,
                    f"the reading session hit a limit on {session.slot} ({session.wall.reason}) "
                    f"and could not be moved: {moved.reason}",
                    now,
                )
                continue
            # A turn that finished without the verb will never write one:
            # the registry's `done` is that fact, and the ceiling is for a
            # session that stops at a question nobody sees.
            turn_done = session is not None and session.state == SessionState.DONE
            overran = (now - record.started_at).total_seconds() >= READING_SECONDS
            if alive and not turn_done and not overran:
                continue
            self.live.store.end_reading_session(record.id, now)
            if alive and session is not None:
                stopped = self.runtime.stop(session.short_id)
                words = (
                    f"the reading session {session.short_id} "
                    + (
                        "finished its turn without a finding"
                        if turn_done
                        else f"ran {READING_SECONDS / 60:.0f} min without a finding"
                    )
                    + " and was stopped"
                    + ("" if stopped.gone else f" (not gone: {stopped.words})")
                )
            else:
                why = self.runtime.why_ended(session) if session is not None else None
                words = "the reading session ended without a finding" + (f" ({why})" if why else "")
            self._reading_ended(live, record.card_number, words, now)

    def _reading_ended(self, live: LiveProject, number: int, words: str, now: datetime) -> None:
        """A reading that produced no finding, on the card: a machine reading
        that could not be read while the card still waits on its signal, a
        note otherwise."""
        slug = live.project.slug
        card = self.live.store.card(slug, number)
        if card is None:
            return
        signal, _ = watch_signal(card)
        if signal is None or card.place.column != Column.EXECUTED:
            self.live.note(slug, number, AuditKind.SIGNAL, Actor.MACHINE, words)
            return
        self._land(slug, number, signal, None, words, now)

    # ── the trunk loop ─────────────────────────────────────────────────

    def level_trunks_now(self) -> None:
        """Keep every project's main checkout level with origin/develop, and
        stamp each folded lane's trunk and main facts as they become true."""
        for live in list(self.live.projects.values()):
            self.level_project(live)

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


def queue_path() -> Path:
    """Where the hook script queues events while the board is down."""
    return data_dir() / "hook-queue.jsonl"
