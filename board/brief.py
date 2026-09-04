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
from domain.watercooler import WatercoolerLine

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_SLUG_LENGTH = 32
"""0.1 cut the slug at 32 characters; the same cut keeps a lane name legible in
a unit name, an app-id and a branch."""
READING_PREFIX = "reading-"
"""A reading session is named after the lane it is not: `reading-card-<n>-<slug>`."""


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


def reading_brief(detail: CardDetail, project: Project, signal: Signal, today: str) -> str:
    """What a reading session opens with (plan 09, item 1): the card, the
    signal and what the closing session said it delivered; that it is never a
    lane; where the project's own rules put its read-only data access; the
    three findings and the one verb that writes them; and the replacement
    row for a measure that cannot be read (item 2). The project's data rules
    are pointed at, never restated: they live in its own CLAUDE.md."""
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
    return (
        f"A reading of #{card.number}'s signal, started by the board on {project.name} "
        f"({project.path}), {today}. This session reads evidence and ends with one finding. "
        "It is never a lane: no worktree (never EnterWorktree), no edit to code, no commit of "
        "code, no push of code, no window. Read-only for the repository; for the project's "
        "data exactly as its own rules provide it — its CLAUDE.md names the read-only "
        "database role, the log rules and the probes; never a credential those rules reserve. "
        "Git, the project's own commands and its documents are yours to read.\n\n"
        + render(detail, project)
        + "\n\nThe signal to read: "
        f"{signal.what} — {signal.target}{expect}; due {signal.due.isoformat()}, {cadence}."
        + (
            f"\nWhat the session that shipped it said the owner now has: {delivered}"
            if delivered
            else ""
        )
        + "\n\nRead the evidence the signal names with the tools you have. Then end your turn "
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
        "\n\nA defect in the product you saw on the way is not this signal's business: file "
        "it as a suggestion in docs/slice-suggestions/ with `**Kind:** defect` on its second "
        f"line and a `**Found by:**` line naming this reading (#{card.number}'s reading, "
        f"{today}), committed on develop with a body saying what prompted it and pushed — "
        "the one write this session may make, and only when you saw one."
        "\n\nYour turn ends with the needle reading command and one plain sentence after it. "
        "Ask the owner nothing: a question is a cannot-tell finding with the question as its "
        "words."
    )
