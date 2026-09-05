"""The card rendered as text: what a lane opens with, and what `needle card`
prints. One renderer, so a session launched from the board and one started
from a terminal read the same brief (plan 03, item 3).
"""

import re
from pathlib import Path

from domain.board import CardDetail
from domain.lane import HANDS_ON, Lane
from domain.project import Project
from domain.row import RowKind
from domain.signal import Signal
from domain.triage import CorpusLaneKind, Direction, Source, Triage
from domain.watercooler import WatercoolerLine

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_SLUG_LENGTH = 32
"""0.1 cut the slug at 32 characters; the same cut keeps a lane name legible in
a unit name, an app-id and a branch."""
READING_PREFIX = "reading-"
"""A reading session is named after the lane it is not: `reading-card-<n>-<slug>`."""
PLANNING_PREFIX = "planning-"
"""The dial's planning session, the same way: `planning-card-<n>-<slug>` (plan 11, item 4)."""
TRIAGE_PREFIX = "triage-"
"""The reading that verifies a mark: `triage-card-<n>-<slug>` (plan 59, item 3)."""


def needle_command() -> str:
    # `--project`, never `--directory`: the latter changes directory to
    # Needle's checkout before the verb runs, so a lane's `needle fold` read
    # its worktree as `.` and pushed Needle's own HEAD to Needle's trunk
    # (found by Hello Revenue card #387's review, 2026-09-04). `--project`
    # only picks the environment; the verb runs where the lane stands.
    return f"uv --project {REPO_ROOT} run needle"


def lane_slug(title: str) -> str:
    bare = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return bare[:LANE_SLUG_LENGTH].rstrip("-") or "card"


def lane_name(number: int, title: str) -> str:
    return f"card-{number}-{lane_slug(title)}"


def lane_path(project_path: str, name: str) -> str:
    return f"{project_path.rstrip('/')}/.claude/worktrees/{name}"


def render(detail: CardDetail, project: Project) -> str:
    card, summary, document = detail.card, detail.summary, detail.document
    lines = [f"#{card.number} — {card.title}", f"column: {card.place.column.value}"]
    if card.place.group:
        lines[-1] += f" · {card.place.group}"
    lines.append(f"project: {project.name} ({project.path})")
    if summary.essence:
        lines.append(f" serves: {summary.essence}")
    for row in detail.brief:
        lines.append(f"{row.kind.value.lower():>7}: {row.text}")
    for row in detail.record:
        lines.append(f"{row.kind.value.lower():>7}: {row.text}")
    if card.deep:
        lines.append(f"   note: {card.deep}")
    if summary.gate:
        why = f" — {document.gate_why}" if document is not None and document.gate_why else ""
        lines.append(f"   gate: {summary.gate.value}{why}")
    else:
        lines.append("   gate: none declared — a suggestion or a note, not a plan")
    for handout in detail.handouts.named:
        item = f"{handout.item} — " if handout.item else ""
        verifies = (
            f"; verifies {handout.verifies}" if handout.verifies else "; verifies nothing named"
        )
        lines.append(f"  hands: {item}{handout.role}: {handout.what}{verifies}")
    if detail.handouts.verdict:
        lines.append(f"  hands: {detail.handouts.verdict}")
    if document is not None:
        state = "archived" if document.archived else document.kind.value
        lines.append(f"   open: {document.path} ({state})")
    elif summary.document_path:
        lines.append(f"   open: {summary.document_path} — cited, and nowhere")
    else:
        lines.append("   open: (no document — the card text is the whole brief)")
    for other in detail.other_citations:
        lines.append(f"   also: {other}")
    if card.folded_into is not None:
        lines.append(
            f" folded: into #{card.folded_into} — that card's plan carries this suggestion; "
            "it follows that card and closes with it"
        )
    for folded in summary.folded:
        lines.append(
            f"carries: #{folded.number} {folded.title}"
            + (f" ({folded.document_path})" if folded.document_path else "")
        )
    lines.append(
        f"   lane: {lane_name(card.number, card.title)} — the worktree under "
        f".claude/worktrees/ named so the board sees hands on the card"
    )
    return "\n".join(lines)


