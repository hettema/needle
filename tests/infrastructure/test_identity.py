"""A card keeps its number and its history through a rename that changes
stem and title, and its face follows its document (plan 08, item 1), read
end to end through `sweep` against a corpus on disk."""

from pathlib import Path

from domain.audit import AuditKind
from domain.card import CardOrigin
from domain.column import Column
from infrastructure.live import sweep
from infrastructure.store import Store
from tests.conftest import NOW, write_plan, write_suggestion


def test_a_rename_that_changes_stem_and_title_keeps_the_card_and_its_history(
    store: Store, project, corpus: Path
):
    """The #11/#18 incident, replayed: the suggestion's stem and title both
    change; git has not seen it (a rename by hand); the previous read has.
    One card, the new document, the old history, and no new card."""
    store.add_project(project)
    old = write_suggestion(
        corpus, "2026-09-04-the-closed-card", title="The closed card", intent="It lied."
    )
    before, effects = sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    number = next(c.number for c in store.cards("proj") if c.title == "The closed card")
    old.unlink()
    write_suggestion(
        corpus, "2026-09-04-the-collapsed-card", title="The collapsed card", intent="It lied."
    )
    after, effects = sweep(
        store, project, origin=CardOrigin.ARRIVED, at=NOW, previous=before, renames_of=lambda _: {}
    )
    assert [(r.card_number, r.how) for r in effects.renamed] == [
        (number, "its body is the one the board read before")
    ]
    assert effects.born == []
    card = store.card("proj", number)
    assert card is not None and card.link is not None
    assert card.link.stem == "2026-09-04-the-collapsed-card"
    assert card.title == "The collapsed card", "the face follows the document"
    history = store.history("proj", number)
    assert [h.kind for h in history][-2:] == [AuditKind.RENAMED, AuditKind.BORN]
    assert "renamed from 2026-09-04-the-closed-card to 2026-09-04-the-collapsed-card" in (
        history[0].detail
    )
    assert 'it read "The closed card"' in history[0].detail
    assert not any(
        c.title == "The collapsed card" and c.number != number for c in store.cards("proj")
    )


def test_the_face_follows_the_document_it_cites_through_a_carry_and_an_edit(
    store: Store, project, corpus: Path
):
    """#34 read its suggestion's working title for a day after plan 11
    carried it (2026-09-05): the card is the plan's, and its face says so.
    An edit to the title in place follows on the next read, with the old
    title kept in the history."""
    store.add_project(project)
    write_suggestion(corpus, "2026-09-04-a-standing-ruling", title="A standing ruling")
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    number = next(c.number for c in store.cards("proj") if c.title == "A standing ruling")
    write_plan(
        corpus,
        "2026-09-04-11-defects-fix-themselves",
        title="Defects fix themselves",
        extra="**Carries:** docs/slice-suggestions/2026-09-04-a-standing-ruling.md\n",
    )
    sweep(store, project, origin=CardOrigin.ARRIVED, at=NOW)
    card = store.card("proj", number)
    assert card is not None and card.title == "Defects fix themselves"
    assert card.place.column == Column.PLANNED
    linked = next(h for h in store.history("proj", number) if h.kind == AuditKind.LINKED)
    assert 'it read "A standing ruling"' in linked.detail
    plan = corpus / "docs" / "plans" / "2026-09-04-11-defects-fix-themselves.md"
    plan.write_text(
        plan.read_text(encoding="utf-8").replace(
            "# Defects fix themselves", "# Defects fix themselves without him"
        ),
        encoding="utf-8",
    )
    effects = sweep(store, project, origin=CardOrigin.ARRIVED, at=NOW)[1]
    assert [(r.card_number, r.was) for r in effects.retitled] == [
        (number, "Defects fix themselves")
    ]
    card = store.card("proj", number)
    assert card is not None and card.title == "Defects fix themselves without him"
    retitled = store.history("proj", number)[0]
    assert retitled.kind == AuditKind.RETITLED and 'it read "Defects fix themselves"' in (
        retitled.detail
    )
