"""The doors: Start, Answer, Watch, Look, Discuss, Resume, Stop, the owner's
reading of a signal, and a session's close. Each opens through the runtime,
proves its effect by evidence, and fails loudly by name (INTENT.md lesson
5); none is a silent no-op. Every door writes what it did on the card.
"""

from pathlib import Path

from api.loops import Loops
from board.brief import lane_name, render
from board.lane import HANDS_ON
from board.signals import GRAMMAR, read_or_decline, where_after
from domain.audit import AuditKind
from domain.board import CardDetail
from domain.card import Actor, Place
from domain.column import Column
from domain.gate import Gate
from domain.lane import DoorResult, LaneRecord, LaneState
from domain.launch import LaunchVerdict, Start
from domain.row import Row, RowKind
from domain.window import WindowKind
from infrastructure import clock
from infrastructure.live import Live
from runtime.service import Runtime
from runtime.windows import WindowRefused

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_EFFORT = Gate.XHIGH
"""Talking a card through is thinking work, whatever the build gate says (0.1's rule)."""


class DoorRefused(Exception):
    """The door does not open, and the message says why by name. Nothing changed."""


class DoorFailed(Exception):
    """The door was opened and the machine did not do what it should; the
    message carries the machine's words."""


def needle_command() -> str:
    return f"uv --directory {REPO_ROOT} run needle"


