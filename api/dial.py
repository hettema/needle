"""The dial's cadence: the owner's standing ruling applied by the board
(plan 11, item 4).

INTENT.md: one move is his — he decides what enters execution. Pressing
Start on each card is today's way of recording that decision; the dial is
the same decision made once, as a document line the finder writes (`Fix:
now`) and a toggle he holds. While it is on, and fewer fix lanes are live
than his number, the board takes the oldest marked defect whose Start would
otherwise be open, starts a windowless planning session in the project's
checkout, follows the plan it writes onto the card, and opens the Start
door itself with the machine as the actor — so the card's history says
*started by the dial*. From there the lane runs as any lane. What needs
him stops and asks on the card.

This module is the one place besides the owner's own doors that reaches
Start, and it reaches it through the door, never the runtime, and never
with the dial off: `tests/ratchets/test_start_is_the_owners_click.py`
holds both. The loops (`api/loops.py`, what the board does on evidence)
still never start anything; the dial runs on its own timer under the
loops' lock, so a tick and a machine read never act on one lane at once.
"""

import asyncio
import contextlib
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from api.doors import REPO_ROOT, DoorFailed, DoorRefused, Doors, plan_skill
from api.loops import Loops, Tended
from board.assemble import document_of, routing_for
from board.brief import (
    lane_name,
    planning_brief,
    planning_name,
    ruling_brief,
    split_brief,
    triage_brief,
    triage_name,
)
from board.dial import (
    LIVE_STAGES,
    MEMORY_FLOOR_BYTES,
    Candidate,
    headroom,
    held_lanes,
    is_quiet,
    rail_count,
    rail_defects,
    running,
    why_not_eligible,
)
from board.lane import has_row, is_question
from board.triage import already_ruled, source_ref_of, split_row
from domain.audit import AuditKind
from domain.card import Actor, Card
from domain.dial import Dial as DialSetting
from domain.dial import DialState, Fixes, FixLane, FixReport, FixStage, Waiting
from domain.document import Document, DocumentKind
from domain.gate import Gate
from domain.hook import HookKind
from domain.lane import LaneState
from domain.launch import LaunchVerdict, WindowlessStart
from domain.row import Row, RowKind
from domain.session import SessionState
from domain.signal import SessionWork
from domain.triage import (
    CorpusLane,
    CorpusLaneKind,
    Decision,
    Fate,
    Routing,
    Triage,
    TriageResult,
)
from infrastructure import clock
from infrastructure.live import Live, LiveProject
from infrastructure.store import StoreRefusal
from runtime.service import Runtime

log = logging.getLogger("needle")

DIAL_SECONDS = 60.0
"""The dial's beat: one defect taken per beat at most, so a dial set to
three fills in three minutes and every start re-reads the machine."""
PLANNING_EFFORT = Gate.XHIGH
"""A plan written with no owner in the loop is thinking work: the same
effort the Plan door gives a conversation with him."""
PLANNING_SECONDS = 3600.0
"""A planning session still without a plan or a question past this is
stopped and the card says so."""
PLANNING_SETTLE_SECONDS = 120.0
"""After a planning session's turn ends, how long the board waits for the
corpus watcher to card the plan it pushed before calling the session ended
without one: the commit lands before the turn does, and the watcher
rescans within a second or two."""

TRIAGE_EFFORT = Gate.HIGH
"""Reading one document against one source and applying a written rule is
work, not thinking work: the plan the dial writes gets xhigh, the reading
that decides who may write it gets high."""
TRIAGE_SECONDS = 1800.0
"""A reading still without a result past this is stopped and the card says
so; it reads two documents and answers one question."""
TRIAGE_ATTEMPTS = 3
"""How many readings may die on one card before the board stops opening
them. Without a cap a defect whose brief kills the session is an infinite
beat, and the card would say `needs triage` forever with nothing saying
why."""
CORPUS_LANE_SECONDS = 1800.0
CORPUS_LANE_ATTEMPTS = 2
"""One retry. A corpus lane writes one document from a record that already
selected the outcome; a second failure is a fact about the brief or the
machine, not luck, and the card says the half-state rather than looping."""
CORPUS_LANES_AT_ONCE = 1
"""These are not fix lanes and do not count against the dial's number, so
they carry their own ceiling: one at a time, board-wide."""
SPLIT_FROM = "split from"
"""The head line the split lane writes on the half it extracts: how the
board finds the new document, and then its card, without being told."""
RULED_BY = "ruled by"
"""The head line the ruling lane writes: how a cold session reads where the
mark came from, from the document rather than from a database."""

CLASS_LINE = "class"
"""The plan's head line that names what makes the class loud (plan 11,
item 4, the third rule); `needle fixes` reads it."""


def _class_closer(document) -> str | None:
    if document is None:
        return None
    return next((f.value for f in document.head_fields if f.key.lower() == CLASS_LINE), None)


