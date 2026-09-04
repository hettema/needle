"""The doors: Start, Answer, Watch, Look, Discuss, Idea, Resume, Stop, the
owner's reading of a signal, a reading session's finding, and a session's
close. Each opens through the
runtime, proves its effect by evidence, and fails loudly by name (INTENT.md
lesson 5); none is a silent no-op. Every door writes what it did on the
card — Idea, which is about no card yet, on the board's record of
conversations.
"""

import uuid
from pathlib import Path

from api.loops import Loops
from board.brief import lane_name, needle_command, neighbours_text, render, watercooler_text
from board.handouts import handouts_row
from board.lane import HANDS_ON
from board.signals import GRAMMAR, read_or_decline, where_after, where_after_finding
from domain.audit import AuditKind
from domain.board import CardDetail
from domain.card import Actor, Place
from domain.column import Column
from domain.evidence import Evidence, EvidenceState
from domain.gate import Gate
from domain.lane import DoorResult, Lane, LaneRecord, LaneState
from domain.launch import LaunchVerdict, Start
from domain.project import Project
from domain.row import Row, RowKind
from domain.signal import Finding
from domain.verdict import EvidenceClass, VerdictsRuled
from domain.window import WindowKind
from infrastructure import clock
from infrastructure.live import WATERCOOLER_SHOWN, Live
from infrastructure.store import StoreRefusal
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


def idea_brief(project: Project, session_id: str, first_line: str | None, today: str) -> str:
    """What an idea conversation opens with (plan 07, item 1): whose idea it
    is, that the corpus is the only way in, and that the document names this
    conversation so the card it becomes says where it was born."""
    short = session_id[:8]
    asked = (
        f'The owner typed this into the door: "{first_line.strip()}" — that is his opening '
        "line; answer it."
        if first_line and first_line.strip()
        else "He typed nothing into the door: ask him, in one line, what is on his mind."
    )
    return (
        f"An idea from the owner, opened from the board's Idea door on {project.name} "
        f"({project.path}), {today}. Nothing is a card yet; this window is a conversation "
        "about nothing yet, never hands on any tree.\n\n"
        "The corpus is the only way in. What this conversation produces becomes a card only "
        "by being written into it: a plan into docs/plans/ (with an `**Effort gate:**` line "
        'and a "done means" per item, in the shape docs/plans/README.md describes), or a '
        "suggestion into docs/slice-suggestions/ (with its `**Kind:** idea` or `**Kind:** "
        "defect` line on the second line). Head the document with\n"
        f"  **Found by:** the owner, from the board's Idea door on {today} (conversation {short})\n"
        "so the card it becomes says it was born from this conversation. Write nothing else "
        "to the repository. Commit the document in this checkout on develop with a body that "
        "says what prompted it, and push it (`git push origin develop`); the board cards the "
        "file the moment it lands.\n\n"
        "Your FIRST message is two or three short plain sentences — no headers, no file "
        f"paths. {asked} Challenge the idea where it deserves it, and say when it is already "
        "in the corpus under another name."
    )


def plan_skill(project_path: Path) -> str | None:
    """The project's own plan-writing skill, when its `.claude/skills/` has
    one (Hello Revenue's is `hr-plan-write`); None means the shape in
    docs/plans/README.md is the plan shape."""
    skills = project_path / ".claude" / "skills"
    if not skills.is_dir():
        return None
    for found in sorted(skills.iterdir()):
        if found.is_dir() and "plan" in found.name and "write" in found.name:
            return f"/{found.name}"
    return None


