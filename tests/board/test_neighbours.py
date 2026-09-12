"""A live document is read against the other live documents of its project
(card #69, item 1): who sits beside it on its ground, whether it names them,
and — for a document naming no ground — the nearest by words, said as
candidates. The head counts only a file neighbour a document born after the
reader does not name; words are retrieval, never a verdict (ruling 3)."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from board import neighbours
from board.neighbours import (
    Corpus,
    beside_all,
    clears_of,
    sentence_of,
    words_of,
)
from board.parse import parse_document
from domain.card import Card, CardOrigin, Place
from domain.column import Column
from domain.document import Document, DocumentKind
from domain.neighbour import NeighbourGround

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent.parent / "fixtures" / "harbourmaster"


def card(number: int, born: datetime = NOW) -> Card:
    return Card(
        number=number,
        project="harbourmaster",
        place=Place(column=Column.BACKLOG, group=None, position=0),
        title=f"Card {number}",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=None,
        origin=CardOrigin.ARRIVED,
        born_at=born,
        rows=[],
    )


def plan(stem: str, text: str) -> Document:
    return parse_document(
        text, kind=DocumentKind.PLAN, path=f"docs/plans/{stem}.md", archived=False, read_at=NOW
    )


def suggestion(stem: str, text: str) -> Document:
    return parse_document(
        text,
        kind=DocumentKind.SUGGESTION,
        path=f"docs/slice-suggestions/{stem}.md",
        archived=False,
        read_at=NOW,
    )


def fixture_pairs() -> list[tuple[Card, Document]]:
    """The Harbourmaster corpus with one card per live document, numbered in
    folder order — the plans first, as the fixture's own card file does."""
    pairs: list[tuple[Card, Document]] = []
    number = 0
    for kind, folder in (
        (DocumentKind.PLAN, "docs/plans"),
        (DocumentKind.SUGGESTION, "docs/slice-suggestions"),
    ):
        for file in sorted((FIXTURE / folder).glob("*.md")):
            if file.name.upper() == "README.MD":
                continue
            number += 1
            document = parse_document(
                file.read_text(encoding="utf-8"),
                kind=kind,
                path=f"{folder}/{file.name}",
                archived=False,
                read_at=NOW,
            )
            pairs.append((card(number), document))
    return pairs


def by_stem(pairs: list[tuple[Card, Document]], stem: str) -> Card:
    return next(c for c, d in pairs if d.stem == stem)


def padding(count: int, first: int) -> list[tuple[Card, Document]]:
    """Unrelated documents that make a board big enough for the glue cut
    to mean something: on a board of forty, a word six share is glue."""
    return [
        (
            card(first + i),
            plan(
                f"pad{i}",
                f"# Padding {i}\n\n## Intent\n\nFiller number {i} about pad{i}.\n\n"
                f"## Terrain\n\n`pad/file{i}.py`\n",
            ),
        )
        for i in range(count)
    ]


def test_the_words_of_a_text_are_its_rare_nouns_stemmed_once():
    assert words_of("The cards are priced; the skipper's berths") == {
        "card",
        "priced",
        "skipper",
        "berth",
    }
    assert words_of(None, "") == set()


def test_a_suggestion_naming_a_file_a_live_plans_terrain_names_sits_beside_that_plan():
    # The fixture: the slip defect names office/pricing.py, which two live
    # pricing plans name in their Terrain; none of the three names another.
    pairs = fixture_pairs()
    read = beside_all(pairs)
    slip = by_stem(pairs, "2026-09-05-the-slip-shows-last-months-price")
    see = by_stem(pairs, "2026-09-02-the-skipper-sees-the-price-before-the-berth")
    judged = by_stem(pairs, "2026-09-02-the-pricing-rule-judged-against-a-real-season")
    beside = read[slip.number]
    assert [(n.number, n.ground, n.files, n.named) for n in beside.neighbours] == [
        (judged.number, NeighbourGround.FILES, ["office/pricing.py"], False),
        (see.number, NeighbourGround.FILES, ["office/pricing.py"], False),
    ]
    assert beside.neighbours[0].essence.startswith("A season's real bookings say")
    assert beside.unnamed == [judged.number, see.number]
    assert beside.sentence == (
        f"sits beside #{judged.number}, #{see.number} on office/pricing.py and does not name "
        "them."
    )
    # A defect's count is cleared by the reading that verifies its mark.
    assert beside.counted and beside.clears is not None
    assert beside.clears.startswith("the reading that verifies its mark folds it into")
    # The plan sits beside the defect and the other plan the same way, and
    # its row names the act a session on it can do.
    assert [n.number for n in read[see.number].neighbours] == [judged.number, slip.number]
    assert read[see.number].clears is not None
    assert read[see.number].clears.startswith("a session on it cites")
    assert "Discuss it" in read[see.number].clears