def _shown_files(files: list[str], limit: int = 8) -> str:
    more = f" … and {len(files) - limit} more" if len(files) > limit else ""
    return ", ".join(files[:limit]) + more


def watercooler_text(lines: list[WatercoolerLine]) -> str:
    """The watercooler as a lane reads it: one line per act, oldest first, in UTC."""
    if not lines:
        return "  (nothing said yet)"
    return "\n".join(
        f"  {line.at.strftime('%Y-%m-%d %H:%MZ')} "
        f"{f'#{line.card_number}' if line.card_number is not None else 'the board'}: {line.text}"
        for line in lines
    )


def neighbours_text(lanes: dict[int, Lane], titles: dict[int, str], number: int) -> str:
    """The other lanes with hands on the project right now, each with its
    footprint and one line, as every lane is told before it starts (plan
    07, item 2). `lanes` is the loop's last read; `titles` the cards'."""
    lines: list[str] = []
    for other, lane in sorted(lanes.items()):
        if other == number or lane.state not in HANDS_ON:
            continue
        touching = (
            f" Touching: {_shown_files(lane.edits)}." if lane.edits else " Touching nothing yet."
        )
        declared = f" Its plan names: {_shown_files(lane.declared)}." if lane.declared else ""
        lines.append(
            f"  #{other} {titles.get(other, lane.name)} — {lane.sentence}{touching}{declared}"
        )
    return "\n".join(lines) if lines else "  (no other lane has hands on this project)"


def reading_name(number: int, title: str) -> str:
    return READING_PREFIX + lane_name(number, title)


def planning_name(number: int, title: str) -> str:
    return PLANNING_PREFIX + lane_name(number, title)


def triage_name(number: int, title: str) -> str:
    return TRIAGE_PREFIX + lane_name(number, title)


def corpus_lane_name(kind: CorpusLaneKind, number: int, title: str) -> str:
    """A corpus lane's worktree, named so nothing reads it as the card's own
    lane: `split-<n>-<slug>`, never `card-<n>-…`. Two readers search for
    `card-<digits>-` — the lane directory (`board/lane.py`) and the lane
    branch (`runtime/git.py`) — and a corpus lane that matched either would
    put phantom hands on a card nobody planned (plan 59, item 4)."""
    return f"{kind.value}-{number}-{lane_slug(title)}"


FIX_BAR = (
    "`now` when all three hold — the intent it breaks is written (a CLAUDE.md rule, a "
    "shipped plan's intent, a validator that already states the bar), the fix stays inside "
    "the change it corrects, and the fix removes a class rather than an instance (a "
    "validator, a ratchet, an alarm; never a special case); `when <signal>` in the WATCH "
    "grammar (`<what> — session|url|file|command <target> by <YYYY-MM-DD> [every <N>h|<N>d]`) "
    "when the fix waits for a trigger the board can read; `his` when the fix implies a "
    "decision the owner has to make first. A `now` or a `his` says why on the same line, in "
    "words a reader who was not there can act on: name the written thing that selects the "
    "outcome and what in it selects it. A category — \"a product call\", \"UX\", \"a bound\" — "
    "names the shape of the decision and not the decision, and a backticked path on its own "
    "is a source, not a reason; a ratchet refuses both"
)
"""The three-part bar for `Fix: now`, and the bar on the reason beside it
(plan 59, item 2). From the owner's own question ("find a bug, fix it,
because you can; but is it that black and white?") and the answer that it is
not. The reason half is what an independent reading has to work with: the
mark is written from inside one session's context and read from outside it,
so a reason nobody else can act on is a mark nobody else can check."""