def plan_brief(project: Project, details: list[CardDetail], skill: str | None, today: str) -> str:
    """What a plan-writing conversation opens with (plan 06, item 5): the
    suggestions as their cards read, the plan shape to write in, the head
    line that lets the board follow the plan, and what to write and what not.
    The session moves the carried suggestions to done/ itself: the board reads
    the repository and never writes into it."""
    several = len(details) > 1
    paths = [d.summary.document_path for d in details if d.summary.document_path]
    shape = (
        f"use the project's own plan-writing skill, {skill}"
        if skill
        else "the shape docs/plans/README.md describes: a `**Status:**` line, a `**Written:**` "
        "line, an `**Effort gate:** <low|medium|high|xhigh> — <why>` line, `**Sequencing:**` "
        "when it depends on another plan, an Intent section, and numbered items each ending "
        'with what "done means" as a behaviour someone can observe'
    )
    cards = "\n\n".join(render(d, project) for d in details)
    return (
        f"A plan to write, opened from the board's Plan door on {project.name} ({project.path}), "
        f"{today}: "
        + (
            f"one plan that carries these {len(details)} suggestions together, as one slice's "
            "worth of work."
            if several
            else "the plan for this suggestion."
        )
        + " This window is a conversation in the project's checkout, never hands on any "
        "tree.\n\n"
        + cards
        + "\n\nWrite the plan into docs/plans/ in the project's plan shape — "
        + shape
        + ". Head it with a `**Carries:**` line naming "
        + ("each suggestion's path:\n" if several else "the suggestion's path:\n")
        + "".join(f"  {p}\n" for p in paths)
        + "That line is how the board follows the plan: when the plan lands, "
        + (
            f"#{details[0].card.number} becomes the plan's card (same number, same history) and "
            "the other cards fold under it"
            if several
            else f"#{details[0].card.number} becomes the plan's card, same number and history"
        )
        + ", so nothing is retyped and no second card is born. In the same commit move each "
        "carried suggestion to docs/slice-suggestions/done/ and add a `**Carried by:** <the "
        "plan's path>` line under its title; the board reads the repository and never writes "
        "into it. Ask the owner in this window where the intent is unclear; he holds the "
        "market and the priorities, you hold the code. Write nothing else to the repository. "
        "Commit the plan and the moved suggestions in this checkout on develop with a body "
        "that says what prompted them, and push (`git push origin develop`); the board "
        "follows the plan the moment it lands.\n\n"
        "Your FIRST message is two or three short plain sentences — no headers, no file "
        "paths: what you read the "
        + ("suggestions" if several else "suggestion")
        + " as asking for, and the one question that most sharpens the intent."
    )


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
        snapshot = self.live.projects[slug].snapshot
        lanes = snapshot.lanes if snapshot is not None else {}
        titles = {c.number: c.title for c in self.live.store.cards(slug)}
        text += (
            "\n\nOther lanes with hands on this project right now:\n"
            + neighbours_text(lanes, titles, card.number)
            + "\nLeave those files to their lanes unless your plan names them. If you must "
            "touch one, say so in the watercooler first; the board re-reads every lane's "
            "actual edits on every read and marks two lanes in the same file as colliding "
            "on both cards — and tells you, inside this session beside a tool result, within "
            "a minute, when your edits collide with another lane's and when another lane or "
            "the board says something on the watercooler; you need not poll for either."
            "\n\nThe watercooler — what the lanes on this project say to each other; read it "
            f"now, and once more before your fold (`{needle} fold` shows it):\n"
            + watercooler_text(self.live.store.watercooler(slug, limit=WATERCOOLER_SHOWN))
            + "\nSay something when you touch a file outside your footprint or change a "
            "seam another lane depends on:"
            f'\n  {needle} watercooler {slug} {card.number} "…"'
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
            evidence=Evidence.HANDS_ON,
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
        lane, session = self._lane_session(detail, "watch")
        if lane.window_open:
            try:
                focused = self.runtime.focus(session.short_id)
            except WindowRefused as refusal:
                raise DoorFailed(f"Focus did not land: {refusal}") from refusal
            return DoorResult(
                door="watch",
                said=(
                    f"Focused {focused.window.app_id}; the compositor reports "
                    f"{focused.app_id} active."
                ),
            )
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

    def idea(self, slug: str, first_line: str | None) -> DoorResult:
        """A conversation about nothing yet, in the project's checkout (plan
        07, item 1): the session id is chosen here so the brief can name it,
        and the document the session writes names it back."""
        project = self.live.projects[slug].project
        session_id = str(uuid.uuid4())
        today = clock.now().date().isoformat()
        brief = idea_brief(project, session_id, first_line, today)
        try:
            opened, session_id, placement = self.runtime.discuss(
                repo=project.path,
                card=slug,
                brief=brief,
                effort=DISCUSS_EFFORT,
                what=f"An idea for {project.name}",
                kind=WindowKind.IDEA,
                session_id=session_id,
            )
        except WindowRefused as refusal:
            raise DoorFailed(f"Idea did not open: {refusal}") from refusal
        self.live.store.record_discussion(
            slug, None, session_id, placement.slot, clock.now(), kind=WindowKind.IDEA
        )
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="idea",
            said=(
                f"Talking in {opened.window.app_id}, {placement.model.value} on "
                f"{placement.slot}; a conversation about nothing yet ({session_id[:8]}), never "
                "hands on a tree. What it writes into the corpus becomes a card."
            ),
        )

    # ── Plan ───────────────────────────────────────────────────────────

    def plan(self, slug: str, numbers: list[int]) -> DoorResult:
        """A plan-writing conversation for one suggestion or several (plan
        06, item 5), in the project's checkout like an Idea: the plan it
        writes cites the suggestions, and the watcher then makes the first
        one's card the plan's and folds the rest under it."""
        if not numbers:
            raise DoorRefused("Plan needs at least one suggestion card.")
        details = [self._detail(slug, n) for n in numbers]
        for detail in details:
            if not detail.doors.plan.offered:
                raise DoorRefused(f"#{detail.card.number}: {detail.doors.plan.why}")
        project = self.live.projects[slug].project
        skill = plan_skill(Path(project.path))
        brief = plan_brief(project, details, skill, clock.now().date().isoformat())
        numbered = ", ".join(f"#{n}" for n in numbers)
        what = f"Planning {numbered}" + (" together" if len(numbers) > 1 else "")
        card = (
            lane_name(details[0].card.number, details[0].card.title)
            if len(numbers) == 1
            else "cards-" + "-".join(str(n) for n in numbers)
        )
        try:
            opened, session_id, placement = self.runtime.discuss(
                repo=project.path,
                card=card,
                brief=brief,
                effort=DISCUSS_EFFORT,
                what=what,
                kind=WindowKind.PLAN,
            )
        except WindowRefused as refusal:
            raise DoorFailed(f"Plan did not open: {refusal}") from refusal
        now = clock.now()
        said = (
            f"Planning {numbered} in {opened.window.app_id}, {placement.model.value} on "
            f"{placement.slot}; the plan it writes carries "
            + ("this card" if len(numbers) == 1 else "these cards, the first keeping its number")
            + "."
        )
        for number in numbers:
            self.live.store.record_discussion(
                slug, number, session_id, placement.slot, now, kind=WindowKind.PLAN
            )
            self.live.note(slug, number, AuditKind.DISCUSSED, Actor.OWNER, said)
        self.loops.reconcile_now()
        return DoorResult(door="plan", said=said)

    # ── the owner reads a signal ───────────────────────────────────────

    def signal(self, slug: str, number: int, *, delivered: bool) -> DoorResult:
        detail = self._detail(slug, number)
        if not detail.doors.signal.offered or detail.signal is None:
            raise DoorRefused(detail.doors.signal.why)
        now = clock.now()
        words = f"the owner read it as {'delivered' if delivered else 'not delivered'}"
        self.live.store.record_reading(slug, number, now, delivered, words, Actor.OWNER)
        landing = where_after(detail.signal, delivered, now)
        column = landing.column or Column.DECISION_MOMENT
        reason = landing.reason if landing.column else "the owner read the signal as not delivered"
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

    # ── the owner rules on a verdict ───────────────────────────────────

    def accept(self, slug: str, number: int) -> DoorResult:
        """The owner accepts the card's verdict: the machine moves the card
        where it said, with the verdict's reason on the history row and the
        owner named as the acceptor; a verdict that stays is his word that
        the card belongs where it is (plan 05, item 2)."""
        detail = self._detail(slug, number)
        verdict = detail.verdict
        if verdict is None:
            raise DoorRefused(
                f"#{number} carries no verdict the board can act on: {detail.verdict_note}"
            )
        card = detail.card
        to = (
            Place(column=verdict.to, group=None, position=0)
            if verdict.to is not None and verdict.to != card.place.column
            else None
        )
        said = f"accepted the verdict: {verdict.evidence_class.value} — {verdict.evidence}"
        replace = to is None and detail.summary.standing.state == EvidenceState.DOUBTED
        after = self.live.rule_on_verdict(
            slug, number, accepted=True, word=None, to=to, replace=replace, said=said
        )
        where = (
            f"moved to {after.place.column}" if to is not None else f"stays in {after.place.column}"
        )
        return DoorResult(
            door="accept",
            said=f"#{number} {where}: {verdict.evidence_class.value} — {verdict.evidence}",
        )

    def overturn(self, slug: str, number: int, word: str) -> DoorResult:
        """The owner overturns the card's verdict: the card stays and his word
        is recorded on it in a RULED row."""
        word = word.strip()
        if not word:
            raise DoorRefused("An overturn without a word records nothing; say why.")
        detail = self._detail(slug, number)
        if detail.verdict is None:
            raise DoorRefused(
                f"#{number} carries no verdict the board can act on: {detail.verdict_note}"
            )
        after = self.live.rule_on_verdict(
            slug,
            number,
            accepted=False,
            word=word,
            to=None,
            replace=False,
            said=f"overturned the verdict: {word}",
        )
        return DoorResult(
            door="overturn", said=f"#{number} stays in {after.place.column}; your word: {word}"
        )

    def accept_class(self, slug: str, evidence_class: EvidenceClass) -> VerdictsRuled:
        """Accept every unread verdict in one class, each as its own act; a
        card the store refuses stays with the refusal's words in the answer."""
        board = self.live.board(slug)
        accepted = 0
        refused: list[str] = []
        for line in board.verdicts:
            if line.verdict.evidence_class != evidence_class:
                continue
            try:
                self.accept(slug, line.number)
                accepted += 1
            except (DoorRefused, StoreRefusal) as why:
                refused.append(f"#{line.number}: {why}")
        return VerdictsRuled(evidence_class=evidence_class, accepted=accepted, refused=refused)

    # ── a reading session's finding ────────────────────────────────────

    def reading(
        self,
        slug: str,
        number: int,
        *,
        finding: Finding,
        words: str,
        watch: str | None,
    ) -> DoorResult:
        """A reading session's finding (plan 09, item 1), in one act: the
        replacement WATCH row when the measure was wrong (item 2), the
        reading in the session's words, the end of the reading session's
        record, and the move the finding implies. Delivered goes to Done;
        not delivered to Decision moment now; cannot tell stays and asks the
        owner with the words, or lands in Decision moment once past due."""
        words = words.strip()
        if not words:
            raise DoorRefused("A finding without its evidence records nothing; say what you read.")
        detail = self._detail(slug, number)
        if detail.card.place.column != Column.EXECUTED:
            raise DoorRefused(
                f"#{number} is in {detail.card.place.column}; a reading is of an Executed "
                "card's signal."
            )
        signal = detail.signal
        if signal is None:
            raise DoorRefused(f"#{number}'s WATCH row names no signal: {detail.signal_note}")
        if watch is not None:
            replacement, why = read_or_decline(watch)
            if replacement is None:
                raise DoorRefused(f"The replacement WATCH row names no signal: {why}")
            self.live.add_row(
                slug, number, Row(kind=RowKind.WATCH, text=watch.strip()), Actor.SESSION
            )
            signal = replacement
        now = clock.now()
        self.live.store.record_reading(slug, number, now, finding.delivered, words, Actor.SESSION)
        for open_reading in self.live.store.reading_sessions(slug, open_only=True):
            if open_reading.card_number == number:
                self.live.store.end_reading_session(open_reading.id, now)
        self.live.bump()
        landing = where_after_finding(signal, finding, now)
        if landing.column is not None:
            self.live.move(
                slug,
                number,
                Place(column=landing.column, group=None, position=0),
                actor=Actor.MACHINE,
                detail=landing.reason,
                evidence=landing.evidence,
            )
            where = f"moved to {landing.column}"
        elif finding == Finding.CANNOT_TELL:
            where = "stays in Executed; the owner is asked with your words"
        else:
            where = f"stays in Executed ({landing.reason})"
        return DoorResult(
            door="reading",
            said=f"#{number} read as {finding.value.replace('-', ' ')}; {where}"
            + ("; the WATCH row replaced" if watch is not None else "")
            + ".",
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
        lane = live.snapshot.lanes.get(number) if live.snapshot else None
        # Read before any row is written: a transcript that cannot be read
        # must refuse the whole close, never leave DELIVERED on a card that
        # did not move (review pass 2).
        handed = self._handed_out(slug, number, lane)
        self.live.add_row(slug, number, Row(kind=RowKind.DELIVERED, text=delivered.strip()), actor)
        self.live.add_row(slug, number, Row(kind=RowKind.WATCH, text=watch.strip()), actor)
        if review:
            self.live.add_row(slug, number, Row(kind=RowKind.REVIEW, text=review.strip()), actor)
        if handed is not None:
            self.live.add_row(slug, number, Row(kind=RowKind.HANDED_OUT, text=handed), actor)
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
            + (", HANDED OUT" if handed is not None else "")
            + f" written; the signal is read {signal.kind.value} {signal.target} by {signal.due}.",
        )

    def _handed_out(self, slug: str, number: int, lane: Lane | None) -> str | None:
        """The HANDED OUT row (plan 12, item 3): what the plan named against
        what the lane's transcripts show it dispatched. The lane is found by
        the board's own record of it, else the loop's last read; a card
        whose plan named nothing and whose lane dispatched nothing gets no
        row."""
        named = self._detail(slug, number).handouts.named
        record = self.live.store.lane(slug, number)
        where = record.path if record is not None else (lane.path if lane is not None else None)
        if where is None:
            return handouts_row(named, None, None)
        return handouts_row(named, self.runtime.dispatches(where), where)
