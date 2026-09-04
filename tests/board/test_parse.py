from datetime import UTC, date, datetime

from board.parse import essence_of, parse_document
from domain.document import DocumentKind
from domain.gate import Gate

AT = datetime(2026, 9, 3, tzinfo=UTC)


def parse(
    text: str,
    kind: DocumentKind = DocumentKind.PLAN,
    path: str = "docs/plans/2026-09-03-a-thing.md",
    archived: bool = False,
):
    return parse_document(text, kind=kind, path=path, archived=archived, read_at=AT)


def test_a_plan_head_is_read_whole():
    document = parse(
        "# Every metered kilowatt is billed\n\n"
        "**Status:** PENDING — written 2026-09-03 from the owner's read.\n"
        "**Effort gate:** medium — the fix is one parser and two call sites.\n"
        "**Origin:** the meter alerts.\n"
        "**Sequencing:** independent of every open card.\n"
        "**Card:** #253 (Up next).\n\n---\n\n## Intent\n\nPower truth. Every kilowatt lands.\n\n"
        "## Terrain\n\nx\n"
    )
    assert document.title == "Every metered kilowatt is billed"
    assert document.status_word == "PENDING"
    assert document.status is not None and document.status.startswith("PENDING — written")
    assert document.gate == Gate.MEDIUM
    assert document.gate_why == "the fix is one parser and two call sites."
    assert document.sequencing == "independent of every open card."
    assert document.card_ref == 253
    assert [f.key for f in document.head_fields] == [
        "Status",
        "Effort gate",
        "Origin",
        "Sequencing",
        "Card",
    ]
    assert document.intent_heading == "Intent"
    assert document.intent == "Power truth. Every kilowatt lands."
    assert document.essence == "Power truth."
    assert document.date == date(2026, 9, 3)
    assert document.stem == "2026-09-03-a-thing"


def test_the_intent_heading_is_found_under_its_corpus_variants():
    for heading in (
        "Intent — what this achieves and why",
        "1. Intent",
        'Intent (defines "done")',
        "The intent",
    ):
        document = parse(f"# T\n\n## Context\n\nBackground.\n\n## {heading}\n\nThe point.\n")
        assert document.intent_heading == heading, heading
        assert document.intent == "The point."


def test_without_an_intent_heading_the_first_section_stands_in():
    document = parse(
        "# T\n\n**Found by:** a review\n\n## Observation\n\nSeen. Twice.\n\n## Fix\n\nDo.\n",
        kind=DocumentKind.SUGGESTION,
    )
    assert document.intent_heading == "Observation"
    assert document.essence == "Seen."


def test_a_headless_document_still_has_an_essence():
    document = parse("# T\n\n**Status:** DONE\n\nJust prose, no sections. More prose.\n")
    assert document.intent_heading is None
    assert document.essence == "Just prose, no sections."


def test_a_multi_line_head_field_is_joined():
    document = parse(
        "# T\n\n**Found by:** the review of card #249\n"
        "(`docs/reviews/x.md`, finding 1), carried out.\n\n## Observation\n\nx\n",
        kind=DocumentKind.SUGGESTION,
    )
    assert (
        document.found_by
        == "the review of card #249 (`docs/reviews/x.md`, finding 1), carried out."
    )


def test_the_gate_is_read_in_any_case_and_keeps_its_why():
    assert parse("# T\n\n**Effort gate:** High — judgement\n\n## Intent\n\nx\n").gate == Gate.HIGH
    assert parse("# T\n\n**Effort gate:** xhigh\n\n## Intent\n\nx\n").gate_why is None
    unnamed = parse("# T\n\n**Effort gate:** to be decided at the comp\n\n## Intent\n\nx\n")
    assert unnamed.gate is None
    assert unnamed.gate_why == "to be decided at the comp"


def test_a_missing_title_falls_back_to_the_stem():
    document = parse(
        "**Status:** DONE\n\n## Intent\n\nx\n", path="docs/plans/2026-05-01-lp-renderer.md"
    )
    assert document.title == "Lp renderer"


def test_the_essence_skips_code_and_list_markers_and_strips_marks():
    intent = (
        "```python\ncode = 1\n```\n\n"
        "- **A client without Calendly cannot be offered a page.** HR built one.\n"
    )
    assert essence_of(intent) == "A client without Calendly cannot be offered a page."
    assert (
        essence_of("`_handle` reads [the metadata](x) as *a dict*. Then more.")
        == "_handle reads the metadata as a dict."
    )
    assert essence_of("") is None


def test_a_long_first_sentence_is_capped():
    text = "word " * 100
    essence = essence_of(text)
    assert essence is not None and len(essence) <= 280 and essence.endswith("…")


def test_status_word_is_the_first_word_without_punctuation():
    assert (
        parse("# T\n\n**Status:** Pending, comp first\n\n## Intent\n\nx\n").status_word == "PENDING"
    )
    assert (
        parse("# T\n\n**Status:** DONE — 2026-09-02, main synced\n\n## Intent\n\nx\n").status_word
        == "DONE"
    )


# ── plan 06: a suggestion's kind, and what a plan carries ──────────────


def test_a_suggestions_kind_is_its_line_else_read_from_its_text_where_it_can_tell():
    from domain.document import SuggestionKind

    kind, path = DocumentKind.SUGGESTION, "docs/slice-suggestions/2026-09-04-x.md"

    def sugg(text: str):
        return parse(text, kind, path).suggestion_kind

    assert sugg("# A thing\n\n**Kind:** defect\n\n## Observation\n\nx\n") == SuggestionKind.DEFECT
    # The line wins over a defect-shaped title.
    assert (
        sugg("# The raw-button ratchet does not see a button\n\n**Kind:** idea\n\n## O\n\nx\n")
        == SuggestionKind.IDEA
    )
    assert sugg("# A brighter pontoon\n\n**Found by:** the owner\n\n## O\n\nx\n") == (
        SuggestionKind.IDEA
    )
    # No line: a review filed it, or the title says what went wrong.
    assert (
        sugg("# A brighter pontoon\n\n**Found by:** the code review of card #222\n\n## O\n\nx\n")
        == SuggestionKind.DEFECT
    )
    assert sugg("# The gate code does not reach the skipper\n\n## O\n\nx\n") == (
        SuggestionKind.DEFECT
    )
    assert sugg("# A brighter pontoon\n\n## O\n\nx\n") == SuggestionKind.IDEA
    # A plan has no kind, whatever its head says.
    assert parse("# A plan\n\n**Kind:** defect\n\n## Intent\n\nx\n").suggestion_kind is None


def test_a_plans_head_names_the_suggestions_it_carries_and_its_body_does_not():
    document = parse(
        "# 06 — The board\n\n"
        "**Written:** 2026-09-04, folding `docs/slice-suggestions/2026-09-04-a.md` and "
        "`docs/slice-suggestions/2026-09-04-b.md`.\n"
        "**Carries:** docs/slice-suggestions/done/2026-09-04-a.md\n\n"
        "## Intent\n\nSee docs/slice-suggestions/2026-09-04-c.md for the neighbour.\n"
    )
    assert document.cites == ["2026-09-04-a", "2026-09-04-b"]
    assert parse("# A plan\n\n## Intent\n\nx\n").cites == []
