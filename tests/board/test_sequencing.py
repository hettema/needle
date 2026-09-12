"""The one reason a Start waits on another card is the plan's own word (the
plan "as many lanes as the machine can hold", item 2): the Sequencing line's
leading card names, read by the parser and placed by the board. The lines
here are the real corpora's, read on 2026-09-05, so the reading that held
nothing falsely there keeps holding nothing falsely."""

from datetime import UTC, datetime

from board.parse import parse_document, sequenced_cards_of
from board.sequencing import holding, waits_for
from domain.card import Card, CardOrigin, Place
from domain.column import Column
from domain.document import DocumentKind, SequencedCard

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
PROJECTS = {"hellorevenue": "Hello Revenue", "needle": "Needle", "omarchy": "Omarchy"}


def named(*pairs: tuple[str | None, int]) -> list[SequencedCard]:
    return [SequencedCard(words=words, number=number) for words, number in pairs]


def test_the_names_lead_and_the_prose_follows():
    # Hello Revenue, 2026-09-03: two dependencies, then prose naming two more cards.
    line = (
        "after card #222 (shipped 2026-09-02, main synced), and after card #235 (an undefined "
        "name cannot ship) folds — it fixes the two crash paths this planning found; the owner "
        "ruled 2026-09-03 that the crash paths ship first. Card #228 (Ava and the analyst are "
        "told what the author wrote) ships BEFORE the Ava seam here. Card #219's fork 2 is "
        "sequenced after this plan by owner ruling."
    )
    assert sequenced_cards_of(line) == named((None, 222), (None, 235))
    # Hello Revenue #411: two other boards' cards, each with a parenthesis.
    line = (
        "after omarchy #17 (the shared skill this repo's skills will cite) and Needle #20 "
        "(Needle's plan 08, whose item 2 makes `needle close` refuse an unstanced promise for "
        "every project). Item 1 is the check: the lane reads both cards at launch."
    )
    assert sequenced_cards_of(line) == named(("omarchy", 17), ("Needle", 20))
    # Harbourmaster: one card, then prose.
    assert sequenced_cards_of("after #139, the four berth-first rulings.") == named((None, 139))
    # A two-word project name.
    assert sequenced_cards_of("Hello Revenue #411 first") == named(("Hello Revenue", 411))


def test_a_line_that_does_not_lead_with_a_name_names_nothing():
    # Hello Revenue #386: a card named mid-sentence, describing shared ground, not an order.
    line = (
        "the lane's migration takes the next free revision at its start (`210` if the head has "
        "not moved) and re-numbers on rebase; the live plan for #384 (docs/plans/x.md) also "
        'takes "the next free head" for its rename migration.'
    )
    assert sequenced_cards_of(line) == []
    assert sequenced_cards_of("independent of every open card.") == []
    assert sequenced_cards_of("none. The one live lane (card-379) is at its close.") == []
    assert sequenced_cards_of("beside 15 and 16 (all three touch `api/loops.py`).") == []
    assert sequenced_cards_of("after 07. Independent of the page.") == []
    assert sequenced_cards_of(None) == [] and sequenced_cards_of("") == []
    # "beside #15" reaches the board as a name with the word "beside" on it;
    # the board, not the parser, says that word is nobody's project.
    assert sequenced_cards_of("beside #15 (both add a call in `api/loops.py`)") == named(
        ("beside", 15)
    )


def test_a_suggestion_names_nothing_and_a_plan_reads_its_head_line():
    plan = parse_document(
        "# A plan\n\n**Status:** PENDING\n**Sequencing:** after #139, the four rulings.\n\n"
        "## Intent\n\nx\n",
        kind=DocumentKind.PLAN,
        path="docs/plans/p.md",
        archived=False,
        read_at=NOW,
    )
    assert plan.sequenced == named((None, 139))
    suggestion = parse_document(
        "# A defect\n\n**Kind:** defect\n**Fix:** now\n**Sequencing:** after #139.\n\n"
        "## Observation\n\nx\n",
        kind=DocumentKind.SUGGESTION,
        path="docs/slice-suggestions/s.md",
        archived=False,
        read_at=NOW,
    )
    assert suggestion.sequenced == []


def card(project: str, number: int, column: Column) -> Card:
    return Card(
        number=number,
        project=project,
        place=Place(column=column, group=None, position=0),
        title=f"Card {number}",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=None,
        origin=CardOrigin.ARRIVED,
        born_at=NOW,
        rows=[],
    )


BOARDS = {
    ("hellorevenue", 222): card("hellorevenue", 222, Column.DONE),
    ("hellorevenue", 235): card("hellorevenue", 235, Column.EXECUTED),
    ("hellorevenue", 411): card("hellorevenue", 411, Column.UP_NEXT),
    ("omarchy", 17): card("omarchy", 17, Column.UP_NEXT),
    ("needle", 20): card("needle", 20, Column.UP_NEXT),
    ("needle", 15): card("needle", 15, Column.PLANNED),
}