def filing_rule(found_by: str) -> str:
    """How a reading or review session files a defect it saw on the way
    (plan 06, item 2 for the kind; plan 11, item 2 for the mark): the title
    rule, the three head lines, the bar for `now`, and one mark per
    document. One sentence of it in every brief that may file, so the head
    the dial reads eligibility from is written by the session that holds the
    evidence, when it is fresh."""
    return (
        "file it as a suggestion in docs/slice-suggestions/, titled by docs/plans/README.md's "
        "rule — what will be true when it is fixed, in the owner's words, never a mechanism "
        "or a term from the code, since it is a card the moment it lands and he ranks it from "
        "the title alone — with three lines under the title: `**Kind:** defect`, `**Fix:** "
        f"<mark>` and `**Found by:** {found_by}`. The mark says who fixes it: {FIX_BAR}. "
        "One mark, one document: a finding that carries a different mark is its own "
        "suggestion, cross-linked by path. Commit it on develop with a body saying what "
        "prompted it, and push"
    )


def reading_brief(
    detail: CardDetail, project: Project, signal: Signal, today: str, *, trigger: bool = False
) -> str:
    """What a reading session opens with (plan 09, item 1): the card, the
    signal and what the closing session said it delivered; that it is never a
    lane; where the project's own rules put its read-only data access; the
    three findings and the one verb that writes them; and the replacement
    row for a measure that cannot be read (item 2). With `trigger`, the
    signal is a defect's `Fix: when` trigger (plan 11, item 5): delivered
    makes the defect eligible for the dial and moves nothing. The project's
    data rules are pointed at, never restated: they live in its own CLAUDE.md."""
    card = detail.card
    needle = needle_command()
    slug = card.project
    delivered = next((r.text for r in card.rows if r.kind == RowKind.DELIVERED), None)
    expect = f" expect {signal.expect}" if signal.expect else ""
    cadence = (
        f"every {signal.every_hours:g} h"
        if signal.every_hours < 24 or signal.every_hours % 24
        else f"every {signal.every_hours / 24:g} d"
    )
    what = (
        f"A reading of #{card.number}'s trigger — the `Fix: when` line on its suggestion, "
        "which says when this defect may be fixed"
        if trigger
        else f"A reading of #{card.number}'s signal"
    )
    return (
        f"{what}, started by the board on {project.name} "
        f"({project.path}), {today}. This session reads evidence and ends with one finding. "
        "It is never a lane: no worktree (never EnterWorktree), no edit to code, no commit of "
        "code, no push of code, no window. Read-only for the repository; for the project's "
        "data exactly as its own rules provide it — its CLAUDE.md names the read-only "
        "database role, the log rules and the probes; never a credential those rules reserve. "
        "Git, the project's own commands and its documents are yours to read.\n\n"
        + render(detail, project)
        + ("\n\nThe trigger to read: " if trigger else "\n\nThe signal to read: ")
        + f"{signal.what} — {signal.target}{expect}; due {signal.due.isoformat()}, {cadence}."
        + (
            f"\nWhat the session that shipped it said the owner now has: {delivered}"
            if delivered and not trigger
            else ""
        )
        + (
            "\nDelivered means the trigger has fired and the defect may be fixed now: the "
            "board records it on the card and the dial may take the card; nothing moves. Not "
            "delivered leaves it waiting for the next reading."
            if trigger
            else ""
        )
        + "\n\nRead the evidence the "
        + ("trigger" if trigger else "signal")
        + " names with the tools you have. Then end your turn "
        "with exactly one finding, through the needle command line, never by editing a file:"
        f'\n  {needle} reading {slug} {card.number} delivered "what you read, where, and what '
        'it said"'
        f'\n  {needle} reading {slug} {card.number} not-delivered "what you read, where, and '
        'what it said"'
        f'\n  {needle} reading {slug} {card.number} cannot-tell "what you read, and what would '
        'decide it"'
        "\nA finding names what was read and where, so the owner can check it in a minute. "
        "Never guess: delivered needs the evidence in hand; not delivered means the evidence "
        "exists and says no; cannot tell means the evidence cannot exist yet (the next real "
        "build has not happened) or exists and does not decide it. A cannot-tell is put to "
        "the owner with your words as the evidence, so write them for him."
        "\n\nIf the signal is unmeasurable or the wrong measure — a threshold nobody set from "
        "data, a measure that ignores size — do not guess. Write the measure you can read as "
        'a replacement WATCH row on the same command, `--watch "<what> — session <what to '
        'check, where> [expect <value>] by YYYY-MM-DD [every <N>h|<N>d]"`, and say so in your '
        "finding: the board reads the new row from its next cadence and the owner sees both "
        "rows on the card. When the evidence cannot exist before a certain time, set the "
        "cadence so the next reading lands when it could."
        "\n\nA defect in the product you saw on the way is not this "
        + ("trigger's" if trigger else "signal's")
        + " business: "
        + filing_rule(f"#{card.number}'s reading, {today}")
        + " — the one write this session may make, and only when you saw one."
        "\n\nYour turn ends with the needle reading command and one plain sentence after it. "
        "Ask the owner nothing: a question is a cannot-tell finding with the question as its "
        "words."
    )


