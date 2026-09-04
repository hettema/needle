from datetime import UTC, datetime

from board.reconcile import reconcile
from domain.card import Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind

AT = datetime(2026, 9, 3, tzinfo=UTC)


def doc(
    kind: DocumentKind,
    stem: str,
    title: str,
    *,
    archived: bool = False,
    card_ref: int | None = None,
) -> Document:
    folder = "docs/plans" if kind == DocumentKind.PLAN else "docs/slice-suggestions"
    return Document(
        kind=kind,
        stem=stem,
        path=f"{folder}{'/done' if archived else ''}/{stem}.md",
        archived=archived,
        title=title,
        date=None,
        status=None,
        status_word=None,
        gate=None,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=card_ref,
        head_fields=[],
        intent_heading=None,
        intent="",
        essence=None,
        read_at=AT,
    )


def card(number: int, link: DocumentLink | None, column: Column = Column.PLANNED) -> Card:
    return Card(
        number=number,
        project="p",
        place=Place(column=column, group=None, position=0),
        title=f"Card {number}",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=link,
        origin=CardOrigin.IMPORTED,
        born_at=AT,
        rows=[],
    )


def index(*documents: Document) -> CorpusIndex:
    return CorpusIndex(documents=list(documents), read_at=AT)


def test_a_live_document_with_no_card_is_born_into_its_column():
    effects = reconcile(
        index(doc(DocumentKind.PLAN, "p1", "Plan one"), doc(DocumentKind.SUGGESTION, "s1", "Idea")),
        [],
    )
    assert [(b.document.stem, b.column) for b in effects.born] == [
        ("p1", Column.PLANNED),
        ("s1", Column.BACKLOG),
    ]


def test_an_archived_document_with_no_card_is_never_born():
    assert reconcile(index(doc(DocumentKind.PLAN, "old", "Old", archived=True)), []).empty()


def test_a_linked_live_document_changes_nothing():
    link = DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="Plan one", archived=False)
    assert reconcile(index(doc(DocumentKind.PLAN, "p1", "Plan one")), [card(1, link)]).empty()


def test_a_document_moved_to_done_is_noticed_once():
    link = DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="Plan one", archived=False)
    effects = reconcile(
        index(doc(DocumentKind.PLAN, "p1", "Plan one", archived=True)), [card(1, link)]
    )
    assert [a.card_number for a in effects.archived] == [1]
    knowing = DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="Plan one", archived=True)
    assert reconcile(
        index(doc(DocumentKind.PLAN, "p1", "Plan one", archived=True)), [card(1, knowing)]
    ).empty()


def test_a_renamed_document_keeps_its_card_by_title():
    link = DocumentLink(kind=DocumentKind.PLAN, stem="old-stem", title="Plan one", archived=False)
    effects = reconcile(index(doc(DocumentKind.PLAN, "new-stem", "Plan one")), [card(1, link)])
    assert [(r.card_number, r.old_stem, r.document.stem) for r in effects.renamed] == [
        (1, "old-stem", "new-stem")
    ]
    assert effects.born == []


def test_a_vanished_document_births_nothing_and_a_new_title_is_a_new_card():
    link = DocumentLink(kind=DocumentKind.PLAN, stem="old-stem", title="Plan one", archived=False)
    effects = reconcile(index(doc(DocumentKind.PLAN, "other", "Something else")), [card(1, link)])
    assert effects.renamed == []
    assert [b.document.stem for b in effects.born] == ["other"]


def test_a_plan_naming_a_note_becomes_its_document():
    effects = reconcile(
        index(doc(DocumentKind.PLAN, "p1", "Plan one", card_ref=7)), [card(7, None)]
    )
    assert [(r.card_number, r.document.stem) for r in effects.relinked] == [(7, "p1")]
    assert effects.born == []


def test_a_plan_supersedes_the_suggestion_a_card_cites():
    link = DocumentLink(kind=DocumentKind.SUGGESTION, stem="s1", title="Idea", archived=False)
    effects = reconcile(
        index(
            doc(DocumentKind.PLAN, "p1", "Plan one", card_ref=7),
            doc(DocumentKind.SUGGESTION, "s1", "Idea"),
        ),
        [card(7, link)],
    )
    assert [r.card_number for r in effects.relinked] == [7]


def test_a_second_plan_naming_a_planned_card_is_its_own_card():
    link = DocumentLink(kind=DocumentKind.PLAN, stem="p1", title="Plan one", archived=False)
    effects = reconcile(
        index(
            doc(DocumentKind.PLAN, "p1", "Plan one"),
            doc(DocumentKind.PLAN, "p2", "Plan two", card_ref=7),
        ),
        [card(7, link)],
    )
    assert effects.relinked == []
    assert [b.document.stem for b in effects.born] == ["p2"]


def test_a_plan_naming_an_unknown_card_is_born_as_usual():
    effects = reconcile(index(doc(DocumentKind.PLAN, "p1", "Plan one", card_ref=999)), [])
    assert [b.document.stem for b in effects.born] == ["p1"]
