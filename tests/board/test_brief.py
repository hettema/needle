"""The card rendered as text: the brief a lane opens with (plan 03, item 3)."""

from datetime import UTC, datetime

from board.assemble import assemble_detail
from board.brief import lane_name, lane_path, lane_slug, render
from board.lane import nothing_read
from domain.card import Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind
from domain.gate import Gate
from domain.project import Project
from domain.row import Row, RowKind

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def test_the_lane_name_is_the_card_number_and_a_short_slug():
    assert (
        lane_slug("Every metered kilowatt is billed — at last!")
        == "every-metered-kilowatt-is-billed"
    )
    assert (
        lane_name(253, "Every metered kilowatt is billed")
        == "card-253-every-metered-kilowatt-is-billed"
    )
    assert lane_path("/srv/p/", "card-1-x") == "/srv/p/.claude/worktrees/card-1-x"
    assert lane_slug("!!!") == "card"


def test_the_brief_carries_the_rows_the_gate_the_document_and_the_lane():
    document = Document(
        kind=DocumentKind.PLAN,
        stem="p",
        path="docs/plans/p.md",
        archived=False,
        title="The thing",
        date=None,
        status="PENDING",
        status_word="PENDING",
        gate=Gate.HIGH,
        gate_why="the judgment is small",
        sequencing=None,
        found_by=None,
        card_ref=None,
        head_fields=[],
        intent_heading="Intent",
        intent="The owner presses one button. Then more.",
        essence="The owner presses one button.",
        read_at=NOW,
    )
    card = Card(
        number=7,
        project="proj",
        place=Place(column=Column.UP_NEXT, group="Now", position=1),
        title="The thing",
        gate=None,
        tags=[],
        deep="",
        citations=["docs/plans/p.md", "docs/reviews/r.md"],
        link=DocumentLink(kind=DocumentKind.PLAN, stem="p", title="The thing", archived=False),
        origin=CardOrigin.IMPORTED,
        born_at=NOW,
        rows=[
            Row(kind=RowKind.TODAY, text="build it"),
            Row(kind=RowKind.WATCH, text="w — owner by 2026-09-09"),
        ],
    )
    index = CorpusIndex(documents=[document], read_at=NOW)
    lane, doors = nothing_read(card, "/srv/p", NOW)
    detail = assemble_detail(card, index, [], NOW, lane=lane, doors=doors, readings=[])
    project = Project(slug="proj", name="Harbourmaster", path="/srv/p", registered_at=NOW)
    text = render(detail, project)
    assert text.splitlines() == [
        "#7 — The thing",
        "column: Up next · Now",
        "project: Harbourmaster (/srv/p)",
        " serves: The owner presses one button.",
        "  today: build it",
        "  watch: w — owner by 2026-09-09",
        "   gate: high — the judgment is small",
        "   open: docs/plans/p.md (plan)",
        "   also: docs/reviews/r.md",
        "   lane: card-7-the-thing — the worktree under .claude/worktrees/ named so the board "
        "sees hands on the card",
    ]
