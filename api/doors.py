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
from api.team import Team, hand_of
from board import review_rules
from board.assemble import document_of, is_trigger_card
from board.brief import (
    FOCUS_EXCERPT,
    corpus_lane_name,
    filing_rule,
    focus_brief,
    lane_name,
    lane_path,
    needle_command,
    neighbours_text,
    render,
    review_guidance,
    team_brief,
    watercooler_text,
)
from board.focus import FOCUS_PATH, is_chosen
from board.handouts import handouts_row
from board.lane import HANDS_ON
from board.parse import plan_stem_of
from board.signals import GRAMMAR, read_or_decline, where_after, where_after_finding
from board.team import Unexecutable, team_words
from board.title import title_fingerprint
from board.triage import routing_now, triaged_row
from domain.audit import AuditKind
from domain.board import CardDetail
from domain.call import HowKnown
from domain.card import Actor, Card, Place
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.evidence import Evidence, EvidenceState
from domain.focus import (
    MACHINE_READ_KINDS,
    AcceptedMove,
    FocusVerdict,
    Leverage,
    Likelihood,
    MeasureSide,
    ReadingKind,
    RecheckOutcome,
)
from domain.gate import Gate
from domain.lane import CollisionVerdict, Conversation, DoorResult, Lane, LaneRecord, LaneState
from domain.launch import LaunchVerdict, Start
from domain.project import Project
from domain.row import Row, RowKind
from domain.signal import Finding, SessionWork, SignalKind
from domain.slot import rung_words
from domain.team import Route
from domain.triage import (
    CorpusLane,
    CorpusLaneKind,
    Direction,
    Routing,
    TitleVerdict,
    TriageResult,
)
from domain.verdict import EvidenceClass, VerdictsRuled
from domain.window import WindowKind
from infrastructure import clock
from infrastructure.live import WATERCOOLER_SHOWN, Live
from infrastructure.store import StoreRefusal
from runtime.git import TRUNK
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


SKILLS = Path(".claude") / "skills"
"""The one folder a project's skills live in: Claude Code reads it, the
Start door names the plan-writing skill from it, and the installer links
Codex's own folder at it (`api.board_cli.lay_skills_link`)."""


