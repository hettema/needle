"""The card rendered as text: what a lane opens with, and what `needle card`
prints. One renderer, so a session launched from the board and one started
from a terminal read the same brief (plan 03, item 3).
"""

import re

from domain.board import CardDetail
from domain.lane import HANDS_ON, Lane
from domain.project import Project
from domain.watercooler import WatercoolerLine

LANE_SLUG_LENGTH = 32
"""0.1 cut the slug at 32 characters; the same cut keeps a lane name legible in
a unit name, an app-id and a branch."""


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
    if document is not None:
        state = "archived" if document.archived else document.kind.value
        lines.append(f"   open: {document.path} ({state})")
    elif summary.document_path:
        lines.append(f"   open: {summary.document_path} — cited, and nowhere")
    else:
        lines.append("   open: (no document — the card text is the whole brief)")
    for other in detail.other_citations:
        lines.append(f"   also: {other}")
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
