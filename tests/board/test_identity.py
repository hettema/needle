"""A card follows its document through a rename, a new title and the close
(plan 08, item 1): the rename matchers after the title, the face following
the document, and a citation shown only where the corpus holds it."""

from board.assemble import assemble_detail, other_citations
from board.lane import nothing_read
from board.reconcile import corpus_path_of, moved_to, reconcile
from domain.card import CardOrigin, DocumentLink
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind
from tests.board.test_reconcile import AT, card, doc, index


def _body(document: Document, intent: str, found_by: str | None = "the owner, 2026-09-04"):
    return document.model_copy(update={"intent": intent, "found_by": found_by})


def _link(kind: DocumentKind, stem: str, title: str) -> DocumentLink:
    return DocumentLink(kind=kind, stem=stem, title=title, archived=False)


def test_a_rename_that_changes_stem_and_title_keeps_the_card_when_git_says_so():
    """The #11/#18 incident: "the closed card…" became "the collapsed card…",
    stem and title both; the board birthed #18 and left #11 with nothing.
    Git recorded the rename (R081), and that is the first word after the
    title fails."""
    link = _link(DocumentKind.SUGGESTION, "closed", "The closed card")
    corpus = index(doc(DocumentKind.SUGGESTION, "collapsed", "The collapsed card"))
    asked: list[bool] = []

    def moves() -> dict[str, str]:
        asked.append(True)
        return {"docs/slice-suggestions/closed.md": "docs/slice-suggestions/collapsed.md"}

    effects = reconcile(corpus, [card(1, link)], moves=moves)
    assert [(r.card_number, r.old_stem, r.document.stem, r.how) for r in effects.renamed] == [
        (1, "closed", "collapsed", "git records the rename")
    ]
    assert effects.born == [], "no second card is born for the same document"
    assert asked == [True], "git is asked once per read, and only once a title has failed"


def test_git_is_not_asked_while_every_card_has_its_document():
    def moves() -> dict[str, str]:
        raise AssertionError("git was asked with nothing missing")

    corpus = index(doc(DocumentKind.SUGGESTION, "a", "a"))
    effects = reconcile(corpus, [card(1, _link(DocumentKind.SUGGESTION, "a", "a"))], moves=moves)
    assert effects.empty()


def test_a_chain_of_renames_is_followed_to_its_end():
    corpus = index(doc(DocumentKind.PLAN, "three", "Three"))
    moves = {"docs/plans/one.md": "docs/plans/two.md", "docs/plans/two.md": "docs/plans/three.md"}
    effects = reconcile(
        corpus, [card(1, _link(DocumentKind.PLAN, "one", "One"))], moves=lambda: moves
    )
    assert [(r.document.stem, r.how) for r in effects.renamed] == [
        ("three", "git records the rename")
    ]


def test_a_rename_git_did_not_see_is_matched_by_the_body_against_the_previous_read():
    """A file deleted and another written by hand, or a rename below git's
    similarity bar: the previous read still holds the old body, and the same
    Found-by line with the same intent is the same document."""
    link = _link(DocumentKind.SUGGESTION, "old", "Old words")
    before = index(_body(doc(DocumentKind.SUGGESTION, "old", "Old words"), "The board lied."))
    after = index(
        _body(doc(DocumentKind.SUGGESTION, "new", "New words"), "The board lied."),
        _body(doc(DocumentKind.SUGGESTION, "other", "Other"), "Something else."),
    )
    effects = reconcile(after, [card(1, link)], previous=before, moves=dict)
    assert [(r.document.stem, r.how) for r in effects.renamed] == [
        ("new", "its body is the one the board read before")
    ]
    assert [b.document.stem for b in effects.born] == ["other"]


def test_a_body_match_needs_the_same_found_by_line_and_a_body():
    link = _link(DocumentKind.SUGGESTION, "old", "Old")
    before = index(_body(doc(DocumentKind.SUGGESTION, "old", "Old"), "Same body."))
    other_finder = index(
        _body(doc(DocumentKind.SUGGESTION, "new", "New"), "Same body.", found_by="another")
    )
    assert reconcile(other_finder, [card(1, link)], previous=before).renamed == []
    emptied = index(_body(doc(DocumentKind.SUGGESTION, "old", "Old"), ""))
    empty = index(_body(doc(DocumentKind.SUGGESTION, "new", "New"), ""))
    assert reconcile(empty, [card(1, link)], previous=emptied).renamed == [], (
        "two empty bodies say nothing"
    )


