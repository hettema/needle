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
        suggestion_kind=None,
        cites=[],
        handouts=[],
        items=[],
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


# ── plan 11: who fixes it, in every brief that may file; the dial's planning brief ──


def test_the_filing_rule_names_the_three_lines_the_bar_and_one_mark_per_document():
    from board.brief import FIX_BAR, filing_rule

    rule = filing_rule("the lane on card #7, in the review's seams pass")
    assert "`**Kind:** defect`" in rule and "`**Fix:** <mark>`" in rule
    assert "`**Found by:** the lane on card #7, in the review's seams pass`" in rule
    assert FIX_BAR in rule and "removes a class rather than an instance" in rule
    assert "One mark, one document" in rule and "docs/plans/README.md's rule" in rule


def test_the_reading_brief_files_by_the_rule_and_reads_a_trigger_as_a_trigger():
    from board.brief import reading_brief
    from board.signals import parse_watch

    document = Document(
        kind=DocumentKind.SUGGESTION,
        stem="s",
        path="docs/slice-suggestions/s.md",
        archived=False,
        title="The thing",
        date=None,
        status=None,
        status_word=None,
        gate=None,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=None,
        suggestion_kind=None,
        cites=[],
        handouts=[],
        items=[],
        head_fields=[],
        intent_heading=None,
        intent="x",
        essence="x",
        read_at=NOW,
    )
    card = Card(
        number=7,
        project="proj",
        place=Place(column=Column.BACKLOG, group="Defects", position=0),
        title="The thing",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=DocumentLink(kind=DocumentKind.SUGGESTION, stem="s", title="The thing", archived=False),
        origin=CardOrigin.ARRIVED,
        born_at=NOW,
        rows=[],
    )
    index = CorpusIndex(documents=[document], read_at=NOW)
    lane, doors = nothing_read(card, "/srv/p", NOW)
    detail = assemble_detail(card, index, [], NOW, lane=lane, doors=doors, readings=[])
    project = Project(slug="proj", name="Harbourmaster", path="/srv/p", registered_at=NOW)
    signal = parse_watch("a second slip exists — session the mail log by 2026-12-31 every 1d")
    as_trigger = reading_brief(detail, project, signal, "2026-09-05", trigger=True)
    assert as_trigger.startswith("A reading of #7's trigger — the `Fix: when` line")
    assert "The trigger to read: a second slip exists" in as_trigger
    assert "the dial may take the card; nothing moves" in as_trigger
    assert "`**Fix:** <mark>`" in as_trigger and "#7's reading, 2026-09-05" in as_trigger
    as_signal = reading_brief(detail, project, signal, "2026-09-05")
    assert as_signal.startswith("A reading of #7's signal, started by the board")
    assert "The signal to read: a second slip exists" in as_signal


def test_the_planning_brief_carries_the_five_rules_and_the_one_exit_to_the_owner():
    from board.brief import planning_brief

    document = Document(
        kind=DocumentKind.SUGGESTION,
        stem="s",
        path="docs/slice-suggestions/s.md",
        archived=False,
        title="The thing",
        date=None,
        status=None,
        status_word=None,
        gate=None,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=None,
        suggestion_kind=None,
        cites=[],
        handouts=[],
        items=[],
        head_fields=[],
        intent_heading=None,
        intent="x",
        essence="x",
        read_at=NOW,
    )
    card = Card(
        number=7,
        project="proj",
        place=Place(column=Column.BACKLOG, group="Defects", position=0),
        title="The thing",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=DocumentLink(kind=DocumentKind.SUGGESTION, stem="s", title="The thing", archived=False),
        origin=CardOrigin.ARRIVED,
        born_at=NOW,
        rows=[],
    )
    index = CorpusIndex(documents=[document], read_at=NOW)
    lane, doors = nothing_read(card, "/srv/p", NOW)
    detail = assemble_detail(card, index, [], NOW, lane=lane, doors=doors, readings=[])
    project = Project(slug="proj", name="Harbourmaster", path="/srv/p", registered_at=NOW)
    brief = planning_brief(detail, project, "2026-09-05", skill=None, first_lane=False)
    assert brief.startswith("A plan to write for a defect the dial took, on Harbourmaster (/srv/p)")
    assert "never hands on any tree" in brief and "docs/plans/README.md describes" in brief
    for rule in ("1. The title", "2. Each item", "3. The plan carries an item", "4. When the terrain", "5. When the fix implies a decision"):
        assert rule in brief, rule
    assert "`**Class:**" in brief
    assert 'needle row proj 7 ASK "' in brief
    assert "**Carries:** docs/slice-suggestions/s.md" in brief
    assert "by the dial's planning session for #7" in brief
    assert "git pull --rebase origin develop" in brief
    assert "the board's own repository" not in brief
    own = planning_brief(detail, project, "2026-09-05", skill="/hm-plan-write", first_lane=True)
    assert "/hm-plan-write" in own and "the board's own repository" in own
