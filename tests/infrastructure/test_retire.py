"""A card the board should never have born is retired into the card that
carries its document (plan 08, item 1): Needle's #11 into #18, omarchy's
#13 into #15, the two incidents the rename detector now prevents."""

import pytest

from domain.audit import AuditKind
from domain.card import Actor, CardOrigin
from domain.lane import LaneRecord
from domain.row import Row, RowKind
from infrastructure.live import Live, sweep
from infrastructure.store import Store, StoreRefusal
from tests.conftest import NOW, write_suggestion


def _two_cards(store: Store, project, corpus) -> tuple[Live, int, int]:
    """Two cards born from two suggestions, then the first's document
    vanishes as a rename by hand the board could not follow."""
    store.add_project(project)
    old = write_suggestion(corpus, "2026-09-04-the-closed-card", title="The closed card")
    write_suggestion(corpus, "2026-09-04-the-collapsed-card", title="The collapsed card")
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    by_title = {c.title: c.number for c in store.cards("proj")}
    old_number, new_number = by_title["The closed card"], by_title["The collapsed card"]
    store.add_row(
        "proj", old_number, Row(kind=RowKind.RULING, text="the old ruling"), Actor.OWNER, NOW
    )
    store.add_row(
        "proj", old_number, Row(kind=RowKind.DELIVERED, text="old delivered"), Actor.SESSION, NOW
    )
    store.add_row(
        "proj", new_number, Row(kind=RowKind.DELIVERED, text="new delivered"), Actor.SESSION, NOW
    )
    live = Live(store, now=lambda: NOW)
    live.load()
    old.unlink()
    live.rescan("proj")
    return live, old_number, new_number


def test_a_card_whose_document_is_in_the_corpus_is_not_a_duplicate(store: Store, project, corpus):
    live, old_number, new_number = _two_cards(store, project, corpus)
    with pytest.raises(StoreRefusal, match="is in the corpus, so it is a card of its own"):
        live.retire("proj", new_number, old_number, "no")
    with pytest.raises(StoreRefusal, match="into itself"):
        live.retire("proj", old_number, old_number, "no")


def test_a_retired_cards_rows_and_history_read_on_the_survivor_and_its_number_says_where(
    store: Store, project, corpus
):
    live, old_number, new_number = _two_cards(store, project, corpus)
    before = store.history("proj", old_number)
    assert [h.kind for h in before][-1] == AuditKind.BORN
    old_card = store.card("proj", old_number)
    assert old_card is not None
    mates = [c for c in store.cards("proj") if c.place.column == old_card.place.column]
    group_mates = [c.number for c in mates if c.place.group == old_card.place.group]
    survivor = live.retire(
        "proj", old_number, new_number, "its document was renamed into this card's on 2026-09-04."
    )
    assert store.card("proj", old_number) is None
    assert [(r.kind, r.text) for r in survivor.rows] == [
        (RowKind.DELIVERED, "new delivered"),
        (RowKind.RULING, "the old ruling"),
    ], "rows move over; a one-per-card kind the survivor has stays in the audit line"
    history = store.history("proj", new_number)
    kinds = [h.kind for h in history]
    assert kinds.count(AuditKind.BORN) == 1, "the retired card's lines are quoted, never adopted"
    absorbed = history[0]
    assert absorbed.kind == AuditKind.RETIRED and f"Absorbed #{old_number}" in absorbed.detail
    assert "Its rows RULING moved onto this card" in absorbed.detail
    assert "Not carried, this card already has one: DELIVERED: old delivered" in absorbed.detail
    assert "renamed into this card's" in absorbed.detail
    assert f"Its history, {len(before)} lines:" in absorbed.detail
    assert "born: Born from docs/slice-suggestions/2026-09-04-the-closed-card.md" in absorbed.detail
    left = store.history("proj", old_number)
    assert [h.kind for h in left][0] == AuditKind.RETIRED and len(left) == len(before) + 1
    assert f"Retired into #{new_number}" in left[0].detail and left[0].from_place is not None
    placed = store.placements("proj")
    assert old_number not in placed or placed[old_number].card_number == old_number
    assert placed[new_number].card_number == new_number and placed[new_number].kind == (
        AuditKind.BORN
    ), "the survivor's placement is its own, not a line adopted from the retired card"
    remaining = [
        c
        for c in store.cards("proj")
        if c.place.column == old_card.place.column and c.place.group == old_card.place.group
    ]
    assert sorted(c.place.position for c in remaining) == list(range(len(group_mates) - 1)), (
        "the group's positions close up"
    )
    assert live.detail("proj", new_number).card.number == new_number


def test_a_card_with_a_lane_or_a_reading_is_not_retired(store: Store, project, corpus):
    live, old_number, new_number = _two_cards(store, project, corpus)
    store.record_lane(
        LaneRecord(
            project="proj",
            card_number=old_number,
            name="card-x",
            path="/srv/x",
            branch=None,
            birth=None,
            tip=None,
            first_seen=NOW,
            last_seen=NOW,
            gone_at=None,
            folded_at=None,
            trunk_synced_at=None,
            main_synced_at=None,
        )
    )
    with pytest.raises(StoreRefusal, match="not a duplicate the board can retire: it has a lane"):
        live.retire("proj", old_number, new_number, "no")
    assert store.card("proj", old_number) is not None
