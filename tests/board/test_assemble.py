from datetime import UTC, date, datetime, timedelta

from board.assemble import (
    assemble_board,
    assemble_detail,
    card_gate,
    document_state,
    essence,
    summarize,
)
from board.lane import nothing_read
from board.moves import GroupLayout
from domain.card import Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind, DocumentState
from domain.gate import Gate
from domain.project import Project
from domain.row import Row, RowKind

NOW = datetime(2026, 9, 3, 22, 0, tzinfo=UTC)


def doc(
    stem: str = "p1",
    *,
    kind: DocumentKind = DocumentKind.PLAN,
    archived: bool = False,
    gate: Gate | None = Gate.HIGH,
    essence: str | None = "From the plan.",
) -> Document:
    return Document(
        kind=kind,
        stem=stem,
        path=f"docs/plans/{stem}.md",
        archived=archived,
        title="Plan one",
        date=date(2026, 9, 1),
        status=None,
        status_word=None,
        gate=gate,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=None,
        head_fields=[],
        intent_heading=None,
        intent="",
        essence=essence,
        read_at=NOW,
    )


def card(
    number: int = 1,
    *,
    link: DocumentLink | None = None,
    rows: list[Row] | None = None,
    gate: Gate | None = Gate.LOW,
    origin: CardOrigin = CardOrigin.IMPORTED,
    born_at: datetime = NOW,
    column: Column = Column.PLANNED,
) -> Card:
    return Card(
        number=number,
        project="p",
        place=Place(column=column, group=None, position=0),
        title="Card",
        gate=gate,
        tags=[],
        deep="",
        citations=[],
        link=link,
        origin=origin,
        born_at=born_at,
        rows=rows or [],
    )


LINK = DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="Plan one", archived=False)


def test_the_five_document_states_are_derived_not_stored():
    assert document_state(card(link=None), None) == DocumentState.NOTE
    assert document_state(card(link=LINK), None) == DocumentState.GONE
    assert document_state(card(link=LINK), doc(archived=True)) == DocumentState.ARCHIVED
    assert document_state(card(link=LINK), doc()) == DocumentState.PLAN
    assert (
        document_state(card(link=LINK), doc(kind=DocumentKind.SUGGESTION))
        == DocumentState.SUGGESTION
    )


def test_the_documents_gate_wins_and_the_cards_own_is_the_fallback():
    assert card_gate(card(gate=Gate.LOW), doc(gate=Gate.XHIGH)) == Gate.XHIGH
    assert card_gate(card(gate=Gate.LOW), doc(gate=None)) == Gate.LOW
    assert card_gate(card(gate=Gate.LOW), None) == Gate.LOW


def test_the_essence_is_the_cards_own_words_then_the_documents():
    serves = [Row(kind=RowKind.SERVES, text="Own words.")]
    assert essence(card(rows=serves), doc()) == ("Own words.", "card")
    assert essence(card(), doc()) == ("From the plan.", "document")
    assert essence(card(), None) == (None, None)


def test_new_is_only_an_arrival_within_a_day():
    index = CorpusIndex(documents=[], read_at=NOW)
    assert summarize(
        card(origin=CardOrigin.ARRIVED, born_at=NOW - timedelta(hours=2)), index, NOW
    ).is_new
    assert not summarize(
        card(origin=CardOrigin.ARRIVED, born_at=NOW - timedelta(days=2)), index, NOW
    ).is_new
    assert not summarize(card(origin=CardOrigin.FOUNDING, born_at=NOW), index, NOW).is_new
    assert not summarize(card(origin=CardOrigin.IMPORTED, born_at=NOW), index, NOW).is_new


def test_points_count_rows_the_essence_aside_and_age_prefers_the_document():
    rows = [
        Row(kind=RowKind.SERVES, text="s"),
        Row(kind=RowKind.TODAY, text="t"),
        Row(kind=RowKind.COST, text="c"),
    ]
    index = CorpusIndex(documents=[doc()], read_at=NOW)
    summary = summarize(card(link=LINK, rows=rows), index, NOW)
    assert summary.points == 2
    assert summary.age_date == date(2026, 9, 1)
    assert summarize(card(rows=rows), index, NOW).age_date == NOW.date()


def test_a_gone_document_still_names_the_path_it_cites():
    index = CorpusIndex(documents=[], read_at=NOW)
    summary = summarize(card(link=LINK), index, NOW)
    assert summary.document_state == DocumentState.GONE
    assert summary.document_path == "docs/plans/p1.md"


def test_the_board_always_has_eight_columns_each_with_a_group_and_counts_attention():
    project = Project(slug="p", name="P", path="/tmp/p", registered_at=NOW)
    cards = [
        card(1, link=LINK, column=Column.DECISION_MOMENT),
        card(2, column=Column.EXECUTING, origin=CardOrigin.ARRIVED),
        card(
            3, link=DocumentLink(kind=DocumentKind.PLAN, stem="nowhere", title="", archived=False)
        ),
    ]
    layout = [
        GroupLayout(column=Column.DECISION_MOMENT, name=None, numbers=[1]),
        GroupLayout(column=Column.EXECUTING, name=None, numbers=[2]),
        GroupLayout(column=Column.PLANNED, name=None, numbers=[3]),
    ]
    index = CorpusIndex(documents=[doc(), doc("unlinked")], read_at=NOW)
    board = assemble_board(
        project=project,
        layout=layout,
        cards=cards,
        index=index,
        version=3,
        watching=False,
        watch_note="inotify limit",
        now=NOW,
    )
    assert [c.definition.column for c in board.columns] == list(Column)
    assert all(len(c.groups) >= 1 for c in board.columns)
    assert board.attention.model_dump() == {
        "asking_you": 1,
        "in_flight": 1,
        "lanes_ended": 0,
        "signals_due": 0,
        "signals_asking": 0,
        "doubted": 0,
        "arrived_today": 1,
        "documents_gone": 1,
        "documents_without_card": 1,
        "verdicts_unread": 0,
    }
    assert [d.stem for d in board.documents_without_card] == ["unlinked"]
    assert board.corpus.watching is False and board.corpus.watch_note == "inotify limit"
    assert board.corpus.live_plans == 2
    assert board.version == 3


def test_the_detail_splits_rows_into_the_brief_and_the_record():
    rows = [
        Row(kind=RowKind.SERVES, text="s"),
        Row(kind=RowKind.DELIVERED, text="d"),
        Row(kind=RowKind.TODAY, text="t"),
        Row(kind=RowKind.WATCH, text="w"),
    ]
    index = CorpusIndex(documents=[doc()], read_at=NOW)
    c = card(link=LINK, rows=rows)
    c.citations = ["docs/plans/p1.md", "docs/audits/a.md"]
    lane, doors = nothing_read(c, "/srv/p", NOW)
    detail = assemble_detail(c, index, [], NOW, lane=lane, doors=doors, readings=[])
    assert [r.kind for r in detail.brief] == [RowKind.TODAY]
    assert [r.kind for r in detail.record] == [RowKind.DELIVERED, RowKind.WATCH]
    assert detail.document is not None and detail.document.stem == "p1"
    assert detail.other_citations == ["docs/audits/a.md"]
