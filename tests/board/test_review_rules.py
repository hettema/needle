"""Finite close evidence plus preservation of historical review display parsing."""

from board.parse import review_of
from board.progress import progress_line
from board.review_rules import HELD_FROM, dated, held, record_faults
from domain.document import Fate

RECORD = """# Review — the meter

**Plan:** docs/plans/done/2026-09-11-the-meter.md
**Reviewer:** the build session
**Findings:** 5

## The passes

1. **The feature against the plan's "done means".** The meter billed a berth
   twice on a retry; findings 1 to 2.
   1. a nested list under the pass, which is not a pass
   2. another
Read cold by Codex (01a08a3a) on b14c0cb, call 12: broke 1.2 — the sweep's
   sibling in the nightly job reads the same table and was not named.
Read cold by Codex (01a08a3c) on ac1823d, call 14: complete

2. **The seams.** Two offices; findings 3 to 4. Nothing new.
Read cold by Codex (01a08a3b) on ac1823d, call 13: complete

3. **The boundaries.** Clean.

## Dispositions

### Pass 1's findings

1. [feature] **The berth was billed twice.** — FIXED in b14c0cb; reaches the retry path
   and the invoice mailer, which reads the same row; assumes the sweep runs after the
   bill is written.
2. [seam] **The sweep read the bill before it was written.** — FIXED in b14c0cb; reaches
   the sweep alone; assumes nobody else reads the table.
3. [seam] [repair of 1.2] **The nightly job reads the table too.** — FIXED in ac1823d;
   reaches the nightly job and the sweep; assumes the two never run at once.

### Pass 2's findings

1. [record] The earlier FIXED claim on the mailer was wrong — NO CHANGE
2. [boundary] **The mailer reaches the office directly.** NOT FIXED IN THE LANE — filed
   as docs/slice-suggestions/2026-09-11-the-mailer.md.
"""


def test_the_reader_counts_passes_at_the_margin_and_reads_verdicts_apart():
    review = review_of(RECORD, "docs/reviews/2026-09-11-the-meter.md")
    assert [p.number for p in review.passes] == [1, 2, 3], "nested findings are not passes"
    assert review.passes[1].clean and review.passes[2].clean and review.clean
    assert "Read cold" not in review.passes[0].text and "Read cold" not in review.passes[1].text
    assert [(v.pass_number, v.call, v.commit, v.complete, v.broke) for v in review.verdicts] == [
        (1, 12, "b14c0cb", False, ["1.2"]),
        (1, 14, "ac1823d", True, []),
        (2, 13, "ac1823d", True, []),
    ]
    assert review.verdicts[0].who == "Codex (01a08a3a)"
    assert review.verdicts[0].words.startswith("the sweep's sibling in the nightly job")


def test_the_reader_reads_each_dispositions_address_fate_halves_and_mark():
    review = review_of(RECORD, "docs/reviews/2026-09-11-the-meter.md")
    by_address = {d.address: d for d in review.dispositions}
    assert sorted(by_address) == ["1.1", "1.2", "1.3", "2.1", "2.2"]
    first = by_address["1.1"]
    assert first.fate is Fate.FIXED and first.line == 26
    assert first.reaches == "the retry path and the invoice mailer, which reads the same row"
    assert first.assumes == "the sweep runs after the bill is written"
    assert by_address["1.3"].repair_of == "1.2" and by_address["1.3"].name == (
        "The nightly job reads the table too"
    )
    assert by_address["2.1"].fate is Fate.NO_CHANGE, "FIXED inside prose is prose"
    assert by_address["2.2"].fate is Fate.FILED, "NOT FIXED — filed is filed"
    assert (review.fixed, review.no_change, review.filed) == (3, 1, 1)
    assert review.filed_names == ["The mailer reaches the office directly"]


def test_a_flat_list_has_no_pass_and_a_bare_fix_has_no_halves():
    text = RECORD.replace("### Pass 1's findings\n", "").replace("### Pass 2's findings\n", "")
    text = text.replace(
        "— FIXED in b14c0cb; reaches\n   the sweep alone; assumes nobody else reads the table.",
        "— FIXED in b14c0cb.",
    )
    review = review_of(text, "r.md")
    assert [d.address for d in review.dispositions] == ["1", "2", "3", "1", "2"]
    assert all(d.pass_number is None for d in review.dispositions)
    bare = review.dispositions[1]
    assert bare.fate is Fate.FIXED and bare.reaches is None and bare.assumes is None


def test_a_verdict_never_makes_a_pass_clean_and_a_clean_pass_stays_clean_with_one():
    text = RECORD.replace(
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: complete",
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: complete — nothing new",
    ).replace("findings 3 to 4. Nothing new.", "findings 3 to 4.")
    review = review_of(text, "r.md")
    assert not review.passes[1].clean, "the verdict's 'nothing new' is the reader's, not the pass's"
    assert review.passes[2].clean