def planning_brief(
    detail: CardDetail, project: Project, today: str, *, skill: str | None, first_lane: bool
) -> str:
    """What the dial's planning session opens with (plan 11, item 4): the
    defect as its card reads, the plan shape, and the five rules it must
    hold with no owner in the loop — the title rule, the done means from the
    suggestion's own words, the class-closer item with its `Class:` line,
    the live check when the terrain touches the page, and the one exit when
    the fix implies a decision that is his: an ASK row and a stop. It never
    has hands on a tree; it writes back through the corpus and the card."""
    card = detail.card
    needle = needle_command()
    slug = card.project
    path = detail.summary.document_path or ""
    shape = (
        f"use the project's own plan-writing skill, {skill}"
        if skill
        else "the shape docs/plans/README.md describes: a `**Status:**` line, a `**Written:**` "
        "line, an `**Effort gate:** <low|medium|high|xhigh> — <why>` line, `**Sequencing:**` "
        "when it depends on another plan, an Intent section, and numbered items each ending "
        'with what "done means" as a behaviour someone can observe'
    )
    return (
        f"A plan to write for a defect the dial took, on {project.name} ({project.path}), "
        f"{today}. The owner turned the dial — his standing ruling that a defect its finder "
        "marked `Fix: now` enters execution without him — and the board started this session "
        "to write the plan. Nobody is in the loop: this is a windowless session in the "
        "project's checkout, never hands on any tree (no worktree, never EnterWorktree, no "
        "edit to code, no commit of code). Once the plan lands the board opens Start itself, "
        "and the lane it starts runs as any lane: a worktree, the review rings, a fold on "
        "green, a close the board refuses without a review record.\n\n"
        + render(detail, project)
        + "\n\nThe suggestion is the material: read it whole, and read the code it names. "
        f"Write the plan into docs/plans/ in the project's plan shape — {shape}. Five rules "
        "this plan holds, because no owner reads it before it runs:\n"
        "1. The title says what will be true when the plan is done, in the owner's words, so "
        'he can rank the card without opening it ("Defects fix themselves", never a '
        "mechanism, an area or a term from the code).\n"
        '2. Each item\'s "done means" comes from the suggestion\'s own "What would hold it" '
        '(or "Done means"); the plan adds no scope the suggestion did not name.\n'
        "3. The plan carries an item that makes the class loud — a validator, a ratchet, an "
        "alarm — or says in one sentence why the class is already loud, and the head carries "
        "that sentence as `**Class:** <what makes the class loud, or why it already is>` so "
        "the board can read it.\n"
        "4. When the terrain touches `frontend/`, the done means carries a live check of the "
        "served page, because a green suite is not the truth for the page.\n"
        "5. When the fix implies a decision that is the owner's — an intent nobody wrote, a "
        "boundary to move, a product surface, a call between two acceptable shapes — or the "
        "defect is already fixed or its premise no longer holds, write nothing to the "
        "repository. End your turn with one row on the card and stop:\n"
        f'   {needle} row {slug} {card.number} ASK "<the decision or the finding, in one '
        'sentence, with what depends on it>"\n'
        "   The card reads as his from that row; the board never rewrites the document.\n\n"
        f"Head the plan with `**Carries:** {path}` — that line is how the board follows the "
        f"plan: #{card.number} becomes the plan's card, same number and history — and with "
        f"`**Written:** {today}, by the dial's planning session for #{card.number}`, its "
        "`**Effort gate:**` with the why, and a `**Terrain:**` section that names in "
        "backticks every file the lane will touch, honestly: the collision check before "
        "Start reads nothing else. In the same commit move the suggestion to "
        "docs/slice-suggestions/done/ and add a `**Carried by:** <the plan's path>` line under "
        "its title. Write nothing else to the repository. Commit in this checkout on develop "
        f"with a body that says the dial's planning session wrote it for #{card.number}, and "
        "push (`git push origin develop`); if the push is refused because the trunk moved, "
        "`git pull --rebase origin develop` and push again. The board cards the plan the "
        "moment it lands."
        + (
            "\n\nThis is the board's own repository: the lane that follows folds code under "
            "the running board, so it runs only when no other lane is live anywhere; write "
            "the plan for that."
            if first_lane
            else ""
        )
        + "\n\nYour turn ends with the push, or with the ASK row, and one plain sentence "
        "after it. Ask the owner nothing in this window: nobody is reading it."
    )


