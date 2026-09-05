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
from board.assemble import is_trigger_card
from board.brief import (
    corpus_lane_name,
    filing_rule,
    lane_name,
    lane_path,
    needle_command,
    neighbours_text,
    render,
    watercooler_text,
)
from board.handouts import handouts_row
from board.lane import HANDS_ON
from board.signals import GRAMMAR, read_or_decline, where_after, where_after_finding
from board.triage import routing_now, triaged_row
from domain.audit import AuditKind
from domain.board import CardDetail
from domain.card import Actor, Place
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.evidence import Evidence, EvidenceState
from domain.gate import Gate
from domain.lane import CollisionVerdict, DoorResult, Lane, LaneRecord, LaneState
from domain.launch import LaunchVerdict, Start
from domain.project import Project
from domain.row import Row, RowKind
from domain.signal import Finding, SessionWork
from domain.triage import CorpusLane, CorpusLaneKind, Direction, Routing, TriageResult
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
CORPUS_LANE_EFFORT = Gate.MEDIUM
"""A corpus lane writes what a record already selected: one document edit,
one commit, one push. It is not thinking work — the thinking was the reading
that produced the record, or the owner's own sentence."""
DOCS = "docs/"
"""A lane whose every file is under here shipped no code, and its close
needs no review record (plan 11, item 1)."""


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

    def brief_for_lane(self, detail: CardDetail, slug: str) -> str:
        project = self.live.projects[slug].project
        card = detail.card
        gate = detail.summary.gate
        needle = needle_command()
        text = render(detail, project) + f"\n\nexecute #{card.number}"
        collision = detail.doors.collision
        if collision is not None and collision.verdict == CollisionVerdict.COLLIDES:
            # The session is told what it shares so it rebases early and
            # often; the fold, not a lock, settles it (INTENT.md lesson 4).
            text += (
                f"\n\nSHARED GROUND: {collision.sentence} Rebase onto origin/develop early and "
                "often (`git pull --rebase origin develop`), not only at the fold: the second "
                "to fold rebases, and the full suite on the levelled tree is the judge of what "
                "you share. The files: " + ", ".join(collision.files) + "."
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
            "\n\nWrite back to the card's rows through the `needle` command line, never by "
            "editing the board's own files, so the owner and the next session read the same "
            "true state:"
            f"\n  {needle} card {slug} {card.number}            # this brief"
            f'\n  {needle} row {slug} {card.number} <KIND> "…"   # one row: DELIVERED, WATCH, '
            "REVIEW, WAITS, RULING"
            f'\n  {needle} close {slug} {card.number} --delivered "what the owner now has" '
            f'--watch "<signal>" --review docs/reviews/<file>.md'
            f"\n\nThe close is your whole job: the review record under docs/reviews/, the plan "
            "archived to docs/plans/done/, the fold, then `needle close`. A WATCH row names the "
            "signal that will say the work delivered, and without one the card cannot enter "
            f"Executed. Its grammar: {GRAMMAR}"
            "\nThe close refuses a lane that folded anything outside docs/ unless --review "
            "names a record that exists; a docs-only close passes without one."
            "\n\nYour plan and your review record are your own documents, and the fold carries "
            "them; the card reads both from this worktree as your word. When an item's done-means "
            "holds, end it in your plan with `**Met:** <what shows it>` in the commit that makes "
            "it true, `**Deviated:** <pointer>` when it landed otherwise. Write the review record "
            "pass by pass, each pass appended under `## The passes` as it completes, with its "
            "`**Plan:**` line naming your plan; the card shows the count of items met while you "
            "work and the review loop's pass and findings once every item is met."
            "\n\nThe review runs in rings (CLAUDE.md): a finding inside your change or on its "
            "seams is fixed here and the next pass re-reads; a finding outside it is never "
            "fixed in this lane — "
            + filing_rule(
                f"the lane on card #{card.number}"
                + (f" ({detail.document.path})" if detail.document is not None else "")
                + ", in the review's <lens> pass"
            )
            + "."
            "\n\nTo ask the owner something, end your turn with the question; the board shows it "
            "on the card and his answer resumes you."
        )
        return text

    def start(self, slug: str, number: int, *, actor: Actor = Actor.OWNER) -> DoorResult:
        """Start the card's lane where the rule says. `actor` is whose move
        it is: the owner's click through the page or his terminal, or the
        machine's under the dial — his standing ruling applied by the board
        (plan 11, item 4), which the card's history then says. One door:
        shared ground opens it with the ground in its label, and there is
        nothing left to override (INTENT.md lesson 4)."""
        detail = self._detail(slug, number)
        doors = detail.doors
        project = self.live.projects[slug].project
        if not doors.start.offered:
            raise DoorRefused(doors.start.why)
        shares = (
            doors.collision
            if doors.collision is not None and doors.collision.verdict == CollisionVerdict.COLLIDES
            else None
        )
        gate = detail.summary.gate
        assert gate is not None
        card = detail.card
        name = lane_name(card.number, card.title)
        brief = self.brief_for_lane(detail, slug)
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
            self.live.note(slug, number, AuditKind.STARTED, actor, words)
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
        if actor == Actor.MACHINE:
            said += "; started by the dial"
        if shares is not None:
            said += f"; {shares.sentence[0].lower()}{shares.sentence[1:]}"
        self.live.note(slug, number, AuditKind.STARTED, actor, said)
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
        """The owner's sentence, on a lane or on a parked card. On a lane it
        resumes the session with it, as it always has. On a card with no
        lane at all — a defect a reading put on his pile — it is his durable
        ruling: it lands as the `ANSWERED` row and the board opens a lane
        that makes the corpus say it (plan 59, item 5). Before this, a
        parked `his` defect had no door at all, which is why the pile drained
        at zero for the board's whole life."""
        text = text.strip()
        if not text:
            raise DoorRefused("An empty answer resumes nothing.")
        detail = self._detail(slug, number)
        if not detail.doors.answer.offered:
            raise DoorRefused(detail.doors.answer.why)
        if detail.lane is None or detail.lane.session is None:
            return self._rule_on_a_parked_card(slug, number, text, detail)
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

    def _rule_on_a_parked_card(
        self, slug: str, number: int, text: str, detail: CardDetail
    ) -> DoorResult:
        """His answer on a defect nobody has hands on. The row is written
        first and is the durable thing: every failure after it leaves the row
        standing, the card saying the half-state in words, and the machine
        retrying — so he is never asked the same question twice, whatever
        the lane does next."""
        routed = detail.summary.routing
        if routed is None or routed.state != Routing.TRIAGED_HIS:
            raise DoorRefused(
                f"#{number} is not on your pile: it routes as "
                + (routed.state.value if routed is not None else "nothing to rule on")
                + "."
            )
        said = f"Ruled: {text}"
        self.live.note(slug, number, AuditKind.ANSWERED, Actor.OWNER, said)
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="answer",
            said=(
                f"{said} — the board opens a lane that rewrites the mark citing your ruling; "
                "the card says so until the corpus does."
            ),
        )

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
        """The owner's reading: of an Executed card's signal, which moves the
        card where the reading says; or of a Backlog defect's `Fix: when`
        trigger (plan 11, item 5), which moves nothing — delivered makes the
        defect eligible for the dial."""
        detail = self._detail(slug, number)
        trigger_card = is_trigger_card(detail.card, detail.document)
        signal = detail.trigger if trigger_card else detail.signal
        if not detail.doors.signal.offered or signal is None:
            raise DoorRefused(detail.doors.signal.why)
        now = clock.now()
        words = f"the owner read it as {'delivered' if delivered else 'not delivered'}"
        self.live.store.record_reading(slug, number, now, delivered, words, Actor.OWNER)
        if trigger_card:
            self.live.bump()
            said = (
                "the trigger has fired: the defect is eligible for the dial"
                if delivered
                else "the trigger has not fired: the defect waits"
            )
            return DoorResult(door="signal", said=f"Read as {words.split(' as ')[1]}; {said}.")
        landing = where_after(signal, delivered, now)
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
        trigger_card = is_trigger_card(detail.card, detail.document)
        if detail.card.place.column != Column.EXECUTED and not trigger_card:
            raise DoorRefused(
                f"#{number} is in {detail.card.place.column}; a reading is of an Executed "
                "card's signal, or of a Backlog defect's Fix: when trigger."
            )
        signal = detail.trigger if trigger_card else detail.signal
        if signal is None:
            if trigger_card:
                raise DoorRefused(
                    f"#{number}'s Fix: when line names no trigger: {detail.trigger_note}"
                )
            raise DoorRefused(f"#{number}'s WATCH row names no signal: {detail.signal_note}")
        if watch is not None and trigger_card:
            raise DoorRefused(
                "A trigger lives on the suggestion's Fix: when line, not on a WATCH row; a "
                "wrong measure is changed there."
            )
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
        for open_reading in self.live.store.windowless_sessions(
            slug, work=SessionWork.READING, open_only=True
        ):
            if open_reading.card_number == number:
                self.live.store.end_windowless_session(open_reading.id, now)
        self.live.bump()
        if trigger_card:
            where = {
                Finding.DELIVERED: "the trigger has fired: the defect is eligible for the dial",
                Finding.NOT_DELIVERED: "the trigger has not fired: the defect waits",
                Finding.CANNOT_TELL: "the owner is asked with your words",
            }[finding]
            return DoorResult(
                door="reading",
                said=f"#{number} read as {finding.value.replace('-', ' ')}; {where}.",
            )
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


    # ── a triage reading's result (plan 59, item 3) ────────────────────

    def triage(
        self,
        slug: str,
        number: int,
        *,
        result: TriageResult,
        words: str,
        source: str | None,
        direction: Direction | None,
    ) -> DoorResult:
        """A triage reading's result, in one act: the typed result validated
        against what it must name, the two fingerprints taken from the text
        it actually judged, the record written with the decision identity it
        mints, the `TRIAGED` row on the card, the end of that exact reading's
        record, and a reconcile — the shape `reading` has, for the same
        reason: a verb that writes a row and leaves the session's record open
        makes the seat look busy forever, and one that writes a row without
        a fingerprint routes tomorrow's document on yesterday's reading.

        Nothing here decides what the routing becomes: that is
        `board/triage.py::routing_of`, from this record and the document
        together. This door only refuses a result that does not carry what
        its own kind has to carry."""
        words = words.strip()
        if not words:
            raise DoorRefused(
                "A result without its reasoning records nothing; say what the source said."
            )
        detail = self._detail(slug, number)
        document = detail.document
        if (
            document is None
            or document.archived
            or document.kind != DocumentKind.SUGGESTION
            or document.suggestion_kind != SuggestionKind.DEFECT
        ):
            raise DoorRefused(
                f"#{number} is not a live defect suggestion; a triage reads a defect's mark."
            )
        open_now = next(
            (
                r
                for r in self.live.store.windowless_sessions(
                    slug, work=SessionWork.TRIAGE, open_only=True
                )
                if r.card_number == number
            ),
            None,
        )
        if open_now is None:
            raise DoorRefused(
                f"No triage is open for #{number}. A result lands from the reading the board "
                "started and nowhere else; that is what makes it independent."
            )
        sources = self.live.sources(slug)
        resolved = sources.resolve(source)
        if result == TriageResult.NOW:
            if resolved is None or resolved.fingerprint is None:
                raise DoorRefused(
                    "A `now` needs a source the board can read: "
                    + (resolved.note if resolved is not None else "this result names none")
                    + ". Prose shaped like a source is not a source."
                )
            if direction is None:
                raise DoorRefused(
                    "A `now` records which way it moves the product; name one of: "
                    + ", ".join(d.value for d in Direction)
                )
        if result == TriageResult.SPLIT and (resolved is None or resolved.fingerprint is None):
            raise DoorRefused(
                "A split names the source that settles its settled half: "
                + (resolved.note if resolved is not None else "this result names none")
            )
        if result == TriageResult.WHEN:
            trigger, why = read_or_decline(words)
            if trigger is None:
                raise DoorRefused(f"A `when` names a trigger the board can read: {why}")
        now = clock.now()
        previous = self.live.store.latest_triages(slug).get(number)
        record = self.live.store.record_triage(
            slug,
            number,
            at=now,
            actor=Actor.SESSION,
            result=result,
            words=words,
            decision=uuid.uuid4().hex[:16],
            parent=previous.decision if previous is not None else None,
            direction=direction,
            source_ref=resolved.ref if resolved is not None else None,
            source_path=resolved.path if resolved is not None else None,
            source_fingerprint=resolved.fingerprint if resolved is not None else None,
            document_fingerprint=document.fingerprint,
            session_id=open_now.session_id,
        )
        self.live.add_row(
            slug,
            number,
            Row(kind=RowKind.TRIAGED, text=triaged_row(record, resolved)),
            Actor.SESSION,
        )
        self.live.store.end_windowless_session(open_now.id, now)
        self.live.bump()
        self.loops.reconcile_now()
        routed = routing_now(document, record, sources)
        return DoorResult(
            door="triage",
            said=(
                f"#{number} read as {result.value}; it routes as {routed.state.value} "
                f"(decision {record.decision})."
            ),
        )

    # ── the short lanes that write the corpus (items 4 and 5) ──────────

    def corpus_lane(
        self,
        slug: str,
        number: int,
        *,
        kind: CorpusLaneKind,
        decision: str,
        brief: str,
        attempt: int,
    ) -> CorpusLane:
        """Open one isolated worktree whose only job is a corpus write the
        record already selected: a split to separate, or the owner's ruling
        to apply. It is not the card's lane — its worktree is named
        `<kind>-<n>-<slug>` so neither the lane directory reader nor the
        branch reader sees `card-<n>-`, the card never moves to Executing,
        and no lane record is written — because a card whose defect is being
        separated has no hands on its work.

        A launch that fails is a lane that ended before it began: the record
        says so with the machine's words and the board's next beat decides
        whether to try again."""
        live = self.live.projects[slug]
        card = self.live.card(slug, number)
        name = corpus_lane_name(kind, number, card.title)
        now = clock.now()
        launch = self.runtime.start(
            Start(
                repo=live.project.path,
                card=name,
                brief=brief,
                effort=CORPUS_LANE_EFFORT,
                from_slot=None,
            )
        )
        session = launch.session
        opened = self.live.store.open_corpus_lane(
            slug,
            number,
            kind=kind,
            decision=decision,
            name=name,
            path=(session.worktree if session is not None else None)
            or lane_path(live.project.path, name),
            session_id=session.session_id if session is not None else None,
            attempt=attempt,
            at=now,
        )
        if launch.verdict != LaunchVerdict.ALIVE or session is None:
            words = f"The {kind.value} lane did not start: {launch.reason}"
            self.live.store.end_corpus_lane(opened.id, now, words)
            self.live.note(slug, number, AuditKind.DIAL, Actor.MACHINE, words)
            return opened
        placement = launch.placement
        where = f"{placement.model.value} on {placement.slot}" if placement else session.slot
        self.live.note(
            slug,
            number,
            AuditKind.DIAL,
            Actor.MACHINE,
            f"A {kind.value} lane opened for decision {decision}: {session.short_id}, {where}, "
            f"in {name}; it writes the corpus and nothing else",
        )
        return opened

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
        happened. Executed needs the plan archived and a readable signal; a
        lane that folded anything outside docs/ needs a review record that
        exists (plan 11, item 1) — an unattended lane's "clean" is a refused
        close, not a remembered rule."""
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
        self._refuse_a_code_lane_without_its_review(slug, number, lane, review)
        # Read before any row is written, so nothing that goes wrong reading
        # the lane leaves DELIVERED on a card that did not move (review
        # pass 2; a file the board cannot read is skipped, and a directory
        # it cannot list would raise here, before the first row).
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

    def _refuse_a_code_lane_without_its_review(
        self, slug: str, number: int, lane: Lane | None, review: str | None
    ) -> None:
        """The lane's files from its birth to its tip, read from its worktree
        while it stands and from the project's checkout once it is gone: a
        file outside docs/ makes it a code lane, and a code lane closes with
        a review record that exists — named by the path it was expected at.
        A card the board knows no lane for shipped nothing the board could
        see, and passes; the head counts a shipped card with no REVIEW row
        either way."""
        project = self.live.projects[slug].project
        record = self.live.store.lane(slug, number)
        where = record.path if record is not None else (lane.path if lane is not None else None)
        if where is None:
            return
        standing = Path(where).is_dir()
        files = self.runtime.lane_files(
            where if standing else project.path,
            birth=record.birth if record is not None else None,
            tip=None if standing else (record.tip if record is not None else None),
        )
        code = sorted(f for f in files if not f.startswith(DOCS))
        if not code:
            return
        shown = ", ".join(code[:3]) + (f" and {len(code) - 3} more" if len(code) > 3 else "")
        expected = f"{project.path}/docs/reviews/<file>.md"
        if not review:
            raise DoorRefused(
                f"#{number}'s lane folded code ({shown}); a code lane closes with a review "
                f"record — name it with --review, a file at {expected}."
            )
        if not any((Path(root) / review).is_file() for root in (project.path, where)):
            raise DoorRefused(
                f"#{number}'s review record {review} is not in the project's tree; expected "
                f"{project.path}/{review}."
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