def test_a_corpus_born_cards_face_follows_its_documents_title_and_an_imported_one_keeps_its_own():
    link = _link(DocumentKind.PLAN, "p", "Old title")
    corpus = index(doc(DocumentKind.PLAN, "p", "New title"))
    arrived = card(1, link).model_copy(update={"origin": CardOrigin.ARRIVED, "title": "Old title"})
    imported = card(2, link).model_copy(update={"title": "The owner's words"})
    effects = reconcile(corpus, [arrived, imported])
    assert [(r.card_number, r.title, r.was) for r in effects.retitled] == [
        (1, "New title", "Old title")
    ]
    same = card(3, link).model_copy(update={"origin": CardOrigin.FOUNDING, "title": "New title"})
    assert reconcile(corpus, [same]).retitled == []


def test_moved_to_and_corpus_path_of():
    assert moved_to({}, "docs/plans/a.md") is None
    loop = {"docs/plans/a.md": "docs/plans/b.md", "docs/plans/b.md": "docs/plans/a.md"}
    assert moved_to(loop, "docs/plans/a.md") == "docs/plans/b.md"
    assert corpus_path_of("docs/plans/done/2026-09-04-x.md") == (
        DocumentKind.PLAN,
        "2026-09-04-x",
        True,
    )
    assert corpus_path_of("docs/slice-suggestions/y.md") == (DocumentKind.SUGGESTION, "y", False)
    assert corpus_path_of("docs/plans/sub/z.md") is None
    assert corpus_path_of("docs/audits/a.md") is None


def test_a_finished_card_names_its_plan_once_where_the_plan_is():
    """Four of four archived cards checked on 2026-09-05 showed their plan
    twice — at done/ and at the live path the close moved it from. A
    citation follows the file; one whose file is nowhere is not shown; a
    path outside the corpus is the card's own word."""
    plan = doc(DocumentKind.PLAN, "p", "Plan", archived=True)
    carried = doc(DocumentKind.SUGGESTION, "s", "S", archived=True)
    corpus = CorpusIndex(documents=[plan, carried], read_at=AT)
    link = DocumentLink(kind=DocumentKind.PLAN, stem="p", title="Plan", archived=True)
    c = card(1, link)
    c.citations = [
        "docs/slice-suggestions/s.md",
        "docs/plans/p.md",
        "docs/plans/done/p.md",
        "docs/slice-suggestions/gone.md",
        "docs/audits/a.md",
    ]
    assert other_citations(c, corpus) == ["docs/slice-suggestions/done/s.md", "docs/audits/a.md"]
    lane, doors = nothing_read(c, "/srv/p", AT)
    detail = assemble_detail(c, corpus, [], AT, lane=lane, doors=doors, readings=[])
    assert detail.other_citations == ["docs/slice-suggestions/done/s.md", "docs/audits/a.md"]


def test_a_rename_straight_into_done_is_followed_and_git_is_not_asked_while_nothing_appeared():
    """A close that renames the plan as it archives it: the destination is an
    archived document that appeared since the previous read. And a card
    whose document is gone for good does not ask git on every read — only
    when something appeared that could be the answer."""
    link = _link(DocumentKind.PLAN, "old", "Old")
    done = doc(DocumentKind.PLAN, "new", "New", archived=True)
    long_archived = doc(DocumentKind.PLAN, "ancient", "Ancient", archived=True)
    before = index(long_archived)
    after = index(done, long_archived)
    moves = {"docs/plans/old.md": "docs/plans/done/new.md"}
    effects = reconcile(after, [card(1, link)], previous=before, moves=lambda: moves)
    assert [(r.document.path, r.how) for r in effects.renamed] == [
        ("docs/plans/done/new.md", "git records the rename")
    ]

    def never() -> dict[str, str]:
        raise AssertionError("git was asked with nothing new in the corpus")

    quiet = reconcile(before, [card(1, link)], previous=before, moves=never)
    assert quiet.renamed == [] and quiet.born == []
