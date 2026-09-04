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
from datetime import datetime
from pathlib import Path

from api.doors import REPO_ROOT, DoorFailed, DoorRefused, Doors, plan_skill
from api.loops import Loops, Tended
from board.assemble import document_of
from board.brief import lane_name, planning_brief, planning_name
from board.dial import (
    LIVE_STAGES,
    Candidate,
    is_quiet,
    rail_count,
    rail_defects,
    running,
    why_not_eligible,
)
from board.lane import has_row, is_question
from domain.audit import AuditKind
from domain.card import Actor, Card
from domain.dial import Dial as DialSetting
from domain.dial import DialState, Fixes, FixLane, FixReport, FixStage
from domain.document import DocumentKind
from domain.gate import Gate
from domain.hook import HookKind
from domain.lane import LaneState
from domain.launch import LaunchVerdict, WindowlessStart
from domain.row import RowKind
from domain.signal import SessionWork
from infrastructure import clock
from infrastructure.live import Live, LiveProject
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
        return self.live.dial_state()

    def _rail_now(self):
        return [
            rail_count(slug, self.live.store.cards(slug), live.index)
            for slug, live in self.live.projects.items()
        ]

    # ── the beat ───────────────────────────────────────────────────────

    def tick_now(self) -> None:
        """Follow every fix lane the dial has open — a plan that landed to
        its Start, a lane that folded or ended to its end, a planning session
        that died to the card — whether or not the dial is still on; then,
        with it on and room under the number, take the next defect."""
        self._follow()
        setting = self.live.store.dial()
        if not setting.on:
            return
        self._take_next(setting)

    def _take_next(self, setting: DialSetting) -> None:
        store = self.live.store
        fix_lanes = store.fix_lanes()
        if running(fix_lanes) >= setting.lanes:
            return
        lanes_by_project = {
            slug: live.snapshot.lanes
            for slug, live in self.live.projects.items()
            if live.snapshot is not None
        }
        quiet = is_quiet(lanes_by_project)
        candidates: list[Candidate] = []
        for slug, live in self.live.projects.items():
            snapshot = live.snapshot
            if snapshot is None:
                continue  # the machine has not been read for this project yet
            readings = store.last_readings(slug)
            planning = store.open_windowless_sessions(slug, SessionWork.PLANNING)
            ran = {f.card_number for f in fix_lanes if f.project == slug}
            for card, document in rail_defects(store.cards(slug), live.index):
                why = why_not_eligible(
                    card,
                    document,
                    last=readings.get(card.number),
                    lane=snapshot.lanes.get(card.number),
                    planning_open=card.number in planning,
                    ran_before=card.number in ran,
                )
                if why is not None:
                    continue
                doors = snapshot.doors.get(card.number)
                if doors is None or doors.placement is None:
                    continue  # nowhere to run: the card would say so on Start too
                candidates.append(Candidate(project=slug, card=card, document=document))
        for candidate in sorted(candidates, key=lambda c: c.age_key):
            live = self.live.projects[candidate.project]
            if self._own_board(live) and not quiet:
                continue  # a fold on the board restarts the service under every running lane
            self._plan(live, candidate)
            return

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
        fix = self.live.store.open_fix_lane(slug, card.number, now)
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
                    without="without a plan",
                )

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
        if not detail.doors.start.offered:
            why = detail.doors.start.why
            if fix.note != why:
                store.stage_fix_lane(fix.id, FixStage.PLANNED, fix.planned_at or now, note=why)
                self.live.note(
                    slug, card.number, AuditKind.DIAL, Actor.MACHINE, f"Start waits: {why}"
                )
            return
        try:
            result = self.doors.start(slug, card.number, anyway=False, actor=Actor.MACHINE)
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

    # ── the loop, counted (item 6) ─────────────────────────────────────

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
        )