THE_RULE = (
    "A decision is Dennis's only when the written record does not select among materially "
    "different outcomes he owns, or when acting would create external exposure beyond a bound "
    "he has already authorised. Applying an existing intent, ruling, precedent or authorised "
    "bound is execution, not a new decision. Effect-level reversibility is evidence about how "
    "safely to act under uncertainty; it is never the test of who owns the call."
)
"""The owner's own words, ruled true 2026-09-05, and the whole test a triage
applies. Carried verbatim into every brief that has to apply it, because a
paraphrase of an ownership rule is a different ownership rule."""

PUSH_LINE = (
    "and push (`git push origin develop`); if the push is refused because the trunk moved, "
    "`git pull --rebase origin develop` and push again."
)
"""The one way a windowless session lands a corpus write, as plan 11's
planning brief already says it; written once so the three briefs cannot
drift into three ways of pushing."""


def triage_brief(
    detail: CardDetail,
    project: Project,
    today: str,
    *,
    document_text: str,
    source: Source | None,
) -> str:
    """What the reading that verifies a mark opens with (plan 59, item 3).

    Everything it needs is in the brief and nothing else is: the rule in the
    owner's words, the document whole, and the source the mark cites as this
    board resolved it — or the fact that it resolved nowhere. It never reads
    the session that filed the defect, because independence of context is
    the whole point of the seat; a second reader that inherits the first
    reader's reasons is not a second reader.

    It asks one question. Not *is this a good fix* and not *what should we
    do* — those are the plan's and the lane's. Only: does the record the
    mark cites select this outcome?"""
    card = detail.card
    needle = needle_command()
    slug = card.project
    document = detail.document
    mark = "unmarked"
    if document is not None and document.fix is not None:
        fix = document.fix
        mark = fix.mark.value + (
            f" — {fix.trigger}" if fix.trigger else f" — {fix.why}" if fix.why else ""
        )
    elif document is not None:
        mark = f"unmarked ({document.fix_note})"
    where = (
        f"{source.note}\n\n--- the source, as the board read it ---\n{source.text}\n--- ends ---"
        if source is not None and source.text is not None
        else source.note
        if source is not None
        else "the mark cites no source the board could find a reference in"
    )
    return (
        f"A reading of #{card.number}'s mark on {project.name} ({project.path}), {today}. "
        "The session that filed this defect decided who fixes it from inside its own context, "
        "and nothing has read that decision again. You are that second reading. You have no "
        "share of its context and you must not go looking for one: decide from the document "
        "and the source below, and from the project's own written rules.\n\n"
        "This session is never a lane: no worktree (never EnterWorktree), no edit to any file, "
        "no commit, no push, no window. It writes nothing but its one result.\n\n"
        + render(detail, project)
        + f"\n\nThe mark as it stands: **Fix: {mark}**\n"
        f"\n--- the document ({detail.summary.document_path}) ---\n{document_text}\n--- ends ---"
        f"\n\nThe source the mark relies on: {where}"
        f"\n\nThe rule, in the owner's words, ruled true on 2026-09-05:\n\n{THE_RULE}\n\n"
        "Your one question: **does the source select this outcome?** Not whether the fix is "
        "good, not what to build — those belong to the plan and the lane. Only whether the "
        "written record the mark leans on already settles who decides.\n\n"
        "End your turn with exactly one result, through the needle command line, never by "
        "editing a file:\n"
        f'  {needle} triage {slug} {card.number} now "<the resolved source and the proposition '
        'in it that selects this outcome>" --source <path or #N> --direction <direction>\n'
        f'  {needle} triage {slug} {card.number} his "<the alternatives, which owner-held '
        "outcome differs between them, and why no written ruling selects one — or the exact "
        'exposure and the missing authorised bound>"\n'
        f'  {needle} triage {slug} {card.number} when "<trigger in the WATCH grammar: <what> — '
        'session|url|file|command <target> by YYYY-MM-DD [every <N>h|<N>d]>"\n'
        f'  {needle} triage {slug} {card.number} split "<the two halves, each with its source>" '
        "--source <path or #N>\n"
        f'  {needle} triage {slug} {card.number} cannot-tell "<the missing evidence and where '
        'it should come from>"\n\n'
        "What each result has to hold:\n"
        "- `now` needs a source that resolved and a proposition in it that selects this "
        "outcome. An absent or unresolvable source cannot produce `now`, however obvious the "
        "fix looks: prose shaped like a source is not a source. A `now` that leans on a spend "
        "or risk bound names the artefact, the bound, this action's measured exposure and the "
        "comparison showing it inside.\n"
        "- `his` is for a record that does not select: name the alternatives, say which "
        "owner-held outcome differs between them, and say why no written ruling picks one.\n"
        "- `split` is for a document holding an outcome the record settles beside one it does "
        "not. Name both halves and each half's source. You authorise neither: a short lane "
        "separates them and both halves come back for a fresh reading.\n"
        "- `cannot-tell` is the honest answer when the evidence that would decide it is "
        "missing. Say what is missing and where it should come from. It routes to nobody; it "
        "does not route to the owner unless the missing thing is itself his decision, in "
        "which case the result is `his`.\n"
        "- A `--direction` is required with `now`, from this set, and says which way the "
        "product moves if the machine acts: "
        + ", ".join(f"`{d.value}`" for d in Direction)
        + ".\n\n"
        "Your result is a verification, not an authorisation. It can close the dial at once — "
        "a `his` or a `cannot-tell` on a document marked `now` stops the machine immediately — "
        "and it can never open it wider than the corpus: a `now` on a document the corpus does "
        "not mark `now` authorises nothing until a session rewrites the mark in a commit that "
        "cites your reading.\n\n"
        "Your turn ends with the needle triage command and one plain sentence after it. Ask "
        "the owner nothing: nobody is reading this window."
    )


