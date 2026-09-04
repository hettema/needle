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
        suggestion_kind=None,
        cites=[],
        handouts=[],
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


def test_an_archived_plan_naming_a_card_links_to_it_archived_and_is_never_born():
    """A plan written at the close and archived in the same fold is still the
    card's document; three of Hello Revenue's shipped cards were doubted for
    want of a plan they had (2026-09-04)."""
    link = DocumentLink(kind=DocumentKind.SUGGESTION, stem="s1", title="Idea", archived=False)
    effects = reconcile(
        index(
            doc(DocumentKind.PLAN, "p1", "Plan one", archived=True, card_ref=7),
            doc(DocumentKind.PLAN, "p2", "Plan two", archived=True, card_ref=8),
            doc(DocumentKind.SUGGESTION, "s1", "Idea"),
        ),
        [card(7, None, Column.EXECUTED), card(8, link, Column.EXECUTED)],
    )
    assert [(r.card_number, r.document.stem, r.archived) for r in effects.relinked] == [
        (7, "p1", True),
        (8, "p2", True),
    ]
    assert effects.born == []
    # A card that already has a plan keeps it: the archived one is not its document.
    planned = DocumentLink(kind=DocumentKind.PLAN, stem="p0", title="Plan zero", archived=False)
    effects = reconcile(
        index(
            doc(DocumentKind.PLAN, "p0", "Plan zero"),
            doc(DocumentKind.PLAN, "p1", "Plan one", archived=True, card_ref=7),
        ),
        [card(7, planned)],
    )
    assert effects.relinked == [] and effects.born == []


# ── plan 06, item 5: a card follows its plan; item 2: the defects rail ─


def _plan(stem: str, *cites: str, archived: bool = False, card_ref: int | None = None) -> Document:
    return doc(DocumentKind.PLAN, stem, stem.title(), archived=archived, card_ref=card_ref).model_copy(
        update={"cites": list(cites)}
    )


def _suggestion(stem: str, kind: str = "idea", *, archived: bool = False) -> Document:
    from domain.document import SuggestionKind

    return doc(DocumentKind.SUGGESTION, stem, stem, archived=archived).model_copy(
        update={"suggestion_kind": SuggestionKind(kind)}
    )


def _slink(stem: str, archived: bool = False) -> DocumentLink:
    return DocumentLink(kind=DocumentKind.SUGGESTION, stem=stem, title=stem, archived=archived)


def _plink(stem: str, archived: bool = False) -> DocumentLink:
    return DocumentLink(kind=DocumentKind.PLAN, stem=stem, title=stem.title(), archived=archived)


def test_a_plan_citing_suggestions_takes_the_first_card_and_folds_the_rest_and_nothing_is_born():
    cards = [
        card(7, _slink("a"), Column.BACKLOG),
        card(8, _slink("b"), Column.BACKLOG),
        card(9, _slink("c"), Column.BACKLOG),
    ]
    corpus = index(_plan("p", "a", "b", "c"), _suggestion("a"), _suggestion("b"), _suggestion("c"))
    effects = reconcile(corpus, cards)
    assert [(r.card_number, r.document.stem, r.promote, r.why) for r in effects.relinked] == [
        (7, "p", True, "which carries this card's suggestion")
    ]
    assert [(f.card_number, f.into, f.plan.stem) for f in effects.folded] == [(8, 7, "p"), (9, 7, "p")]
    assert effects.born == [], "neither the plan nor the suggestions it carries are born"
    # The next read, with the store's work done, changes nothing: the suggestions
    # stay live in their folder and are carried, not without a card.
    after = [
        card(7, _plink("p"), Column.PLANNED),
        card(8, _slink("b"), Column.PLANNED).model_copy(update={"folded_into": 7}),
        card(9, _slink("c"), Column.PLANNED).model_copy(update={"folded_into": 7}),
    ]
    assert reconcile(corpus, after).empty()


def test_a_plan_that_already_has_a_card_folds_what_it_cites_under_that_card():
    cards = [
        card(16, _plink("p"), Column.EXECUTING),
        card(7, _slink("a", archived=True), Column.NOT_NOW),
    ]
    effects = reconcile(index(_plan("p", "a"), _suggestion("a", archived=True)), cards)
    assert effects.relinked == []
    assert [(f.card_number, f.into) for f in effects.folded] == [(7, 16)]


def test_a_carried_suggestion_with_no_card_is_never_born_and_a_shipped_card_is_not_carried():
    effects = reconcile(
        index(_plan("p", "a", "b"), _suggestion("a"), _suggestion("b")),
        [card(3, _slink("b"), Column.DONE)],
    )
    assert [b.document.stem for b in effects.born] == ["p"]
    assert effects.folded == [] and effects.relinked == []


def test_a_live_plan_carries_a_suggestion_before_an_archived_one_does():
    cards = [
        card(8, _slink("a", archived=True), Column.NOT_NOW),
        card(17, _plink("old", archived=True), Column.EXECUTED),
        card(20, _plink("new"), Column.UP_NEXT),
    ]
    corpus = index(
        _plan("old", "a", archived=True), _plan("new", "a"), _suggestion("a", archived=True)
    )
    assert [(f.card_number, f.into) for f in reconcile(corpus, cards).folded] == [(8, 20)]


def test_a_plan_naming_a_card_by_number_still_folds_the_other_suggestions_it_cites():
    cards = [card(7, None, Column.PLANNED), card(8, _slink("b"), Column.BACKLOG)]
    effects = reconcile(index(_plan("p", "b", card_ref=7), _suggestion("b")), cards)
    assert [(r.card_number, r.why) for r in effects.relinked] == [(7, "which names this card")]
    assert [(f.card_number, f.into) for f in effects.folded] == [(8, 7)]


def test_a_backlog_card_follows_its_documents_kind_onto_and_off_the_rail():
    from domain.card import Place
    from domain.column import DEFECTS_RAIL

    on_rail = card(5, _slink("d"), Column.BACKLOG).model_copy(
        update={"place": Place(column=Column.BACKLOG, group=DEFECTS_RAIL, position=0)}
    )
    below = card(6, _slink("i"), Column.BACKLOG)
    effects = reconcile(index(_suggestion("d", "idea"), _suggestion("i", "defect")), [on_rail, below])
    assert [(r.card_number, r.into_rail, r.kind.value) for r in effects.rehomed] == [
        (5, False, "idea"),
        (6, True, "defect"),
    ]
    settled = reconcile(index(_suggestion("d", "defect"), _suggestion("i", "idea")), [on_rail, below])
    assert settled.rehomed == []
    elsewhere = reconcile(index(_suggestion("i", "defect")), [card(6, _slink("i"), Column.UP_NEXT)])
    assert elsewhere.rehomed == [], "the rail is Backlog's; a defect queued by the owner stays queued"


def test_a_suggestion_is_born_with_its_kind():
    effects = reconcile(index(_suggestion("d", "defect"), _suggestion("i", "idea")), [])
    assert [(b.document.stem, b.kind.value if b.kind else None) for b in effects.born] == [
        ("d", "defect"),
        ("i", "idea"),
    ]