def find(slug: str, number: int) -> Card | None:
    return BOARDS.get((slug, number))


def test_the_board_places_each_name_and_says_which_still_hold():
    # The same-author plan: both named cards shipped, so nothing holds.
    waits = waits_for(
        named((None, 222), (None, 235)), here="hellorevenue", projects=PROJECTS, find=find
    )
    assert [(w.label, w.column, w.shipped) for w in waits] == [
        ("#222", Column.DONE, True),
        ("#235", Column.EXECUTED, True),
    ]
    assert holding(waits) == []
    # Hello Revenue #411: two other boards, both still in Up next, so both hold.
    waits = waits_for(
        named(("omarchy", 17), ("Needle", 20)), here="hellorevenue", projects=PROJECTS, find=find
    )
    assert [(w.label, w.project, w.column) for w in waits] == [
        ("Omarchy #17", "omarchy", Column.UP_NEXT),
        ("Needle #20", "needle", Column.UP_NEXT),
    ]
    assert [w.number for w in holding(waits)] == [17, 20]
    # A project by its two-word name, and a possessive.
    assert (
        waits_for(named(("Hello Revenue", 411)), here="needle", projects=PROJECTS, find=find)[
            0
        ].project
        == "hellorevenue"
    )
    assert (
        waits_for(named(("Needle's", 20)), here="omarchy", projects=PROJECTS, find=find)[0].project
        == "needle"
    )
    # A card nobody has: on the board's word it holds, and the face says where it is not.
    missing = waits_for(named((None, 999)), here="needle", projects=PROJECTS, find=find)
    assert missing[0].column is None and not missing[0].shipped


def test_words_that_name_no_project_end_the_reading():
    """ "beside #15" is prose about running alongside, never a hold; and so
    is every name after the first the board cannot place."""
    assert waits_for(named(("beside", 15)), here="needle", projects=PROJECTS, find=find) == []
    waits = waits_for(
        named((None, 20), ("beside", 15), (None, 222)), here="needle", projects=PROJECTS, find=find
    )
    assert [w.number for w in waits] == [20]


def test_a_line_that_means_a_hold_the_board_cannot_place_says_which_names():
    """Card #69, item 4: the loose reading keeps the names the grammar loses
    after a hold word — a bare plan number, `plan N`, a project no board
    holds — and the board says which it cannot place, so the writer's hold
    is loud instead of silently never holding. A `#N` no board holds yet is
    placed (it holds today, the shape of a card not born), and a line that
    leads with no hold word — "beside #15" — is shared ground, never a hold."""
    from board.parse import held_names_of
    from board.sequencing import unplaced

    assert held_names_of("after 08 and 11 (the two pricing plans).") == ["08", "11"]
    assert held_names_of("after 07. Independent of the page.") == ["07"]
    assert held_names_of("after plan 08 (the map) and #12") == ["plan 08", "#12"]
    assert held_names_of("after HR #409 and #123") == ["HR #409", "#123"]
    assert held_names_of("after omarchy #17 (the shared skill) and Needle #20 (plan 08).") == [
        "omarchy #17",
        "Needle #20",
    ]
    assert held_names_of("depends on 12") == ["12"]
    # A quantity after a hold word is not a plan number: what follows a bare
    # number has to be the end, a separator, filler or another name.
    for prose in (
        "after 2 ChatGPT accounts exist",
        "after 50 builds have run",
        "once 10 clients are live",
        "after 3 weeks of the signal",
        "waits on 2 of the boards being level",
        "after the 5 GB floor lands",
    ):
        assert held_names_of(prose) == [], prose
    assert held_names_of("after 12 (the reader) and 13 (the item read)") == ["12", "13"]
    assert held_names_of("beside #15 (both add a call in `api/loops.py`)") == []
    assert held_names_of("beside 15 and 16 (all three touch `api/loops.py`).") == []
    assert held_names_of("Hello Revenue #411 first") == []
    assert held_names_of("after 2026-09-05 folds") == []
    assert held_names_of("independent of every open card.") == []
    assert held_names_of(None) == [] and held_names_of("") == []

    placed = dict(here="needle", projects=PROJECTS)
    assert unplaced(["08", "11"], **placed) == ["08", "11"]
    assert unplaced(["plan 08", "#12"], **placed) == ["plan 08"]
    assert unplaced(["HR #409", "#123"], **placed) == ["HR #409"]
    assert unplaced(["omarchy #17", "Needle #20", "#999"], **placed) == []
    plan = parse_document(
        "# A plan\n\n**Status:** PENDING\n**Sequencing:** after 08 and 11.\n\n## Intent\n\nx\n",
        kind=DocumentKind.PLAN,
        path="docs/plans/p.md",
        archived=False,
        read_at=NOW,
    )
    assert plan.sequenced == [] and plan.held_names == ["08", "11"]