class Dial:
    def __init__(self, live: Live, runtime: Runtime, loops: Loops, doors: Doors):
        self.live = live
        self.runtime = runtime
        self.loops = loops
        self.doors = doors
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    # ── lifecycle ──────────────────────────────────────────────────────

    async def run(self) -> None:
        self._task = asyncio.create_task(self._timer())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _timer(self) -> None:
        while not self._stop.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), DIAL_SECONDS)
            if self._stop.is_set():
                return
            try:
                await self.tick()
            except Exception as error:  # noqa: BLE001 — the dial never dies quietly
                log.warning("the dial failed (%s: %s); it runs again", type(error).__name__, error)

    async def tick(self) -> None:
        async with self.loops.lock:
            await asyncio.to_thread(self.tick_now)

    # ── the owner turns it ─────────────────────────────────────────────

    def turn(self, *, on: bool, lanes: int, actor: Actor = Actor.OWNER) -> DialState:
        """The owner's turn of the dial (plan 11, item 3), audited as his.
        The first turn to on records the rail as it stands, by who filed
        each card: the baseline the loop reads the rail against (item 6)."""
        before = self.live.store.dial()
        after = self.live.store.turn_dial(on=on, lanes=lanes, actor=actor, at=clock.now())
        if after.on and before.first_on_at is None:
            self.live.store.record_rail_at_on(self._rail_now())
        self.live.bump()
        return self.state()

    def state(self) -> DialState:
        """The dial as the head shows it, with the machine read if this
        board has not read it yet (the terminal's own process)."""
        self._full()
        return self.live.dial_state()

    def _rail_now(self):
        return [
            rail_count(slug, self.live.store.cards(slug), live.index)
            for slug, live in self.live.projects.items()
        ]

    # ── the beat ───────────────────────────────────────────────────────

    def tick_now(self) -> None:
        """Read the machine's memory against the floor; follow every fix
        lane the dial has open — a plan that landed to its Start, a lane
        that folded or ended to its end, a planning session that died to the
        card — whether or not the dial is still on; then, with it on, room
        under the number and room on the machine, take the next defect."""
        self.live.set_headroom(headroom(self.runtime.meminfo(), MEMORY_FLOOR_BYTES, clock.now()))
        self._follow()
        # A corpus lane applies what a record already selected — the owner's
        # own answer, or a separation the reading proposed — so it runs
        # whether or not the dial is on. The dial is his ruling about what
        # enters execution *without* him; his own ruling is not that.
        self._corpus_lanes()
        setting = self.live.store.dial()
        if not setting.on:
            return
        self._take_next(setting)

    def _full(self) -> str | None:
        """The head's sentence while the machine is under the floor; the
        beat opens nothing — no planning session, no Start — until it is
        not (the number is a ceiling the machine lowers, ruling 4). A board
        that has not read the machine yet — `needle fixes` in its own
        process — reads it now, so the terminal's reasons are the beat's."""
        room = self.live.headroom
        if room is None:
            room = headroom(self.runtime.meminfo(), MEMORY_FLOOR_BYTES, clock.now())
            self.live.set_headroom(room)
        return room.sentence if room.full else None

    def _take_next(self, setting: DialSetting) -> None:
        """One act per beat: plan a defect a reading has verified, or open
        the reading that would verify one. Verified defects go first — a rail
        of untriaged cards would otherwise fill the number with readings and
        never plan anything, which is the starvation the ceiling makes
        possible the moment a triage counts against it (plan 59, item 3)."""
        store = self.live.store
        fix_lanes = store.fix_lanes()
        if self._full() is not None:
            return
        held = held_lanes(fix_lanes, self.live.start_offered)
        triaging = self._triaging()
        if running(fix_lanes, held, triaging=triaging) >= setting.lanes:
            return
        lanes_by_project = {
            slug: live.snapshot.lanes
            for slug, live in self.live.projects.items()
            if live.snapshot is not None
        }
        quiet = is_quiet(lanes_by_project)
        candidates: list[Candidate] = []
        unread: list[Candidate] = []
        for slug, live in self.live.projects.items():
            snapshot = live.snapshot
            if snapshot is None:
                continue  # the machine has not been read for this project yet
            readings = store.last_readings(slug)
            planning = store.open_windowless_sessions(slug, SessionWork.PLANNING)
            open_triage = store.open_windowless_sessions(slug, SessionWork.TRIAGE)
            triages = store.latest_triages(slug)
            sources = self.live.sources(slug)
            ran = {f.card_number for f in fix_lanes if f.project == slug}
            for card, document in rail_defects(store.cards(slug), live.index):
                routed = routing_for(card, document, triages.get(card.number), sources)
                assert routed is not None  # a rail defect always routes somewhere
                why = why_not_eligible(
                    card,
                    document,
                    routed=routed,
                    last=readings.get(card.number),
                    lane=snapshot.lanes.get(card.number),
                    planning_open=card.number in planning,
                    triage_open=card.number in open_triage,
                    ran_before=card.number in ran,
                )
                if why is None:
                    doors = snapshot.doors.get(card.number)
                    if doors is None or doors.placement is None:
                        continue  # nowhere to run: the card would say so on Start too
                    candidates.append(Candidate(project=slug, card=card, document=document))
                elif self._wants_a_reading(slug, card, document, routed, snapshot):
                    # No placement check here: a reading is a windowless
                    # session in the project's own checkout, so the card's
                    # Start door — which is about a worktree — has nothing to
                    # say about whether it can run.
                    unread.append(Candidate(project=slug, card=card, document=document))
        for candidate in sorted(candidates, key=lambda c: c.age_key):
            live = self.live.projects[candidate.project]
            if self._own_board(live) and not quiet:
                continue  # a fold on the board restarts the service under every running lane
            self._plan(live, candidate)
            return
        for candidate in sorted(unread, key=lambda c: c.age_key):
            self._triage(self.live.projects[candidate.project], candidate)
            return

    def _triaging(self) -> int:
        return sum(
            len(self.live.store.open_windowless_sessions(slug, SessionWork.TRIAGE))
            for slug in self.live.projects
        )

    def _wants_a_reading(self, slug, card: Card, document, routed, snapshot) -> bool:
        """Whether the board should open a reading on this defect now. Only
        the two states that mean *nobody has verified today's text*: a
        cannot-tell is not retried, because the evidence it named has to
        arrive first — and when it does, the document or the source moves and
        the row goes stale, which is this same door."""
        if routed.state not in (Routing.NEEDS_TRIAGE, Routing.STALE):
            return False
        lane = snapshot.lanes.get(card.number)
        if lane is not None and (lane.state != LaneState.NONE or lane.path is not None):
            return False
        if has_row(card, RowKind.ASK):
            return False
        return self._readings_that_died(slug, card.number) < TRIAGE_ATTEMPTS

    def _readings_that_died(self, slug: str, number: int) -> int:
        """How many readings the board opened on this card that landed no
        result: the record of sessions, less the results."""
        store = self.live.store
        opened = [
            r
            for r in store.windowless_sessions(slug, work=SessionWork.TRIAGE)
            if r.card_number == number
        ]
        landed = {t.session_id for t in store.triages(slug, number) if t.session_id}
        return sum(1 for r in opened if r.session_id not in landed and r.ended_at is not None)

    def _triage(self, live: LiveProject, candidate: Candidate) -> None:
        """Open the one independent reading of this defect's mark, in the
        project's own checkout. The brief carries the rule, the document
        whole, and the source the mark cites as this board resolved it — so
        the reading never has to go looking for context it must not have."""
        slug, project = live.project.slug, live.project
        card = candidate.card
        now = clock.now()
        detail = self.live.detail(slug, card.number)
        sources = self.live.sources(slug)
        ref = source_ref_of(candidate.document.fix.why if candidate.document.fix else None)
        brief = triage_brief(
            detail,
            project,
            now.date().isoformat(),
            document_text=self._document_text(live, candidate.document),
            source=sources.resolve(ref),
        )
        launch = self.runtime.start_windowless(
            WindowlessStart(
                repo=project.path,
                card=triage_name(card.number, card.title),
                brief=brief,
                effort=TRIAGE_EFFORT,
            )
        )
        if launch.verdict != LaunchVerdict.ALIVE or launch.session is None:
            words = f"The board could not start a reading of the mark: {launch.reason}"
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)
            return
        session = launch.session
        try:
            self.live.store.open_windowless_session(
                slug, card.number, SessionWork.TRIAGE, session.session_id, session.slot, now
            )
        except StoreRefusal as refusal:
            # A second reading raced this one to the table; the store refuses
            # it, so this session has nothing to write through and is stopped.
            self.runtime.stop(session.short_id)
            log.info("a second triage was refused on #%s: %s", card.number, refusal)
            return
        placement = launch.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else session.slot
        self.live.note(
            slug,
            card.number,
            AuditKind.DIAL,
            Actor.MACHINE,
            f"A reading of its mark started: {session.short_id}, {where}, in {project.path}; "
            "never hands on the tree",
        )

    def _document_text(self, live: LiveProject, document: Document) -> str:
        try:
            return (Path(live.project.path) / document.path).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as error:
            return f"(the board could not read {document.path}: {error})"

    def _own_board(self, live: LiveProject) -> bool:
        return Path(live.project.path).resolve() == REPO_ROOT.resolve()

    def _plan(self, live: LiveProject, candidate: Candidate) -> None:
        """Start the planning session for one defect, in the project's own
        checkout, and open the fix lane's record. A start that fails is a
        fix lane that ended before it began: the card says why, and the dial
        leaves it to the owner rather than trying every beat."""
        slug, project = live.project.slug, live.project
        card = candidate.card
        now = clock.now()
        detail = self.live.detail(slug, card.number)
        brief = planning_brief(
            detail,
            project,
            now.date().isoformat(),
            skill=plan_skill(Path(project.path)),
            first_lane=self._own_board(live),
        )
        launch = self.runtime.start_windowless(
            WindowlessStart(
                repo=project.path,
                card=planning_name(card.number, card.title),
                brief=brief,
                effort=PLANNING_EFFORT,
            )
        )
        verified = self.live.store.latest_triages(slug).get(card.number)
        fix = self.live.store.open_fix_lane(
            slug,
            card.number,
            now,
            decision=verified.decision if verified is not None else None,
        )
        if launch.verdict != LaunchVerdict.ALIVE or launch.session is None:
            words = f"The dial could not start a planning session: {launch.reason}"
            self.live.store.stage_fix_lane(fix.id, FixStage.ENDED, now, note=words)
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)
            return
        session = launch.session
        self.live.store.open_windowless_session(
            slug, card.number, SessionWork.PLANNING, session.session_id, session.slot, now
        )
        placement = launch.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else session.slot
        self.live.note(
            slug,
            card.number,
            AuditKind.DIAL,
            Actor.MACHINE,
            f"The dial took it: planning session {session.short_id}, {where}, in "
            f"{project.path}; never hands on the tree",
        )

    # ── following what the dial opened ─────────────────────────────────

    def _follow(self) -> None:
        fix_lanes = self.live.store.fix_lanes()
        if any(f.stage in LIVE_STAGES for f in fix_lanes):
            # A plan that landed changed the card's gate and its footprint,
            # and a lane that folded changed its record: the doors the Start
            # is judged by are this read's, not the beat before.
            self.loops.reconcile_now()
        now = clock.now()
        sessions = self.runtime.sessions()
        by_id = {s.session_id: s for s in sessions if not s.stale}
        for fix in fix_lanes:
            live = self.live.projects.get(fix.project)
            if live is None:
                continue
            card = self.live.store.card(fix.project, fix.card_number)
            if card is None:
                continue
            if fix.stage == FixStage.PLANNING:
                self._follow_planning(live, fix, card, by_id, now)
            elif fix.stage == FixStage.PLANNED:
                self._start(live, fix, card, now)
            elif fix.stage == FixStage.STARTED:
                self._follow_lane(live, fix, card, now)
        # A planning session whose plan or question has landed is let finish
        # its turn and then stopped, as a finished reading is (review pass 1):
        # its record is ended but its process is not, and nothing else tends
        # a record no fix lane is at the planning stage for.
        for live in self.live.projects.values():
            slug = live.project.slug
            for record in self.live.store.windowless_sessions(slug, work=SessionWork.PLANNING):
                if record.ended_at is None:
                    continue
                self.loops.tend_windowless(
                    live,
                    record,
                    by_id.get(record.session_id),
                    now,
                    ceiling_seconds=PLANNING_SECONDS,
                    what="planning",
                    without="without a result",
                )
            self._follow_triages(live, by_id, now)

    def _follow_triages(self, live: LiveProject, by_id, now: datetime) -> None:
        """The readings the board opened: one that ended without a result
        leaves the card exactly where it was — nobody's — with the reason on
        the card, and the beat opens another until the cap. A reading never
        inherits its card to the owner by dying, which is the failure that
        made the old default dangerous."""
        slug = live.project.slug
        store = self.live.store
        landed = {t.session_id for t in store.triages(slug) if t.session_id}
        for record in store.windowless_sessions(slug, work=SessionWork.TRIAGE):
            session = by_id.get(record.session_id)
            tended, words = self.loops.tend_windowless(
                live,
                record,
                session,
                now,
                ceiling_seconds=TRIAGE_SECONDS,
                what="triage",
                without="without a result",
            )
            if tended == Tended.TURN_DONE and session is not None:
                if record.session_id in landed:
                    continue  # its result landed; the door ended the record
                store.end_windowless_session(record.id, now)
                stopped = self.runtime.stop(session.short_id)
                words = (
                    f"the reading {session.short_id} finished its turn without a result and "
                    "was stopped"
                    + ("" if stopped.gone else f" (not gone: {stopped.words})")
                )
                tended = Tended.ENDED
            if tended == Tended.ENDED:
                died = self._readings_that_died(slug, record.card_number)
                left = (
                    "the board reads it again"
                    if died < TRIAGE_ATTEMPTS
                    else f"{died} readings have died on it; the board stops opening them"
                )
                self.live.note(
                    slug,
                    record.card_number,
                    AuditKind.DIAL,
                    Actor.MACHINE,
                    f"{words}; the card stays nobody's and {left}",
                )
                self.live.bump()

    def _follow_planning(self, live: LiveProject, fix: FixLane, card: Card, by_id, now) -> None:
        """A planning session ends one of three ways: its plan lands and the
        card is the plan's (the corpus watcher relinked it), it left a
        question on the card, or it ended with neither — and the record says
        which."""
        slug = live.project.slug
        store = self.live.store
        record = next(
            (
                r
                for r in store.windowless_sessions(slug, work=SessionWork.PLANNING, open_only=True)
                if r.card_number == card.number
            ),
            None,
        )
        planned = card.link is not None and card.link.kind == DocumentKind.PLAN
        if planned:
            if record is not None:
                store.end_windowless_session(record.id, now)
            planned_fix = store.stage_fix_lane(fix.id, FixStage.PLANNED, now)
            assert card.link is not None
            self.live.note(
                slug,
                card.number,
                AuditKind.DIAL,
                Actor.MACHINE,
                f"The plan landed ({card.link.path()}); the dial opens Start next",
            )
            self._start(live, planned_fix, card, now)
            return
        if has_row(card, RowKind.ASK):
            if record is not None:
                store.end_windowless_session(record.id, now)
            asked = next(r.text for r in card.rows if r.kind == RowKind.ASK)
            store.stage_fix_lane(fix.id, FixStage.ASKED, now, note=asked)
            self.live.note(
                slug,
                card.number,
                AuditKind.DIAL,
                Actor.MACHINE,
                f"The planning session left it to you: {asked}",
            )
            return
        if record is None:
            words = "no planning session is open for it and no plan landed"
            store.stage_fix_lane(fix.id, FixStage.ENDED, now, note=words)
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)
            return
        session = by_id.get(record.session_id)
        tended, words = self.loops.tend_windowless(
            live,
            record,
            session,
            now,
            ceiling_seconds=PLANNING_SECONDS,
            what="planning",
            without="without a plan",
        )
        if tended == Tended.TURN_DONE and session is not None:
            settled = session.updated_at
            if settled is None or (now - settled).total_seconds() < PLANNING_SETTLE_SECONDS:
                return  # the plan it pushed may still be on its way onto the card
            store.end_windowless_session(record.id, now)
            stopped = self.runtime.stop(session.short_id)
            words = (
                f"the planning session {session.short_id} finished its turn without a plan or "
                "a question and was stopped"
                + ("" if stopped.gone else f" (not gone: {stopped.words})")
            )
            tended = Tended.ENDED
        if tended == Tended.ENDED:
            store.stage_fix_lane(fix.id, FixStage.ENDED, now, note=words)
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)
            self.live.bump()

    def _start(self, live: LiveProject, fix: FixLane, card: Card, now: datetime) -> None:
        """Open the Start door as the machine. A door that is closed —
        collision, nowhere to run — is waited on, with the reason on the
        record once; a start the machine failed ends the dial's part, and
        the card says why."""
        slug = live.project.slug
        store = self.live.store
        detail = self.live.detail(slug, card.number)
        why = self._full() if detail.doors.start.offered else detail.doors.start.why
        if why is not None:
            if fix.note != why:
                store.stage_fix_lane(fix.id, FixStage.PLANNED, fix.planned_at or now, note=why)
                self.live.note(
                    slug, card.number, AuditKind.DIAL, Actor.MACHINE, f"Start waits: {why}"
                )
            return
        try:
            result = self.doors.start(slug, card.number, actor=Actor.MACHINE)
        except DoorRefused as refusal:
            if fix.note != str(refusal):
                store.stage_fix_lane(
                    fix.id, FixStage.PLANNED, fix.planned_at or now, note=str(refusal)
                )
            return
        except DoorFailed as failure:
            store.stage_fix_lane(fix.id, FixStage.ENDED, now, note=str(failure))
            return
        store.stage_fix_lane(fix.id, FixStage.STARTED, now, note=result.said)

    def _follow_lane(self, live: LiveProject, fix: FixLane, card: Card, now: datetime) -> None:
        slug = live.project.slug
        store = self.live.store
        record = store.lane(slug, card.number)
        if record is not None and record.folded_at is not None:
            words = f"the fix lane folded ({(record.tip or '')[:10]})"
            store.stage_fix_lane(fix.id, FixStage.FOLDED, record.folded_at, note=words)
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)
            return
        lane = live.snapshot.lanes.get(card.number) if live.snapshot is not None else None
        if lane is not None and lane.state == LaneState.ENDED:
            words = "the fix lane ended with nothing folded" + (
                f" ({lane.died})" if lane.died else ""
            )
            store.stage_fix_lane(fix.id, FixStage.ENDED, now, note=words)
            self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, words)


    # ── the short lanes that write the corpus (items 4 and 5) ──────────

    def _corpus_lanes(self) -> None:
        """Follow every corpus lane the board has open, then open at most one
        more. They are not fix lanes and do not count against the dial's
        number, so they carry their own ceiling — one at a time, board-wide —
        and they wait on the machine's memory like everything else."""
        now = clock.now()
        by_id = {s.session_id: s for s in self.runtime.sessions() if not s.stale}
        for live in self.live.projects.values():
            self._follow_corpus_lanes(live, by_id, now)
        if self._full() is not None:
            return
        if len(self.live.store.corpus_lanes(open_only=True)) >= CORPUS_LANES_AT_ONCE:
            return
        lanes_by_project = {
            slug: live.snapshot.lanes
            for slug, live in self.live.projects.items()
            if live.snapshot is not None
        }
        quiet = is_quiet(lanes_by_project)
        for live in self.live.projects.values():
            if self._own_board(live) and not quiet:
                continue  # a fold on the board restarts the service under every running lane
            if self._open_corpus_lane(live, now):
                return

    def _split_half(self, live: LiveProject, document: Document) -> Document | None:
        """The half a split lane extracted, found by the `Split from:` line
        the brief told it to write — read from the corpus, never from the
        lane's own claim that it worked."""
        for other in live.index.documents:
            if other.archived or other.kind != DocumentKind.SUGGESTION:
                continue
            line = next(
                (f.value for f in other.head_fields if f.key.lower() == SPLIT_FROM), None
            )
            if line and document.path in line:
                return other
        return None

    def _applied(
        self, live: LiveProject, lane: CorpusLane, document: Document | None
    ) -> Document | None:
        """The document that proves this lane did its job, or None. A ruling
        lane proves itself with the `Ruled by:` line naming its decision on
        the card's own document; a split lane with the extracted half naming
        the document it came out of. Both are read from the corpus, because
        a lane's word for whether it landed is the one thing a lane cannot
        be trusted about."""
        if document is None:
            return None
        if lane.kind == CorpusLaneKind.RULING:
            ruled = next(
                (f.value for f in document.head_fields if f.key.lower() == RULED_BY), None
            )
            return document if ruled and lane.decision in ruled else None
        return self._split_half(live, document)

    def _follow_corpus_lanes(self, live: LiveProject, by_id, now: datetime) -> None:
        slug = live.project.slug
        store = self.live.store
        for lane in store.corpus_lanes(slug, open_only=True):
            card = store.card(slug, lane.card_number)
            if card is None:
                store.end_corpus_lane(lane.id, now, "the card is gone")
                continue
            document = document_of(card, live.index)
            landed = self._applied(live, lane, document)
            if landed is not None:
                self._land_corpus_lane(live, lane, card, document, landed, now)
                continue
            session = by_id.get(lane.session_id) if lane.session_id else None
            alive = session is not None and session.pid is not None
            overran = (now - lane.opened_at).total_seconds() >= CORPUS_LANE_SECONDS
            if alive and not overran:
                if session.state == SessionState.WORKING:
                    continue
                settled = session.updated_at
                if settled is None or (now - settled).total_seconds() < PLANNING_SETTLE_SECONDS:
                    continue  # its push may still be on its way into the corpus
            words = (
                f"the {lane.kind.value} lane ran past {CORPUS_LANE_SECONDS / 60:.0f} minutes "
                "without the corpus saying it"
                if overran
                else f"the {lane.kind.value} lane's turn ended without the corpus saying it"
                if alive
                else f"the {lane.kind.value} lane's session is gone and the corpus does not say it"
            )
            if alive and session is not None:
                stopped = self.runtime.stop(session.short_id)
                if not stopped.gone:
                    words += f" (not gone: {stopped.words})"
            store.end_corpus_lane(lane.id, now, words)
            again = (
                "the board opens one more"
                if lane.attempt < CORPUS_LANE_ATTEMPTS
                else "the board stops trying; the record stands and this card is half-ruled"
            )
            self.live.note(
                slug,
                lane.card_number,
                AuditKind.DIAL,
                Actor.MACHINE,
                f"{words}; {again}",
            )
            self.live.bump()

    def _land_corpus_lane(
        self,
        live: LiveProject,
        lane: CorpusLane,
        card: Card,
        document: Document | None,
        landed: Document,
        now: datetime,
    ) -> None:
        """The corpus says what the lane was opened to write. A ruling is
        done here: the document carries the mark and where it came from, and
        the card's next reading verifies the new text as it verifies any
        text. A split has one more act — the two halves are told about each
        other, and the extracted half is given the decision it came out of,
        so one command follows both fates from one identity (item 6)."""
        slug = live.project.slug
        store = self.live.store
        if lane.kind == CorpusLaneKind.SPLIT:
            other = self._card_behind(live, landed)
            if other is None:
                return  # the new document is there; its card is a watcher away
            assert document is not None
            self.live.add_row(
                slug,
                card.number,
                Row(
                    kind=RowKind.SPLIT,
                    text=split_row(
                        landed.path, "the half the record does not settle", lane.decision
                    ),
                ),
                Actor.MACHINE,
            )
            self.live.add_row(
                slug,
                other.number,
                Row(
                    kind=RowKind.SPLIT,
                    text=split_row(document.path, "the half the record settles", lane.decision),
                ),
                Actor.MACHINE,
            )
            store.record_triage(
                slug,
                other.number,
                at=now,
                actor=Actor.MACHINE,
                result=TriageResult.SPLIT,
                words=(
                    f"extracted from {document.path} by the split of #{card.number}; the reading "
                    "that proposed the split authorised neither half, so this one is nobody's "
                    "until it is read on its own"
                ),
                decision=uuid.uuid4().hex[:16],
                parent=lane.decision,
                direction=None,
                source_ref=None,
                source_path=None,
                source_fingerprint=None,
                document_fingerprint=landed.fingerprint,
                session_id=lane.session_id,
            )
            said = (
                f"The split landed: {landed.path} carries the half the record settles, and "
                f"#{other.number} is its card; both halves are nobody's until each is read"
            )
        else:
            said = (
                f"Your ruling is in the corpus: {landed.path} carries the mark and names "
                f"decision {lane.decision}; a fresh reading verifies the new text"
            )
        # Its work is in the corpus, so its session has nothing left to do:
        # a finished lane leaves no process behind, the same rule a finished
        # reading gets (plan 09's review, pass 1).
        if lane.session_id is not None:
            session = next(
                (s for s in self.runtime.sessions() if s.session_id == lane.session_id), None
            )
            if session is not None and session.pid is not None:
                stopped = self.runtime.stop(session.short_id)
                if not stopped.gone:
                    said += f" (its session is not gone: {stopped.words})"
        store.end_corpus_lane(lane.id, now, said)
        self.live.note(slug, card.number, AuditKind.DIAL, Actor.MACHINE, said)
        self.live.bump()

    def _card_behind(self, live: LiveProject, document: Document) -> Card | None:
        for card in self.live.store.cards(live.project.slug):
            if (
                card.link is not None
                and card.link.kind == document.kind
                and card.link.stem == document.stem
            ):
                return card
        return None

    def _open_corpus_lane(self, live: LiveProject, now: datetime) -> bool:
        """Open the one corpus lane this project wants, if it wants one.

        Neither condition can fire twice for the same decision: the moment
        the lane's write lands, the document's fingerprint moves and the
        reading behind it goes stale, which is neither `needs triage` after a
        split nor `triaged his` after a ruling. So the only reason to open a
        second is that the first died without writing, and that is capped."""
        slug = live.project.slug
        store = self.live.store
        triages = store.latest_triages(slug)
        answers = store.answers(slug)
        sources = self.live.sources(slug)
        for card, document in rail_defects(store.cards(slug), live.index):
            triage = triages.get(card.number)
            if triage is None:
                continue
            routed = routing_for(card, document, triage, sources)
            if routed is None:
                continue
            kind: CorpusLaneKind | None = None
            if (
                triage.result == TriageResult.SPLIT
                and triage.actor == Actor.SESSION
                and routed.state == Routing.NEEDS_TRIAGE
            ):
                # A reading proposed it. The machine writes a `split` record
                # of its own on the half it extracts — that one is
                # bookkeeping saying *this half is unread*, never a second
                # proposal, and a lane opened on it would split a document
                # nobody said held two decisions.
                kind = CorpusLaneKind.SPLIT
            elif (
                routed.state == Routing.TRIAGED_HIS
                and already_ruled(triage, answers.get(card.number)) is not None
            ):
                kind = CorpusLaneKind.RULING
            if kind is None:
                continue
            tried = [
                other
                for other in store.corpus_lanes(slug, decision=triage.decision)
                if other.kind == kind
            ]
            if any(other.ended_at is None for other in tried) or len(tried) >= CORPUS_LANE_ATTEMPTS:
                continue
            detail = self.live.detail(slug, card.number)
            today = now.date().isoformat()
            if kind == CorpusLaneKind.SPLIT:
                brief = split_brief(detail, live.project, today, triage=triage)
            else:
                answer = answers[card.number]
                brief = ruling_brief(
                    detail, live.project, today, triage=triage, answer=answer.detail
                )
            self.doors.corpus_lane(
                slug,
                card.number,
                kind=kind,
                decision=triage.decision,
                brief=brief,
                attempt=len(tried) + 1,
            )
            return True
        return False

    # ── the loop, counted (item 6) ─────────────────────────────────────

    def waiting(self, slug: str | None) -> list[Waiting]:
        """Every defect on the rail the dial is not taking, with why, in the
        order it would take them (review pass 2): a dial that is on with
        nothing starting has to say which fact holds it — unmarked, his, a
        trigger not yet fired, a lane on it, nowhere to run, the board's own
        rail while a lane is live — or the fourteen-day guard in the plan's
        WATCH row reads as the path not running when it is the rail."""
        store = self.live.store
        fix_lanes = store.fix_lanes()
        lanes_by_project = {
            s: live.snapshot.lanes for s, live in self.live.projects.items() if live.snapshot
        }
        quiet = is_quiet(lanes_by_project)
        found: list[Waiting] = []
        for project_slug, live in self.live.projects.items():
            if slug is not None and project_slug != slug:
                continue
            snapshot = live.snapshot
            readings = store.last_readings(project_slug)
            planning = store.open_windowless_sessions(project_slug, SessionWork.PLANNING)
            triaging = store.open_windowless_sessions(project_slug, SessionWork.TRIAGE)
            triages = store.latest_triages(project_slug)
            sources = self.live.sources(project_slug)
            ran = {f.card_number for f in fix_lanes if f.project == project_slug}
            for card, document in rail_defects(store.cards(project_slug), live.index):
                routed = routing_for(card, document, triages.get(card.number), sources)
                assert routed is not None
                why = why_not_eligible(
                    card,
                    document,
                    routed=routed,
                    last=readings.get(card.number),
                    lane=snapshot.lanes.get(card.number) if snapshot else None,
                    planning_open=card.number in planning,
                    triage_open=card.number in triaging,
                    ran_before=card.number in ran,
                )
                if why is None:
                    doors = snapshot.doors.get(card.number) if snapshot else None
                    if snapshot is None:
                        why = "the machine has not been read for this project yet"
                    elif doors is None or doors.placement is None:
                        why = f"nowhere to run: {doors.placement_note if doors else 'unread'}"
                    elif self._full() is not None:
                        why = self._full()
                    elif self._own_board(live) and not quiet:
                        why = "the board's own rail waits until no lane is live anywhere"
                    else:
                        why = "eligible: the next beat takes it if the number allows"
                found.append(
                    Waiting(
                        project=project_slug,
                        card_number=card.number,
                        title=card.title,
                        born_at=card.born_at,
                        why=why,
                    )
                )
        return sorted(found, key=lambda w: (w.born_at, w.card_number))

    def decisions(self, slug: str | None) -> list[Decision]:
        """Every decision a colleague took on the owner's rail, oldest
        first, with the source it leaned on, the direction it moved the
        product and what became of it (plan 59, item 6).

        Nothing here is bookkeeping the board keeps separately: the fate is
        read off the fix lanes, the lane records and the corpus that already
        exist, so a decision's fate cannot drift from the facts. That is what
        makes the cold audit the loop asks for an act rather than a
        reconstruction."""
        store = self.live.store
        fix_lanes = store.fix_lanes()
        out: list[Decision] = []
        for project_slug, live in self.live.projects.items():
            if slug is not None and project_slug != slug:
                continue
            sources = self.live.sources(project_slug)
            triages = store.latest_triages(project_slug)
            for triage in store.triages(project_slug):
                card = store.card(project_slug, triage.card_number)
                if card is None:
                    continue
                document = document_of(card, live.index)
                routed = routing_for(card, document, triages.get(card.number), sources)
                resolved = sources.resolve(triage.source_ref)
                out.append(
                    Decision(
                        decision=triage.decision,
                        parent=triage.parent,
                        project=project_slug,
                        card_number=card.number,
                        title=card.title,
                        at=triage.at,
                        result=triage.result,
                        words=triage.words,
                        direction=triage.direction,
                        source=(
                            resolved.note
                            if resolved is not None
                            else "the reading named no source"
                        ),
                        routing=routed.state if routed is not None else Routing.NEEDS_TRIAGE,
                        fate=self._fate(live, card, triage, fix_lanes),
                    )
                )
        return sorted(out, key=lambda d: d.at)

    def _fate(
        self, live: LiveProject, card: Card, triage: Triage, fix_lanes: list[FixLane]
    ) -> Fate:
        slug = live.project.slug
        store = self.live.store
        mine = [
            f
            for f in fix_lanes
            if f.project == slug
            and (f.decision == triage.decision or f.card_number == card.number)
            and f.planning_started_at >= triage.at
        ]
        stage = mine[-1].stage if mine else None
        record = store.lane(slug, card.number)
        folded = record is not None and record.folded_at is not None
        reverted = (
            folded
            and record is not None
            and record.tip is not None
            and self.runtime.reverted(live.project.path, record.tip)
        )
        name = lane_name(card.number, card.title)
        pattern = re.compile(rf"(?<!\d)#{card.number}(?!\d)|{re.escape(name)}")
        filed = any(
            d.kind == DocumentKind.SUGGESTION
            and not d.archived
            and d.found_by is not None
            and pattern.search(d.found_by) is not None
            for d in live.index.documents
        )
        words = "; ".join(
            part
            for part in [
                f"the dial's fix lane is {stage.value}" if stage is not None else None,
                "folded" if folded else None,
                "the fold was reverted" if reverted else None,
                "a defect was filed against it" if filed else None,
            ]
            if part
        ) or "nothing has been built on it yet"
        return Fate(
            planned=stage is not None,
            started=stage is not None and stage not in (FixStage.PLANNING,),
            folded=folded,
            reverted=bool(reverted),
            defect_filed_against=filed,
            stage=stage.value if stage is not None else None,
            words=words,
        )

    def fixes(self, slug: str | None) -> Fixes:
        store = self.live.store
        reports: list[FixReport] = []
        for fix in store.fix_lanes(slug):
            live = self.live.projects.get(fix.project)
            card = store.card(fix.project, fix.card_number)
            if live is None or card is None:
                continue
            document = document_of(card, live.index)
            record = store.lane(fix.project, fix.card_number)
            name = lane_name(card.number, card.title)
            pattern = re.compile(rf"(?<!\d)#{card.number}(?!\d)|{re.escape(name)}")
            filed = any(
                d.kind == DocumentKind.SUGGESTION
                and not d.archived
                and d.found_by is not None
                and pattern.search(d.found_by) is not None
                for d in live.index.documents
            )
            reports.append(
                FixReport(
                    project=fix.project,
                    card_number=card.number,
                    title=card.title,
                    stage=fix.stage,
                    folded=fix.stage == FixStage.FOLDED
                    or (record is not None and record.folded_at is not None),
                    reviewed=has_row(card, RowKind.REVIEW),
                    stopped_to_ask=has_row(card, RowKind.ASK)
                    or any(
                        e.kind == HookKind.STOP and is_question(e.message)
                        for e in store.hook_events(fix.project, card.number)
                    ),
                    defect_filed_against=filed,
                    fold_reverted=record is not None
                    and record.tip is not None
                    and record.folded_at is not None
                    and self.runtime.reverted(live.project.path, record.tip),
                    class_closer=_class_closer(document),
                )
            )
        return Fixes(
            dial=store.dial(),
            lanes=reports,
            rail_now=self._rail_now(),
            rail_at_first_on=store.rail_at_on(),
            waiting=self.waiting(slug),
            decisions=self.decisions(slug),
        )