class Doors:
    def __init__(self, live: Live, runtime: Runtime, loops: Loops):
        self.live = live
        self.runtime = runtime
        self.loops = loops

    def _detail(self, slug: str, number: int) -> CardDetail:
        return self.live.detail(slug, number)

    # ── Start ──────────────────────────────────────────────────────────

    def brief_for_lane(self, detail: CardDetail, slug: str, *, overrode: str | None) -> str:
        project = self.live.projects[slug].project
        card = detail.card
        gate = detail.summary.gate
        needle = needle_command()
        text = render(detail, project) + f"\n\nexecute #{card.number}"
        if overrode:
            text += (
                f"\n\nLANE COLLISION OVERRIDDEN by the owner: {overrode} Another lane has hands "
                "on those files; you were started anyway with that in front of him. Leave those "
                "files to that lane unless your plan actually changes them, and expect to "
                "re-verify them at the fold."
            )
        text += (
            f"\n\nYou were launched at {gate.value if gate else 'the default'} from the card's "
            "gate; the launch is the owner's effort-gate confirmation — do not stop to ask."
            f"\n\nYour lane is the worktree named {lane_name(card.number, card.title)} under "
            f"{project.path}/.claude/worktrees/; you are in it. Work and commit there. The fold "
            "is a fast-forward push to origin/develop from this worktree, never a local merge: "
            f"`{needle} fold` (add `--main` at a slice close to promote main)."
            "\n\nWrite back to the card through the `needle` command line, never by editing a "
            "file, so the owner and the next session read the same true state:"
            f"\n  {needle} card {slug} {card.number}            # this brief"
            f'\n  {needle} row {slug} {card.number} <KIND> "…"   # one row: DELIVERED, WATCH, '
            "REVIEW, WAITS, RULING"
            f'\n  {needle} close {slug} {card.number} --delivered "what the owner now has" '
            f'--watch "<signal>" --review docs/reviews/<file>.md'
            f"\n\nThe close is your whole job: the review record under docs/reviews/, the plan "
            "archived to docs/plans/done/, the fold, then `needle close`. A WATCH row names the "
            "signal that will say the work delivered, and without one the card cannot enter "
            f"Executed. Its grammar: {GRAMMAR}"
            "\n\nTo ask the owner something, end your turn with the question; the board shows it "
            "on the card and his answer resumes you."
        )
        return text

    def start(self, slug: str, number: int, *, anyway: bool) -> DoorResult:
        detail = self._detail(slug, number)
        doors = detail.doors
        project = self.live.projects[slug].project
        if not doors.start.offered:
            if anyway and doors.start_anyway.offered:
                pass
            else:
                raise DoorRefused(doors.start.why)
        overrode = (
            doors.collision.sentence
            if anyway and doors.collision is not None and not doors.start.offered
            else None
        )
        gate = detail.summary.gate
        assert gate is not None
        card = detail.card
        name = lane_name(card.number, card.title)
        brief = self.brief_for_lane(detail, slug, overrode=overrode)
        self.live.store.forget_lane(slug, number)
        launch = self.runtime.start(
            Start(repo=project.path, card=name, brief=brief, effort=gate, from_slot=None)
        )
        if launch.verdict != LaunchVerdict.ALIVE or launch.session is None:
            tried = "; ".join(
                f"{a.rung.slot}: {a.verdict.value}" + (f" — {a.reason}" if a.reason else "")
                for a in launch.attempts
            )
            words = f"Start failed: {launch.reason}" + (f" ({tried})" if tried else "")
            self.live.note(slug, number, AuditKind.STARTED, Actor.OWNER, words)
            raise DoorFailed(words)
        session = launch.session
        now = clock.now()
        path = session.worktree or f"{project.path}/.claude/worktrees/{name}"
        self.live.store.record_lane(
            LaneRecord(
                project=slug,
                card_number=number,
                name=name,
                path=path,
                branch=None,
                birth=None,
                tip=None,
                first_seen=now,
                last_seen=now,
                gone_at=None,
                folded_at=None,
                trunk_synced_at=None,
                main_synced_at=None,
            )
        )
        placement = launch.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else session.slot
        said = f"Started {session.short_id}, {where}, at {gate.value}, in {name}"
        said += f", in {launch.scope}" if launch.scope else f" ({launch.reason})"
        if overrode:
            said += f"; collision overridden: {overrode}"
        self.live.note(slug, number, AuditKind.STARTED, Actor.OWNER, said)
        self.live.move(
            slug,
            number,
            Place(column=Column.EXECUTING, group=None, position=0),
            actor=Actor.MACHINE,
            detail=f"hands on: {session.short_id} on {session.slot} in {name}",
        )
        self.loops.reconcile_now()
        return DoorResult(door="start", said=said)

    # ── the doors on a lane ────────────────────────────────────────────

    def _lane_session(self, detail: CardDetail, door: str):
        lane = detail.lane
        if lane is None or lane.session is None:
            raise DoorRefused(getattr(detail.doors, door).why)
        return lane, lane.session

    def answer(self, slug: str, number: int, text: str) -> DoorResult:
        text = text.strip()
        if not text:
            raise DoorRefused("An empty answer resumes nothing.")
        detail = self._detail(slug, number)
        if not detail.doors.answer.offered:
            raise DoorRefused(detail.doors.answer.why)
        lane, session = self._lane_session(detail, "answer")
        result = self.runtime.resume(session.short_id, prompt=text, card=lane.name)
        if result.verdict != LaunchVerdict.ALIVE or result.session is None:
            words = f"The answer did not resume the lane: {result.reason}"
            self.live.note(slug, number, AuditKind.ANSWERED, Actor.OWNER, words)
            raise DoorFailed(words)
        placement = result.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else result.session.slot
        said = f"Answered, and the lane resumed as {result.session.short_id} ({where}): {text}"
        self.live.note(slug, number, AuditKind.ANSWERED, Actor.OWNER, said)
        self.loops.reconcile_now()
        return DoorResult(door="answer", said=said)

    def watch(self, slug: str, number: int) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.watch.offered:
            raise DoorRefused(detail.doors.watch.why)
        _, session = self._lane_session(detail, "watch")
        try:
            opened = self.runtime.window(session.short_id, WindowKind.WATCH)
        except WindowRefused as refusal:
            raise DoorFailed(f"Watch did not open: {refusal}") from refusal
        self.loops.reconcile_now()
        return DoorResult(
            door="watch",
            said=(
                f"Window {opened.window.app_id} opened into {session.short_id}; "
                "closing it ends nothing."
            ),
        )

    def look(self, slug: str, number: int) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.look.offered:
            raise DoorRefused(detail.doors.look.why)
        _, session = self._lane_session(detail, "look")
        try:
            opened = self.runtime.window(session.short_id, WindowKind.LOOK)
        except WindowRefused as refusal:
            raise DoorFailed(f"Look did not open: {refusal}") from refusal
        said = f"Window {opened.window.app_id} opened. Its first line: {opened.banner}"
        self.live.note(slug, number, AuditKind.DISCUSSED, Actor.OWNER, f"Looked: {said}")
        return DoorResult(door="look", said=said)

    def resume(self, slug: str, number: int) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.resume.offered:
            raise DoorRefused(detail.doors.resume.why)
        lane, session = self._lane_session(detail, "resume")
        result = self.runtime.resume(session.short_id, prompt=None, card=lane.name)
        if result.verdict != LaunchVerdict.ALIVE or result.session is None:
            words = f"Resume failed: {result.reason}"
            self.live.note(slug, number, AuditKind.STARTED, Actor.OWNER, words)
            raise DoorFailed(words)
        placement = result.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else result.session.slot
        said = f"Resumed as {result.session.short_id}, {where}"
        self.live.note(slug, number, AuditKind.STARTED, Actor.OWNER, said)
        self.loops.reconcile_now()
        return DoorResult(door="resume", said=said)

    def stop(self, slug: str, number: int) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.stop.offered:
            raise DoorRefused(detail.doors.stop.why)
        _, session = self._lane_session(detail, "stop")
        stopped = self.runtime.stop(session.short_id)
        if not stopped.gone:
            words = (
                f"Stop did not end {session.short_id} within {stopped.seconds:.0f} s: "
                f"{stopped.words}"
            )
            self.live.note(slug, number, AuditKind.STOPPED, Actor.OWNER, words)
            raise DoorFailed(words)
        self.live.note(
            slug,
            number,
            AuditKind.STOPPED,
            Actor.OWNER,
            f"Stopped {session.short_id}: {stopped.words}",
        )
        self.loops.reconcile_now()
        after = self.live.card(slug, number)
        return DoorResult(
            door="stop",
            said=(
                f"Stopped {session.short_id} after {stopped.seconds:.1f} s; "
                f"the card is in {after.place.column}."
            ),
        )

    def discuss(self, slug: str, number: int) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.discuss.offered:
            raise DoorRefused(detail.doors.discuss.why)
        project = self.live.projects[slug].project
        card = detail.card
        needle = needle_command()
        brief = render(detail, project) + (
            "\n\n(Opened from the card's Discuss door: the owner wants to talk this card "
            "through before deciding anything. Your FIRST message is two or three short plain "
            "sentences: what this card makes true in your own words, then what he wants to "
            "know — no headers, no file paths, no restating the brief he can see on the card. "
            "Answer his questions and challenge the card where it deserves it. If he says go, "
            f"launch the lane exactly as the board's Start button would: `{needle} start-card "
            f"{slug} {card.number}` (add `--anyway` only if the board reports a lane collision "
            "and he has read its reason and says start regardless) — his go IS the effort-gate "
            "confirmation. Then tell him in one sentence that the lane runs in the background "
            "and this window may close: execution never rides this conversation.)"
        )
        try:
            opened, session_id, placement = self.runtime.discuss(
                repo=project.path,
                card=lane_name(card.number, card.title),
                brief=brief,
                effort=DISCUSS_EFFORT,
                what=f"Discussing #{card.number}",
            )
        except WindowRefused as refusal:
            raise DoorFailed(f"Discuss did not open: {refusal}") from refusal
        self.live.store.record_discussion(slug, number, session_id, placement.slot, clock.now())
        said = (
            f"Discussing in {opened.window.app_id}, {placement.model.value} on {placement.slot}; "
            "a conversation, never hands on the tree."
        )
        self.live.note(slug, number, AuditKind.DISCUSSED, Actor.OWNER, said)
        self.loops.reconcile_now()
        return DoorResult(door="discuss", said=said)

    # ── the owner reads a signal ───────────────────────────────────────

    def signal(self, slug: str, number: int, *, delivered: bool) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.signal.offered or detail.signal is None:
            raise DoorRefused(detail.doors.signal.why)
        now = clock.now()
        words = f"the owner read it as {'delivered' if delivered else 'not delivered'}"
        self.live.store.record_reading(slug, number, now, delivered, words, Actor.OWNER)
        column, reason = where_after(detail.signal, delivered, now)
        if column is None:
            column, reason = Column.DECISION_MOMENT, "the owner read the signal as not delivered"
        self.live.move(
            slug,
            number,
            Place(column=column, group=None, position=0),
            actor=Actor.OWNER,
            detail=reason,
        )
        return DoorResult(
            door="signal", said=f"Read as {words.split(' as ')[1]}; moved to {column}."
        )

    # ── a session's close ──────────────────────────────────────────────

    def close(
        self,
        slug: str,
        number: int,
        *,
        delivered: str,
        watch: str,
        review: str | None,
        column: Column | None,
        actor: Actor,
    ) -> DoorResult:
        """Rows and the move in one act, so the card never says half of what
        happened. Executed needs the plan archived and a readable signal."""
        signal, why = read_or_decline(watch)
        if signal is None:
            raise DoorRefused(f"The WATCH row names no signal: {why}")
        live = self.live.projects[slug]
        self.live.rescan(slug)
        card = self.live.card(slug, number)
        target = column or Column.EXECUTED
        if target == Column.EXECUTED and not (card.link is not None and card.link.archived):
            raise DoorRefused(
                f"#{number} cannot enter Executed while its plan is live; archive it to "
                "docs/plans/done/ first, or name another column."
            )
        self.live.add_row(slug, number, Row(kind=RowKind.DELIVERED, text=delivered.strip()), actor)
        self.live.add_row(slug, number, Row(kind=RowKind.WATCH, text=watch.strip()), actor)
        if review:
            self.live.add_row(slug, number, Row(kind=RowKind.REVIEW, text=review.strip()), actor)
        lane = live.snapshot.lanes.get(number) if live.snapshot else None
        hands = lane is not None and lane.state in HANDS_ON and lane.state != LaneState.NONE
        self.live.move(
            slug,
            number,
            Place(column=target, group=None, position=0),
            actor=actor,
            detail="closed by the session: DELIVERED and WATCH written"
            + (" while its own lane still holds the tree" if hands else ""),
        )
        return DoorResult(
            door="close",
            said=f"#{number} closed into {target}: DELIVERED, WATCH"
            + (", REVIEW" if review else "")
            + f" written; the signal is read {signal.kind.value} {signal.target} by {signal.due}.",
        )