def test_a_suggestion_naming_no_file_shows_the_nearest_by_words_as_a_candidate():
    pairs = fixture_pairs()
    read = beside_all(pairs)
    forgets = by_stem(pairs, "2026-09-01-the-waiting-list-forgets-who-asked-first")
    offers = by_stem(pairs, "2026-09-01-the-waiting-list-offers-every-berth-that-fits")
    beside = read[forgets.number]
    assert [(n.number, n.ground) for n in beside.neighbours] == [
        (offers.number, NeighbourGround.WORDS)
    ]
    assert set(beside.neighbours[0].words) >= {"waiting", "list", "asked"}
    # A candidate is never counted, and the sentence says it is one.
    assert beside.unnamed == [] and not beside.counted and beside.clears is None
    assert beside.sentence == f"near #{offers.number} by its words — a candidate, not a verdict."
    # A document with nothing near it sits beside nothing at all.
    kilowatt = by_stem(pairs, "2026-09-03-every-metered-kilowatt-is-billed")
    assert read[kilowatt.number].neighbours == [] and read[kilowatt.number].sentence is None


def test_a_document_that_carries_or_cites_the_neighbour_clears_the_count():
    a = plan("a", "# A\n\n**Effort gate:** low — x\n\n## Intent\n\nOne.\n\n## Terrain\n\n`x/y.py`\n")
    # Cites the neighbour's card in prose.
    b = plan("b", "# B\n\n## Intent\n\nBeside #1, whole without it.\n\n## Terrain\n\n`x/y.py`\n")
    # Carries the neighbour by a plain path, no backticks.
    c = plan(
        "c",
        "# C\n\n**Carries:** docs/slice-suggestions/d.md\n\n## Intent\n\nTwo.\n\n"
        "## Terrain\n\n`x/y.py` and `x/z.py`\n",
    )
    d = suggestion("d", "# D\n\n**Kind:** idea\n\n## Observation\n\nSeen in `x/z.py`.\n")
    # Names the neighbour on its Sequencing line.
    e = plan("e", "# E\n\n**Sequencing:** after #1.\n\n## Intent\n\nThree.\n\n## Terrain\n\n`x/w.py`\n")
    f = plan("f", "# F\n\n## Intent\n\nFour.\n\n## Terrain\n\n`x/w.py`\n")
    pairs = [(card(1), a), (card(2), b), (card(3), c), (card(4), d), (card(5), e), (card(6), f)]
    read = beside_all(pairs + padding(30, 10))
    assert read[1].unnamed == [2, 3]
    assert read[2].unnamed == [3] and [n.number for n in read[2].neighbours if n.named] == [1]
    assert [n.number for n in read[3].neighbours if n.named] == [4]
    assert read[3].unnamed == [1, 2]
    assert read[4].unnamed == [3]
    assert read[5].unnamed == [6] and read[5].neighbours[0].files == ["x/w.py"]
    # The Sequencing name is read by its own parser, not by the `#N` in prose
    # alone: a card no board holds is still named.
    assert e.sequenced[0].number == 1 and 1 in e.named_cards