def split_brief(detail: CardDetail, project: Project, today: str, *, triage: Triage) -> str:
    """What the lane that separates a split document opens with (plan 59,
    item 4). It writes the corpus and nothing else, and it authorises
    neither half: the reading proposed the separation, this lane performs
    it, and both halves come back for a fresh reading afterwards."""
    card = detail.card
    path = detail.summary.document_path or ""
    return (
        f"A document to separate on {project.name} ({project.path}), {today}. A reading of "
        f"#{card.number}'s mark found two decisions in one document: one the written record "
        "settles, and one it does not. Your one job is to separate them in the corpus. You "
        "decide neither.\n\n"
        f"What the reading said:\n\n{triage.words}\n\n"
        + render(detail, project)
        + f"\n\nThe document: {path}\n\n"
        "Do exactly this and nothing else:\n"
        "1. File the settled half as its own suggestion in docs/slice-suggestions/, titled by "
        "docs/plans/README.md's rule — what will be true when it is fixed, in the owner's "
        "words, never a mechanism or a term from the code. Give it `**Kind:** defect`, the "
        "`**Fix:**` mark the reading named for that half with its reason, `**Found by:** the "
        f"split of #{card.number} ({today})`, and `**Split from:** {path}`.\n"
        f"2. Narrow {path} to the half the record does not settle: leave its `**Fix:**` line "
        "as the reading named it for that half, and add `**Split into:** <the new suggestion's "
        "path>` under its title. Move nothing to done/.\n"
        "3. Commit both files on develop with a body saying the split came from the reading "
        f"of #{card.number} and naming the decision `{triage.decision}`, " + PUSH_LINE + "\n\n"
        "Write nothing else to the repository: no code, no plan, no review record. The "
        "founding case is Hello Revenue's split of 2026-09-05 (commit `59661dcd9`, which "
        "produced card #435): one document held a fix the record settled and a product call it "
        "did not, and the settled half had waited behind the unsettled one for weeks.\n\n"
        "Both halves go back to `needs triage` when you are done: the reading that proposed "
        "this separation authorised neither of them, and the board will read each afresh.\n\n"
        "Your turn ends with the push and one plain sentence after it. Ask the owner nothing: "
        "nobody is reading this window."
    )