def plan_skill(project_path: Path) -> str | None:
    """The project's own plan-writing skill, when its `.claude/skills/` has
    one (Hello Revenue's is `hr-plan-write`); None means the shape in
    docs/plans/README.md is the plan shape."""
    skills = project_path / SKILLS
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
        self.team = Team(live, runtime)

    def _detail(self, slug: str, number: int) -> CardDetail:
        return self.live.detail(slug, number)

    # ── Start ──────────────────────────────────────────────────────────

    def brief_for_lane(self, detail: CardDetail, slug: str, team: Route | None = None) -> str:
        """The lane's brief. `team` is the team this Start assigns (card
        #58) — the card's own once it has one, so a restart carries the
        same team the first Start did; a brief read from a terminal with
        none carries the card's stored team, or nothing."""
        project = self.live.projects[slug].project
        card = detail.card
        gate = detail.summary.gate
        needle = needle_command()
        text = render(detail, project) + f"\n\nexecute #{card.number}"
        team = team or (detail.team.route if detail.team is not None else None)
        if team is not None:
            text += "\n\n" + team_brief(team, needle)
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
            "using docs/reviews/README.md, with its `**Plan:**` line naming your plan. "
            "The card shows the items met and the review's recorded findings."
            "\n\nFor findings outside the change, "
            + filing_rule(
                f"the lane on card #{card.number}"
                + (f" ({detail.document.path})" if detail.document is not None else "")
                + ", in the independent review"
            )
            + "."
            "\n\n" + review_guidance() + "."
            "\n\nTo ask the owner something, end your turn with the question; the board shows it "
            "on the card and his answer resumes you."
        )
        return text

    def start(
        self, slug: str, number: int, *, actor: Actor = Actor.OWNER, lens: str | None = None
    ) -> DoorResult:
        """Start the card's lane where the rule says. `actor` is whose move
        it is: the owner's click through the page or his terminal, or the
        machine's under the dial — his standing ruling applied by the board
        (plan 11, item 4), which the card's history then says. One door:
        shared ground opens it with the ground in its label, and there is
        nothing left to override (INTENT.md lesson 4). `lens` is the lens the
        page was under at the click, so the history carries a trace the
        loop of card #87 reads instead of his memory: the lens in use and,
        under Leverage, the class the card was read as."""
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
        # The team is assigned before the work and enters the brief (card
        # #58, item 1): the card's own when it has one — a restart keeps
        # the experiment it began — else the router's, from the cached
        # rule's hand; the row is written once the lane is alive, with the
        # rung it landed on, and never again.
        held = detail.team
        team: Route | None = held.route if held is not None else None
        if team is None and doors.placement is not None:
            try:
                team = self.team.route(slug, number, doors.placement)
            except Unexecutable as why:
                raise DoorRefused(f"Start refused: {why}") from why
        brief = self.brief_for_lane(detail, slug, team)
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
        # The lane's birth is the trunk's head its branch was laid from,
        # read now rather than left for the loop's first pass: a close
        # before that pass — a docs-only lane closed at once — has nothing
        # else to say what the lane folded from (card #110, pass four).
        laid = self.runtime.branch_tip(project.path, TRUNK, path=path)
        self.live.store.record_lane(
            LaneRecord(
                project=slug,
                card_number=number,
                name=name,
                path=path,
                branch=None,
                birth=laid,
                tip=laid,
                first_seen=now,
                last_seen=now,
                gone_at=None,
                folded_at=None,
                trunk_synced_at=None,
                main_synced_at=None,
            )
        )
        placement = launch.placement
        where = rung_words(placement.model, placement.slot) if placement else session.slot
        said = f"Started {session.short_id}, {where}, at {gate.value}, in {name}"
        said += f", in {launch.scope}" if launch.scope else f" ({launch.reason})"
        if team is not None and held is None:
            landed = team.model_copy(update={"hand": hand_of(placement)}) if placement else team
            assigned, wrote = self.team.assign(slug, number, landed)
            if wrote:
                self.live.note(
                    slug, number, AuditKind.STARTED, Actor.MACHINE, f"team: {team_words(landed)}"
                )
            team = assigned.route
        if team is not None:
            said += f"; team: {team_words(team)}"
        if actor == Actor.MACHINE:
            said += "; started by the dial"
        if lens:
            said += f"; under the {lens} lens"
            leverage = detail.summary.leverage
            if leverage is not None and leverage.leverage is not None:
                chance = f" ({leverage.likelihood.value})" if leverage.likelihood else ""
                said += f", read as {leverage.leverage.value}{chance}"
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
        where = rung_words(placement.model, placement.slot) if placement else result.session.slot
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
        where = rung_words(placement.model, placement.slot) if placement else result.session.slot
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
            f"Discussing in {opened.window.app_id}, {rung_words(placement.model, placement.slot)}; "
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
                f"Talking in {opened.window.app_id}, "
                f"{rung_words(placement.model, placement.slot)}; a conversation about nothing "
                f"yet ({session_id[:8]}), never "
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
            f"Planning {numbered} in {opened.window.app_id}, "
            f"{rung_words(placement.model, placement.slot)}; the plan it writes carries "
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
        result: TriageResult | None,
        words: str | None,
        source: str | None,
        direction: Direction | None,
        title: str,
        failed: list[str],
    ) -> DoorResult:
        """A triage reading's result, in one act: the typed result validated
        against what it must name, the two fingerprints taken from the text
        it actually judged, the record written with the decision identity it
        mints, the `TRIAGED` row on the card, the end of that exact reading's
        record, and a reconcile — the shape `reading` has, for the same
        reason: a verb that writes a row and leaves the session's record open
        makes the seat look busy forever, and one that writes a row without
        a fingerprint routes tomorrow's document on yesterday's reading.

        Since card #74 the same reading judges the title (item 3): `title`
        is `passes` or the reader's words for what the owner could not
        place, `failed` the words that failed. On a defect the mark's result
        and the title's verdict land together and the door refuses one
        without the other; on a plan or an idea the title's verdict is the
        whole result and a mark's result is refused, because there is no
        mark to verify.

        Nothing here decides what the routing becomes: that is
        `board/triage.py::routing_of`, from this record and the document
        together. This door only refuses a result that does not carry what
        its own kind has to carry."""
        detail = self._detail(slug, number)
        document = detail.document
        if document is None or document.archived:
            raise DoorRefused(
                f"#{number} has no live document; a reading judges a live plan or suggestion."
            )
        defect = (
            document.kind == DocumentKind.SUGGESTION
            and document.suggestion_kind == SuggestionKind.DEFECT
        )
        if defect and result is None:
            raise DoorRefused(
                f"#{number} is a defect: its reading lands the mark's result and the title's "
                "verdict in one command (now|his|when|split|cannot-tell, then --title)."
            )
        if not defect and result is not None:
            raise DoorRefused(
                f"#{number} is not a defect; it has no mark to verify. A reading of a plan or "
                "an idea lands the title's verdict alone: --title passes, or --title "
                '"<what you could not place>" --failed <words>.'
            )
        title = title.strip()
        if not title:
            raise DoorRefused(
                'A title verdict is "passes" or the words for what you could not place.'
            )
        passes = title.lower() == "passes"
        if passes and failed:
            raise DoorRefused("A passing title names no failed words.")
        words = (words or "").strip()
        if defect and not words:
            raise DoorRefused(
                "A result without its reasoning records nothing; say what the source said."
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
        verdict = TitleVerdict.PLACEABLE if passes else TitleVerdict.UNPLACEABLE
        read = self.live.store.record_title_reading(
            slug,
            number,
            at=now,
            verdict=verdict,
            words="the owner can place it from the title alone" if passes else title,
            failed=failed,
            title_fingerprint=title_fingerprint(document.title, document.essence),
            session_id=open_now.session_id,
        )
        self.live.note(
            slug,
            number,
            AuditKind.TITLE,
            Actor.SESSION,
            f"A cold reading of the title ({open_now.session_id[:8]}): {read.verdict.value} — "
            f"{read.words}"
            + (f"; the words that failed: {', '.join(read.failed)}" if read.failed else ""),
        )
        if not defect:
            self.live.store.end_windowless_session(open_now.id, now)
            self.live.bump()
            self.loops.reconcile_now()
            return DoorResult(
                door="triage",
                said=f"#{number}'s title read as {read.verdict.value}: {read.words}"
                + (
                    "; Start stays closed until a reading of a rewritten title passes."
                    if not passes
                    else "."
                ),
            )
        assert result is not None
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
                f"(decision {record.decision}); its title read as {read.verdict.value}."
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
        where = rung_words(placement.model, placement.slot) if placement else session.slot
        self.live.note(
            slug,
            number,
            AuditKind.DIAL,
            Actor.MACHINE,
            f"A {kind.value} lane opened for decision {decision}: {session.short_id}, {where}, "
            f"in {name}; it writes the corpus and nothing else",
        )
        return opened

    # ── a project's focus (card #87) ───────────────────────────────────

    def _focus_conversation(self, slug: str) -> Conversation | None:
        live = self.live.projects[slug]
        conversations = live.snapshot.conversations if live.snapshot is not None else []
        return next((c for c in conversations if c.kind == WindowKind.FOCUS), None)

    def _intent_text(self, project: Project) -> str | None:
        file = Path(project.path) / "docs" / "INTENT.md"
        if not file.is_file():
            return None
        text = file.read_text(encoding="utf-8", errors="replace")
        return text if len(text) <= FOCUS_EXCERPT else text[:FOCUS_EXCERPT] + "\n… (truncated)"

    def focus_text(self, project: Project) -> str | None:
        file = Path(project.path) / FOCUS_PATH
        if not file.is_file():
            return None
        return file.read_text(encoding="utf-8", errors="replace")

    def focus(self, slug: str, first_line: str | None, *, moves: bool = False) -> DoorResult:
        """The Focus door (card #87, item 2): a conversation in the
        project's checkout that sharpens what matters now and finds what
        holds it back, and writes `docs/FOCUS.md` on his yes; with `moves`,
        the same conversation proposes what else could move the limit.
        Refused while one is already alive for the project, saying which."""
        alive = self._focus_conversation(slug)
        if alive is not None:
            raise DoorRefused(
                f"A focus conversation is already open for this project: {alive.short_id} on "
                f"{alive.slot}. Talk there, or close it first."
            )
        project = self.live.projects[slug].project
        strip, _, _ = self.live.focus_of(slug)
        if moves and not strip.propose.offered:
            raise DoorRefused(strip.propose.why)
        session_id = str(uuid.uuid4())
        today = clock.now().date().isoformat()
        brief = focus_brief(
            project,
            session_id,
            first_line,
            today,
            intent_text=self._intent_text(project),
            focus_text=self.focus_text(project),
            coverage_line=strip.coverage.line if strip.coverage is not None else None,
            moves=moves,
        )
        try:
            opened, session_id, placement = self.runtime.discuss(
                repo=project.path,
                card=slug,
                brief=brief,
                effort=DISCUSS_EFFORT,
                what=f"The focus of {project.name}",
                kind=WindowKind.FOCUS,
                session_id=session_id,
            )
        except WindowRefused as refusal:
            raise DoorFailed(f"Focus did not open: {refusal}") from refusal
        self.live.store.record_discussion(
            slug, None, session_id, placement.slot, clock.now(), kind=WindowKind.FOCUS
        )
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="focus",
            said=(
                f"Talking in {opened.window.app_id}, "
                f"{rung_words(placement.model, placement.slot)}; a conversation about "
                f"{'what else could move this limit' if moves else 'what matters now'} "
                f"({session_id[:8]}), never hands on a tree. What it writes into docs/FOCUS.md "
                "is proposed on the strip; the click is yours."
            ),
        )

    def choose_focus(self, slug: str) -> DoorResult:
        """The owner's click (card #87, item 1): use this document, at this
        fingerprint. The ruling is stored against the document as it stands
        and the two measures are read once as the baseline (item 6); an
        edit after the click is a new proposal, never an inherited ruling."""
        project = self.live.projects[slug].project
        strip, _, _ = self.live.focus_of(slug)
        if not strip.choose.offered:
            raise DoorRefused(strip.choose.why)
        document = strip.document
        assert document is not None and document.what_matters is not None
        now = clock.now()
        read: list[str] = []
        for side, measure in (
            (MeasureSide.OUTCOME, document.outcome),
            (MeasureSide.BOTTLENECK, document.bottleneck),
        ):
            signal = measure.signal
            if signal is None:
                raise DoorRefused(
                    f"The {side.value}'s measure cannot be read: {measure.note}; fix the line in "
                    f"{document.path} first."
                )
            if signal.kind in MACHINE_READ_KINDS:
                delivered, words = self.runtime.read_signal(signal, project.path)
            else:
                delivered, words = (
                    None,
                    (
                        "only you can read it; the recheck asks you"
                        if signal.kind == SignalKind.OWNER
                        else "read by the recheck's reader, not by the board"
                    ),
                )
            self.live.store.record_measure_reading(
                slug,
                fingerprint=document.fingerprint,
                side=side,
                at=now,
                delivered=delivered,
                words=words,
            )
            read.append(f"{side.value}: {words}")
        ruling = self.live.store.record_focus_ruling(
            slug,
            fingerprint=document.fingerprint,
            what_matters=document.what_matters,
            at=now,
        )
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="focus",
            said=(
                f"Focus chosen at {document.fingerprint} ({ruling.chosen_at.isoformat()}): "
                f"{document.what_matters}. Baseline read — {'; '.join(read)}. Every open card "
                "is now read against it, one per beat."
            ),
        )

    def _end_focus_calls(
        self, slug: str, kind: ReadingKind, *, card_number: int | None, fingerprint: str | None
    ) -> str | None:
        """End the open call(s) of this kind as landed; answers the session
        that made the reading, when one was open."""
        session_id: str | None = None
        now = clock.now()
        for call in self.live.store.focus_calls(slug, kind=kind, open_only=True):
            if card_number is not None and call.card_number != card_number:
                continue
            if fingerprint is not None and call.fingerprint != fingerprint:
                continue
            self.live.store.end_focus_call(call.id, now, landed=True, note=None)
            session_id = session_id or call.session_id
        return session_id

    def focus_check(
        self,
        slug: str,
        *,
        verdict: FocusVerdict,
        line: str,
        how_known: HowKnown | None,
        session_id: str | None,
        read: str | None = None,
    ) -> DoorResult:
        """A reader of the other make's verdict on the proposed focus (card
        #87, item 3), bound to the document as it stands now. `read` is the
        fingerprint the reading was opened on: a verdict about yesterday's
        text is refused rather than bound to today's."""
        line = line.strip()
        if not line:
            raise DoorRefused("A verdict without its line records nothing; say why in a sentence.")
        document = self.live.projects[slug].index.focus
        if document is None:
            raise DoorRefused("No focus document is written for this project; nothing to check.")
        if read is not None and read != document.fingerprint:
            raise DoorRefused(
                f"The focus document changed since this reading ({read} is now "
                f"{document.fingerprint}); it is read again."
            )
        if not document.complete:
            raise DoorRefused(
                "The focus document cannot be read whole, so a verdict on it binds to nothing: "
                + "; ".join(document.doubts)
            )
        opened = self._end_focus_calls(
            slug, ReadingKind.CHECK, card_number=None, fingerprint=document.fingerprint
        )
        record = self.live.store.record_focus_check(
            slug,
            fingerprint=document.fingerprint,
            at=clock.now(),
            verdict=verdict,
            line=line,
            how_known=how_known,
            session_id=session_id or opened,
        )
        self.live.bump()
        return DoorResult(
            door="focus-check",
            said=(
                f"The diagnosis {record.verdict.value}: {record.line} "
                f"(bound to {record.fingerprint})"
            ),
        )

    def leverage(
        self,
        slug: str,
        number: int,
        *,
        leverage: Leverage,
        likelihood: Likelihood | None,
        why: str,
        session_id: str | None,
        read: tuple[str, str] | None = None,
    ) -> DoorResult:
        """One card's reading against the chosen focus (card #87, item 4):
        the class, the likelihood with the first class only, one sentence
        of why, bound to both fingerprints. This door moves nothing and
        writes no rank: a reading judges, and only his click arranges."""
        why = why.strip()
        if not why:
            raise DoorRefused("A reading without its sentence records nothing; say why.")
        live = self.live.projects[slug]
        focus = live.index.focus
        ruling = self.live.store.focus_ruling(slug)
        if not is_chosen(focus, ruling):
            raise DoorRefused(
                "This project has no chosen focus, so a card cannot be read against one."
            )
        assert focus is not None
        if leverage == Leverage.HELPS_REMOVE and likelihood is None:
            raise DoorRefused(
                "A card that helps remove the limit says how likely it is to work: "
                "--likelihood high, medium or low."
            )
        if leverage != Leverage.HELPS_REMOVE and likelihood is not None:
            raise DoorRefused(f"A likelihood goes only with `{Leverage.HELPS_REMOVE.value}`.")
        card = self.live.card(slug, number)
        document = document_of(card, live.index)
        if document is None:
            raise DoorRefused(f"#{number} has no document behind it; a reading judges a document.")
        if read is not None and read != (focus.fingerprint, document.fingerprint):
            raise DoorRefused(
                f"The focus or #{number}'s document changed since this reading; it is read again."
            )
        opened = self._end_focus_calls(
            slug, ReadingKind.CARD, card_number=number, fingerprint=focus.fingerprint
        )
        record = self.live.store.record_leverage_reading(
            slug,
            number,
            at=clock.now(),
            leverage=leverage,
            likelihood=likelihood,
            words=why,
            focus_fingerprint=focus.fingerprint,
            document_fingerprint=document.fingerprint,
            session_id=session_id or opened,
        )
        chance = f" ({record.likelihood.value})" if record.likelihood else ""
        self.live.note(
            slug,
            number,
            AuditKind.LEVERAGE,
            Actor.SESSION,
            f"Read against the focus: {record.leverage.value}{chance} — {record.words}",
        )
        return DoorResult(
            door="leverage",
            said=f"#{number} read as {record.leverage.value}{chance}: {record.words}",
        )

    def focus_recheck(
        self,
        slug: str,
        *,
        outcome: RecheckOutcome,
        words: str,
        session_id: str | None,
        read: str | None = None,
    ) -> DoorResult:
        """The scheduled recheck's word (card #87, item 6): which link broke,
        or none. A failed recheck pauses the leverage order by itself; it
        never replaces the focus."""
        words = words.strip()
        if not words:
            raise DoorRefused("A recheck without its words records nothing.")
        live = self.live.projects[slug]
        focus = live.index.focus
        ruling = self.live.store.focus_ruling(slug)
        if not is_chosen(focus, ruling):
            raise DoorRefused("This project has no chosen focus to recheck.")
        assert focus is not None
        if read is not None and read != focus.fingerprint:
            raise DoorRefused(
                f"The focus document changed since this recheck ({read} is now "
                f"{focus.fingerprint}); it is read again."
            )
        opened = self._end_focus_calls(
            slug, ReadingKind.RECHECK, card_number=None, fingerprint=focus.fingerprint
        )
        record = self.live.store.record_focus_recheck(
            slug,
            fingerprint=focus.fingerprint,
            at=clock.now(),
            outcome=outcome,
            words=words,
            session_id=session_id or opened,
        )
        self.live.bump()
        strip, _, _ = self.live.focus_of(slug)
        return DoorResult(
            door="focus-recheck",
            said=f"The recheck says {record.outcome.value}: {record.words}. {strip.sentence}",
        )

    def accept_order(self, slug: str, numbers: list[int]) -> DoorResult:
        """ "Accept this order" (card #87, item 5): every ticked move through
        the one move door with the owner as the mover, the focus's
        fingerprint and the card's class as the reason on each history, and
        the whole batch as one record carrying every card's place before
        the move. An unticked move is recorded so it is not proposed again
        until its ground changes. Never starts a lane, never turns the
        dial, never changes a gate."""
        strip, leverages, arrangement = self.live.focus_of(slug)
        if not arrangement.available:
            raise DoorRefused(f"Leverage order unavailable: {arrangement.why}")
        assert strip.document is not None
        proposed = {m.number: m for m in arrangement.moves}
        unknown = [n for n in numbers if n not in proposed]
        if unknown:
            raise DoorRefused(
                "Not proposed by the leverage order: " + ", ".join(f"#{n}" for n in unknown)
            )
        if not arrangement.moves:
            raise DoorRefused("The leverage order proposes no move; there is nothing to accept.")
        ticked = [proposed[n] for n in numbers]
        unticked = [m for m in arrangement.moves if m.number not in set(numbers)]
        live = self.live.projects[slug]
        now = clock.now()
        fingerprint = strip.document.fingerprint
        for move in unticked:
            lv = leverages.get(move.number)
            card = self.live.card(slug, move.number)
            document = document_of(card, live.index)
            if lv is None or lv.leverage is None or document is None:
                continue
            self.live.store.record_decline(
                slug,
                move.number,
                focus_fingerprint=fingerprint,
                document_fingerprint=document.fingerprint,
                leverage=lv.leverage,
                at=now,
            )
        if not ticked:
            self.live.bump()
            return DoorResult(
                door="leverage-accept",
                said=f"Nothing accepted; {len(unticked)} move{'' if len(unticked) == 1 else 's'} "
                "left unticked and not proposed again until their ground changes.",
            )
        batch = self.live.store.record_acceptance(
            slug,
            at=now,
            focus_fingerprint=fingerprint,
            moves=[
                AcceptedMove(
                    number=m.number, from_place=m.from_place, to_place=m.to_place, why=m.why
                )
                for m in ticked
            ],
            note=None,
        )
        refused: list[str] = []
        moved = 0
        # Each target group's final order is the arrangement's, filtered to
        # the cards that will stand there: the ones already there and the
        # ones he ticked. A card's position is its index in that order.
        by_number = {c.number: c for c in self.live.store.cards(slug)}
        leaving = {m.number for m in ticked}
        for arranged in arrangement.columns:
            for group in arranged.groups:
                # An unticked card stays where it is and keeps its place in
                # the order; only a ticked one leaves its group.
                here = {
                    n
                    for n, c in by_number.items()
                    if c.place.column == arranged.column
                    and c.place.group == group.name
                    and n not in leaving
                }
                arriving = [
                    m
                    for m in ticked
                    if (m.to_place.column, m.to_place.group) == (arranged.column, group.name)
                ]
                if not arriving:
                    continue
                present = here | {m.number for m in arriving}
                order = [n for n in group.numbers if n in present]
                for move in arriving:
                    position = order.index(move.number) if move.number in order else len(order)
                    detail = (
                        f"accepted the leverage order (batch {batch.id}, focus "
                        f"{fingerprint}): {move.why}"
                        + (f"; wakes when {move.wake}" if move.wake else "")
                    )
                    try:
                        self.live.move(
                            slug,
                            move.number,
                            Place(column=arranged.column, group=group.name, position=position),
                            actor=Actor.OWNER,
                            detail=detail,
                        )
                        moved += 1
                    except StoreRefusal as refusal:
                        refused.append(f"#{move.number}: {refusal}")
        if refused:
            self.live.store.note_acceptance(batch.id, "refused — " + "; ".join(refused))
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="leverage-accept",
            said=(
                f"Order accepted (batch {batch.id}): {moved} of {len(ticked)} moves made"
                + (f"; refused: {'; '.join(refused)}" if refused else "")
                + (
                    f"; {len(unticked)} left unticked and not proposed again until their ground "
                    "changes"
                    if unticked
                    else ""
                )
                + ". Put it back is offered until you move a card by hand."
            ),
        )

    def put_back(self, slug: str) -> DoorResult:
        """ "Put it back" (card #87, item 5): every card of the last
        acceptance to its recorded place, through the same door, with his
        name and the batch as the reason. Retired by a hand move after the
        acceptance, since there is no old state any more."""
        strip, _, _ = self.live.focus_of(slug)
        accepted = strip.accepted
        if accepted is None or not strip.put_back_offered:
            raise DoorRefused(
                "Nothing to put back: no accepted order stands, or you moved a card by hand "
                "since, and there is no old state any more."
            )
        refused: list[str] = []
        restored = 0
        # Each place was recorded before any move; putting the lower positions
        # of a column back first rebuilds it as it was.
        for move in sorted(
            accepted.moves, key=lambda m: (m.from_place.column.value, m.from_place.position)
        ):
            try:
                self.live.move(
                    slug,
                    move.number,
                    move.from_place,
                    actor=Actor.OWNER,
                    detail=f"put back where it was before the leverage order (batch {accepted.id})",
                )
                restored += 1
            except StoreRefusal as refusal:
                refused.append(f"#{move.number}: {refusal}")
        self.live.store.put_back_acceptance(accepted.id, clock.now())
        self.live.bump()
        self.loops.reconcile_now()
        return DoorResult(
            door="leverage-put-back",
            said=f"Put back (batch {accepted.id}): {restored} of {len(accepted.moves)} restored"
            + (f"; refused: {'; '.join(refused)}" if refused else "")
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
        if target == Column.EXECUTED:
            self._refuse_an_unstanced_promise(slug, number, card)
        lane = live.snapshot.lanes.get(number) if live.snapshot else None
        self._refuse_a_code_lane_without_its_review(slug, number, lane, review)
        if review:
            self._refuse_a_record_that_skipped_the_read(slug, number, card, lane, review)
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

    def _refuse_an_unstanced_promise(self, slug: str, number: int, card: Card) -> None:
        """Every promise the plan made gets a stance at the close (the
        doctrine's close ritual; plan 08, item 2): an item of the archived
        plan that ends in neither `**Met:**` nor `**Deviated:**` is a promise
        nobody answered, and the card does not enter Executed over it. The
        grammar is the one the board already counts on the running lane
        (`board/parse.py::items_of`, plan 13), read here for every project;
        a plan written as one promise has no items and owes nothing here."""
        assert card.link is not None
        document = self.live.projects[slug].index.find(card.link.kind, card.link.stem)
        if document is None:
            return
        unstanced = [item for item in document.items if item.stance is None]
        if not unstanced:
            return
        named = "; ".join(f"item {item.number}, {item.title}" for item in unstanced[:3])
        more = f" and {len(unstanced) - 3} more" if len(unstanced) > 3 else ""
        raise DoorRefused(
            f"#{number} cannot enter Executed while its plan carries an unstanced promise: "
            f"{named}{more}. End each item with **Met:** <what shows it> or **Deviated:** "
            f"<pointer> in {document.path} (docs/plans/README.md)."
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
        either way. Whether the record named exists and holds is the next
        refusal's, for every record a close names (card #110, ruling 2)."""
        project = self.live.projects[slug].project
        where, standing = self._lane_root(slug, number, lane)
        if where is None:
            return
        record = self.live.store.lane(slug, number)
        birth = record.birth if record is not None else None
        tip = record.tip if record is not None else None
        files = self.runtime.lane_files(where, birth=birth, tip=None) if standing else set()
        if birth is None:
            # No birth to diff the checkout from: whatever the tree still
            # holds — nothing, or a docs edit left standing — says nothing
            # about what the lane folded before, so the board asks for a
            # record rather than reading the leftovers as docs-only (the
            # cold reads of rounds nine and ten and of pass four: a level
            # checkout, a remote lane standing by placement, an edit left in
            # the tree).
            if not review:
                raise DoorRefused(
                    f"#{number}'s lane is gone and the board recorded neither its birth nor its "
                    "tip, so it cannot tell what the lane folded; name its review record with "
                    f"--review, a file at {project.path}/docs/reviews/<file>.md."
                )
            return
        if not files:
            # The lane's tree is gone — here, or on the machine that held it,
            # which answers empty for a tree it no longer has (the cold read
            # of pass two's round) — so the project's checkout, which the
            # fold has levelled, says what the lane folded up to the tip the
            # board recorded, or to the trunk's head when it recorded none:
            # a missing observation is not "folded nothing" (round eight's
            # reader), and over-asking for a record is the loud failure.
            files = self.runtime.lane_files(project.path, birth=birth, tip=tip)
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

    def _lane_root(self, slug: str, number: int, lane: Lane | None) -> tuple[str | None, bool]:
        """Where the lane's tree is, by the board's own record of it, else
        the loop's last read, and whether it still stands — on this disk
        for a lane here, and taken as standing for a lane the board places
        on another machine, whose runtime answers for it over the wire and
        answers nothing when it is gone (pass two's reader: a local
        `is_dir` on a path that exists only there read every remote lane
        as gone)."""
        record = self.live.store.lane(slug, number)
        where = record.path if record is not None else (lane.path if lane is not None else None)
        if where is None:
            return None, False
        if not self.runtime.is_here(self.runtime.lane_machine(where)):
            return where, True
        return where, Path(where).is_dir()

    def _refuse_a_record_that_skipped_the_read(
        self, slug: str, number: int, card: Card, lane: Lane | None, review: str
    ) -> None:
        """Read local or remote review evidence and preserve record identity.

        All records close under the finite review contract, including those
        begun under the former recursive process. Old dates only exempt an
        absent Plan head; an explicitly wrong plan never identifies this card.
        """
        project = self.live.projects[slug].project
        given = Path(review)
        if given.is_absolute() or ".." in given.parts:
            raise DoorRefused(
                f"#{number}'s review record {review} is not a path inside the project's tree; "
                f"name it from the project root, a file at {project.path}/docs/reviews/<file>.md."
            )
        where, standing = self._lane_root(slug, number, lane)
        roots = [where, project.path] if where is not None and standing else [project.path]
        text: str | None = None
        for root in roots:
            text = self.runtime.lane_docs(root, [review]).plan
            if text is not None:
                break
        if text is None:
            raise DoorRefused(
                f"#{number}'s review record {review} is not in the project's tree; expected "
                f"{project.path}/{review}."
            )
        name = given.name
        if review_rules.dated(name) is None:
            raise DoorRefused(
                f"#{number}'s review record {review} carries no date in its name; the README's "
                "shape is docs/reviews/YYYY-MM-DD-<topic>.md."
            )
        if card.link is not None:
            named = plan_stem_of(text)
            if named != card.link.stem and (named is not None or review_rules.held(name)):
                raise DoorRefused(
                    f"#{number}'s review record {review} names the plan "
                    f"{named or 'nothing'} on its `**Plan:**` line, and #{number}'s plan is "
                    f"{card.link.stem}; a record is its card's word about its own diff."
                )
        faults = review_rules.record_faults(text, review)
        if faults:
            more = f"; and {len(faults) - 4} more" if len(faults) > 4 else ""
            shown = "; ".join(faults[:4]) + more
            raise DoorRefused(
                f"#{number}'s review record skipped the read HOW-WE-WORK §13 asks for, so the "
                f"card cannot close: {shown}"
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
