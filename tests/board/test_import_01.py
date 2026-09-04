import copy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from board.import_01 import ImportRefused, read_01
from domain.card import Place
from domain.column import Column
from domain.document import DocumentKind
from domain.gate import Gate
from domain.row import RowKind
from infrastructure.corpus import scan

AT = datetime(2026, 9, 3, tzinfo=UTC)


def test_the_file_is_read_whole_and_the_owners_ranking_is_kept(
    card_file_01: dict[str, object], corpus: Path
):
    imported = read_01(card_file_01, scan(corpus, AT))
    numbers = [c.number for c in imported.cards]
    assert numbers == [
        252, 242, 232, 120, 105, 196, 109, 172, 253, 241, 228, 237, 174, 259, 223, 219, 147,
        139, 149, 134, 201,
    ]  # fmt: skip
    by = {c.number: c for c in imported.cards}
    assert by[120].place == Place(column=Column.BACKLOG, group="Next to plan", position=3)
    assert by[105].place == Place(column=Column.BACKLOG, group="Skipper-facing quality", position=0)
    assert by[253].place == Place(column=Column.UP_NEXT, group=None, position=0)
    assert [(g.column, g.name, g.position) for g in imported.groups][:4] == [
        (Column.BACKLOG, "Next to plan", 0),
        (Column.BACKLOG, "Season opening", 1),
        (Column.BACKLOG, "Skipper-facing quality", 2),
        (Column.PLANNED, "Season opening", 0),
    ]
    assert by[196].gate == Gate.HIGH and by[196].tags == ["Live sooner"]
    assert by[147].tags == ["Action", "Ruling"]


def test_rows_are_typed_and_their_html_is_turned_into_text(
    card_file_01: dict[str, object], corpus: Path
):
    imported = read_01(card_file_01, scan(corpus, AT))
    rows = {r.number: r.rows for r in imported.rows}
    assert [r.kind for r in rows[252]] == [RowKind.SERVES, RowKind.TODAY, RowKind.COST]
    assert rows[252][1].text == "It asks every **eight** seconds via `/api/quay`."


def test_citations_come_from_deep_and_the_first_document_is_the_link(
    card_file_01: dict[str, object], corpus: Path
):
    imported = read_01(card_file_01, scan(corpus, AT))
    by = {c.number: c for c in imported.cards}
    assert by[134].citations == [
        "docs/plans/done/2026-08-30-the-office-runs-its-own-checks.md",
        "docs/audits/2026-08-30-full-office-review.md",
    ]
    assert (
        by[134].link is not None
        and by[134].link.kind == DocumentKind.PLAN
        and by[134].link.archived
    )
    assert by[134].deep == "All seven items built."
    assert by[201].citations == [
        "docs/plans/done/2026-09-01-a-confirmed-booking-waits-for-the-tide.md"
    ]
    assert by[201].link is not None and by[201].link.title == ""
    assert by[228].link is None and by[228].citations == []


def test_a_malformed_citation_links_to_nowhere_rather_than_being_dropped(
    card_file_01: dict[str, object], corpus: Path
):
    imported = read_01(card_file_01, scan(corpus, AT))
    card = next(c for c in imported.cards if c.number == 120)
    assert card.link is not None
    assert card.link.kind == DocumentKind.SUGGESTION
    assert "·" in card.link.stem


def test_the_boards_own_asks_are_skipped_and_named(card_file_01: dict[str, object], corpus: Path):
    imported = read_01(card_file_01, scan(corpus, AT))
    assert [(a.number, a.alarm) for a in imported.skipped_asks] == [
        (204, "suggestion-without-card")
    ]
    assert 204 not in [c.number for c in imported.cards]


def test_retired_numbers_and_the_next_number_carry_over(
    card_file_01: dict[str, object], corpus: Path
):
    imported = read_01(card_file_01, scan(corpus, AT))
    assert [(r.number, r.reason) for r in imported.retired] == [
        (123, "parked into #167"),
        (140, "merged into #135"),
    ]
    assert imported.next_number == 262


def test_the_next_number_never_falls_below_the_highest_card(
    card_file_01: dict[str, object], corpus: Path
):
    payload = copy.deepcopy(card_file_01)
    payload["nextId"] = 5
    assert read_01(payload, scan(corpus, AT)).next_number == 260


def test_an_unknown_row_label_refuses_the_whole_import(
    card_file_01: dict[str, object], corpus: Path
):
    payload = copy.deepcopy(card_file_01)
    payload["cols"][0]["groups"][0]["cards"][0]["b"].append(["GATE", "high"])
    with pytest.raises(ImportRefused, match='row labelled "GATE"'):
        read_01(payload, scan(corpus, AT))


def test_a_gate_outside_the_rubric_is_refused(card_file_01: dict[str, object], corpus: Path):
    payload = copy.deepcopy(card_file_01)
    payload["cols"][1]["groups"][0]["cards"][0]["gate"] = "enormous"
    with pytest.raises(ImportRefused, match='gate "enormous"'):
        read_01(payload, scan(corpus, AT))


def test_an_unknown_tag_letter_or_column_or_duplicate_is_refused(
    card_file_01: dict[str, object], corpus: Path
):
    payload = copy.deepcopy(card_file_01)
    payload["cols"][1]["groups"][0]["cards"][0]["ch"] = ["Z"]
    with pytest.raises(ImportRefused, match='tag letter "Z"'):
        read_01(payload, scan(corpus, AT))
    payload = copy.deepcopy(card_file_01)
    payload["cols"][1]["name"] = "Someday"
    with pytest.raises(ImportRefused, match='column named "Someday"'):
        read_01(payload, scan(corpus, AT))
    payload = copy.deepcopy(card_file_01)
    payload["cols"][3]["groups"][0]["cards"].append(
        copy.deepcopy(payload["cols"][2]["groups"][0]["cards"][0])
    )
    with pytest.raises(ImportRefused, match="appears twice"):
        read_01(payload, scan(corpus, AT))


def test_a_file_in_another_shape_is_refused():
    with pytest.raises(ImportRefused, match="not in 0.1's shape"):
        read_01({"cards": []}, scan(Path("/nonexistent"), AT))