def ruling_brief(
    detail: CardDetail, project: Project, today: str, *, triage: Triage, answer: str
) -> str:
    """What the lane that applies the owner's answer opens with (plan 59,
    item 5). His sentence is already the durable record on the card; this
    lane's one job is to make the corpus say what he said, citing the row,
    so the next cold session reads his ruling from the document and not from
    a database."""
    card = detail.card
    path = detail.summary.document_path or ""
    return (
        f"A ruling to apply on {project.name} ({project.path}), {today}. The owner answered "
        f"#{card.number} on the board. His answer is already on the card's record; the corpus "
        "does not say it yet, and the corpus is what the next session reads. Your one job is "
        "to make the document say what he said.\n\n"
        f"His answer, verbatim:\n\n{answer}\n\n"
        f"The reading that put the question to him:\n\n{triage.words}\n\n"
        + render(detail, project)
        + f"\n\nThe document: {path}\n\n"
        "Do exactly this and nothing else:\n"
        f"1. Rewrite {path}'s `**Fix:**` line to what his answer settles — `now <reason>`, "
        "`when <trigger in the WATCH grammar>`, or a narrowed `his <reason>` — and nothing "
        "else on that line. The reason is his answer in the fewest words that still say what "
        "selects the outcome; a category word alone is refused by the ratchet.\n"
        f"2. Add `**Ruled by:** the owner on {today}, on #{card.number} "
        f"(decision {triage.decision})` under the title, so the document carries where the "
        "mark came from.\n"
        "3. Commit on develop with a body naming his answer and the decision "
        f"`{triage.decision}`, " + PUSH_LINE + "\n\n"
        "Write nothing else to the repository: no code, no plan, no review record. If his "
        "answer does not settle the mark — it asks a question back, or it rules on something "
        "the document does not carry — change nothing, and say so in one sentence; the board "
        "leaves the row standing and the card says the half-state.\n\n"
        "Your turn ends with the push and one plain sentence after it. Ask the owner nothing: "
        "nobody is reading this window."
    )