def test_caught_and_escaped_are_counted_by_the_address_of_the_repair_that_caused_them():
    review = review_of(RECORD, "r.md")
    assert (review.caught, review.escaped) == (1, 0), "the verdict broke 1.2 and pass 1 answered it"
    escaped = RECORD.replace("[repair of 1.2]", "[repair of 1.1]")
    review = review_of(escaped, "r.md")
    assert (review.caught, review.escaped) == (1, 1), (
        "1.1 was marked by a pass and no reader broke it"
    )
    none = RECORD.replace("[repair of 1.2] ", "").replace(
        "broke 1.2 — the sweep's", "complete — the sweep's"
    )
    review = review_of(none, "r.md")
    assert (review.caught, review.escaped) == (0, 0)


def test_the_progress_line_shows_both_counts():
    review = review_of(RECORD, "r.md")
    assert progress_line(3, 0, 3, None, review) == (
        "review clean · 3 passes · 5 found, 3 fixed, 1 no change, 1 filed · 1 caught, 0 escaped"
    )


FINITE = """# Review

**Reviewer:** Claude, independent review of abc123..def456
**Verification:** Retry regression and invoice suite passed after repairs.

## Dispositions

1. [feature] Duplicate billing — FIXED in def456.
2. [seam] Claimed race cannot occur: transaction serializes writes — NO CHANGE.
3. [boundary] Unrelated export issue — filed as docs/slice-suggestions/export.md.
"""


def test_the_date_preserves_the_historical_plan_head_boundary():
    assert dated("2026-09-11-the-meter.md") == HELD_FROM
    assert dated("the-meter.md") is None and dated("2026-13-40-x.md") is None
    assert held("2026-09-11-the-meter.md") and not held("2026-09-10-the-meter.md")


def test_finite_review_needs_no_pass_count_cold_verdict_or_call_row():
    assert record_faults(FINITE, "r.md") == []


def test_legacy_checks_and_disputed_verdicts_can_close_without_another_reader():
    legacy = RECORD + "\n## What was checked\nRetry and sweep regression tests passed.\n"
    legacy = legacy.replace("Read cold by Codex (01a08a3c) on ac1823d, call 14: complete", "")
    assert record_faults(legacy, "r.md") == []


def test_missing_or_blank_reader_and_checks_are_not_evidence():
    assert len(record_faults("# Review\n", "r.md")) == 2
    assert len(record_faults("**Reviewer:** \n**Verification:** \n", "r.md")) == 2
    assert (
        len(record_faults("**Reviewer:** Claude\n## Verification\n## Dispositions\n", "r.md")) == 1
    )
    assert len(record_faults("```markdown\n" + FINITE + "\n```", "r.md")) == 2


def test_legacy_evidence_sections_are_supported():
    for heading in (
        "What was checked",
        "Tests",
        "Evidence",
        "Verification",
        "Verification evidence",
    ):
        assert (
            record_faults(f"**Reviewer:** Codex\n\n## {heading}\nRetry test passed.", "r.md") == []
        )


def test_fenced_command_output_in_real_evidence_sections_is_accepted():
    for heading in ("Verification evidence", "What was checked", "Tests"):
        for marker in ("```", "~~~"):
            text = (
                f"**Reviewer:** Codex\n## {heading}\n{marker}text\n"
                f"$ pytest -q\n42 passed\n{marker}\n"
            )
            assert record_faults(text, "r.md") == []


def test_fences_cannot_supply_metadata_or_move_evidence_into_another_section():
    examples = (
        "**Reviewer:** Codex\n## Example\n```markdown\n"
        "## Verification evidence\n42 passed\n```\n"
    )
    assert len(record_faults(examples, "r.md")) == 1
    outside = (
        "**Reviewer:** Codex\n## Verification evidence\n```text\n\n```\n"
        "## Notes\n```text\n42 passed\n```\n"
    )
    assert len(record_faults(outside, "r.md")) == 1
    no_reader = "```markdown\n**Reviewer:** Codex\n```\n## Tests\n42 passed\n"
    assert len(record_faults(no_reader, "r.md")) == 1


def test_legacy_dispositions_can_carry_verification_without_reformatting():
    text = (
        "**Reviewer:** Independent Codex reader\n\n## Dispositions\n"
        "1. [feature] Missing setting report — FIXED in 734e71e.\n"
        "tests/test_machine.py: 48 checks passing on 734e71e.\n"
    )
    assert record_faults(text, "2026-09-10-legacy.md") == []
    assert len(record_faults("**Reviewer:** Codex\n## Dispositions\n", "r.md")) == 1