def test_a_path_or_a_word_nearly_every_document_shares_is_glue_not_ground():
    # Seven of forty-two plans name the same core file; two of them share a rarer one.
    documents = [
        plan(
            f"p{i}",
            f"# Plan {i}\n\n## Intent\n\nSomething about topic {i}.\n\n## Terrain\n\n"
            "`api/loops.py`" + (" and `runtime/rule.py`" if i < 2 else "") + "\n",
        )
        for i in range(7)
    ]
    pairs = [(card(i + 1), d) for i, d in enumerate(documents)] + padding(35, 10)
    read = beside_all(pairs)
    assert [n.number for n in read[1].neighbours] == [2]
    assert read[1].neighbours[0].files == ["runtime/rule.py"]
    assert read[3].neighbours == []
    # Five namers are always ground, whatever the board's size.
    small = beside_all(pairs[:5] + padding(3, 10))
    assert [n.number for n in small[3].neighbours] == [1, 2, 4, 5]
    # A word seven of forty-two use weighs nothing; a rare shared pair is a candidate.
    documents = [
        suggestion(
            f"s{i}",
            f"# Idea {i}\n\n**Kind:** idea\n\n## Observation\n\nThe pontoon "
            + ("shows the skipper the tariff at dusk." if i < 2 else f"does thing {i}.")
            + "\n",
        )
        for i in range(7)
    ]
    pairs = [(card(i + 1), d) for i, d in enumerate(documents)] + padding(35, 10)
    read = beside_all(pairs)
    assert [n.number for n in read[1].neighbours] == [2]
    assert "pontoon" not in read[1].neighbours[0].words
    assert read[4].neighbours == []


def test_word_candidates_are_the_nearest_few_in_a_fixed_order():
    rare = "The lighthouse keeper's ledger of foghorn tests."
    documents = [suggestion("mine", f"# Mine\n\n**Kind:** idea\n\n## Observation\n\n{rare}\n")]
    for i in range(6):
        documents.append(
            suggestion(
                f"o{i}",
                f"# Other {i}\n\n**Kind:** idea\n\n## Observation\n\n"
                + (rare if i % 2 == 0 else f"A foghorn ledger, number {i}.")
                + "\n",
            )
        )
    # Sixty-seven documents: a word four share is ground, one seven share is glue.
    pairs = [(card(i + 1), d) for i, d in enumerate(documents)] + padding(60, 10)
    beside = beside_all(pairs)[1]
    assert len(beside.neighbours) == neighbours.SHOWN
    # The full-match documents (2, 4, 6) outscore the partial ones; ties by number.
    assert [n.number for n in beside.neighbours] == [2, 4, 6]
    # The same words, read for a line typed at a door, find the same candidates.
    corpus = Corpus(pairs)
    typed = corpus.by_words(words_of("a ledger of foghorn tests kept by the lighthouse keeper"))
    assert [n.number for n in typed] == [1, 2, 4]
    assert corpus.by_words(words_of("nothing here at all")) == []


def test_only_a_document_born_after_the_reader_counts(monkeypatch: pytest.MonkeyPatch):
    a = plan("a", "# A\n\n## Intent\n\nOne.\n\n## Terrain\n\n`x/y.py`\n")
    b = plan("b", "# B\n\n## Intent\n\nTwo.\n\n## Terrain\n\n`x/y.py`\n")
    old = datetime(2026, 9, 1, tzinfo=UTC)
    read = beside_all([(card(1, born=old), a), (card(2), b)])
    assert read[1].unnamed == [2] and not read[1].counted and read[1].clears is None
    assert read[1].born == date(2026, 9, 1)
    assert read[2].unnamed == [1] and read[2].counted and read[2].clears is not None
    monkeypatch.setattr(neighbours, "COUNTED_FROM", date(2026, 8, 1))
    assert beside_all([(card(1, born=old), a), (card(2), b)])[1].counted


def test_the_sentence_and_the_row_say_who_and_what():
    a = plan("a", "# A\n\n## Intent\n\nOne.\n\n## Terrain\n\n`x/y.py`\n")
    named = neighbours._neighbour(
        7, a, ground=NeighbourGround.FILES, files=["x/y.py"], words=[], named=True
    )
    unnamed = named.model_copy(update={"number": 9, "named": False})
    words = neighbours._neighbour(
        11, a, ground=NeighbourGround.WORDS, files=[], words=["tide"], named=False
    )
    assert sentence_of([named, unnamed, words]) == (
        "sits beside #9 on x/y.py and does not name it; names #7 beside it on x/y.py; "
        "near #11 by its words — a candidate, not a verdict."
    )
    assert sentence_of([]) is None
    defect = suggestion("d", "# D\n\n**Kind:** defect\n\n## Observation\n\nx\n")
    assert clears_of(defect, [9]) == (
        "the reading that verifies its mark folds it into #9 or cites #9 in the file"
    )
    assert clears_of(a, [7, 9]) == (
        "a session on it cites #7, #9, carries #7, #9, or folds this card into #7, #9 — "
        "Discuss it and it can"
    )
