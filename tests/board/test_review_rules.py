"""A fix says who else it reaches and what it assumes, a cold reader's verdict
sits on the record with its call, and a finding an earlier repair caused says
so (card #110): the reader reads the three forms `docs/reviews/README.md`
sets, and the rules say what a dated record owes before its card can close.
"""

from datetime import UTC, datetime

from board.parse import review_of
from board.progress import progress_line
from board.review_rules import HELD_FROM, dated, held, record_faults, verdict_faults
from domain.call import Call
from domain.document import Fate

NOW = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)

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


# ── the rules ──────────────────────────────────────────────────────────


def test_the_date_decides_and_a_name_without_one_is_not_the_shape():
    assert dated("2026-09-11-the-meter.md") == HELD_FROM
    assert dated("the-meter.md") is None and dated("2026-13-40-x.md") is None
    assert held("2026-09-11-the-meter.md") and not held("2026-09-10-the-meter.md")
    assert not held("the-meter.md")


def test_a_record_in_the_form_has_no_fault():
    assert record_faults(review_of(RECORD, "r.md"), "r.md") == []


def test_a_fix_line_without_a_half_is_named_by_its_line():
    text = RECORD.replace(
        "— FIXED in b14c0cb; reaches\n   the sweep alone; assumes nobody else reads the table.",
        "— FIXED in b14c0cb; reaches the sweep alone.",
    )
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert len(faults) == 1 and faults[0].startswith("r.md:29 FIXED says no assumes")
    text = text.replace("— FIXED in b14c0cb; reaches the sweep alone.", "— FIXED in b14c0cb.")
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert faults[0].startswith("r.md:29 FIXED says no reaches or assumes")


def test_a_round_of_repairs_without_a_verdict_is_a_fault_and_a_zero_finding_record_is_not():
    text = RECORD.replace("Read cold by Codex (01a08a3b) on ac1823d, call 13: complete\n", "")
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert faults == [], "pass 2's round holds no FIXED line, so it owes no verdict"
    text = RECORD.replace(
        "Read cold by Codex (01a08a3a) on b14c0cb, call 12: broke 1.2 — the sweep's\n"
        "   sibling in the nightly job reads the same table and was not named.\n"
        "Read cold by Codex (01a08a3c) on ac1823d, call 14: complete\n",
        "",
    )
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert len(faults) == 1 and "pass 1's round has FIXED lines and no verdict" in faults[0]
    empty = (
        "# Review\n\n**Plan:** docs/plans/done/p.md\n**Findings:** 0\n\n## The passes\n\n"
        "1. **All three lenses.** Nothing new.\n\n## Dispositions\n"
    )
    assert record_faults(review_of(empty, "r.md"), "r.md") == []


def test_a_broken_address_nobody_answered_is_a_fault():
    text = RECORD.replace("[repair of 1.2] ", "")
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert (
        len(faults) == 1
        and "broke 1.2 and no disposition marked `[repair of 1.2]` says what became of it"
        in faults[0]
        and "broke 1.2 and no disposition marked `[repair of 1.2]` says what became of it"
        in faults[0]
    )
    corrected = text.replace(
        "1. [record] The earlier FIXED claim on the mailer was wrong — NO CHANGE",
        "1. [record] [repair of 1.2] The reach line on 1.2 named the sweep alone; the nightly "
        "job is now on it — CORRECTED in the record",
    )
    assert record_faults(review_of(corrected, "r.md"), "r.md") == [], (
        "a record-only correction answers it"
    )


def test_a_fix_under_no_pass_heading_and_a_record_without_passes_are_structure_faults():
    flat = RECORD.replace("### Pass 1's findings\n", "")
    faults = record_faults(review_of(flat, "r.md"), "r.md")
    assert any("FIXED under no `### Pass N` heading" in f for f in faults)
    no_passes = (
        RECORD.split("## The passes")[0] + "## Dispositions" + RECORD.split("## Dispositions")[1]
    )
    faults = record_faults(review_of(no_passes, "r.md"), "r.md")
    assert len(faults) == 1 and "no `## The passes` section" in faults[0]


def test_a_verdict_off_the_form_is_a_fault():
    text = RECORD.replace(
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: complete",
        "Read cold by Codex: complete",
    )
    faults = record_faults(review_of(text, "r.md"), "r.md")
    assert len(faults) == 1 and faults[0].startswith("r.md:18 a verdict not in the form")


def test_a_fix_that_answers_the_last_break_is_read_and_a_correction_closes_the_round():
    """Pass two's reader: an earlier verdict was satisfying later, unread
    repairs. A round ends on a verdict that says complete, or on breaks
    answered by a record-only correction."""
    unread = RECORD.replace("Read cold by Codex (01a08a3c) on ac1823d, call 14: complete\n", "")
    review = review_of(unread, "r.md")
    faults = record_faults(review, "r.md")
    assert len(faults) == 1 and "the fix that answers it was never read cold" in faults[0]
    assert "broke 1.2" in faults[0]
    assert record_faults(review_of(RECORD, "r.md"), "r.md") == [], "read again, complete"
    corrected = unread.replace(
        "3. [seam] [repair of 1.2] **The nightly job reads the table too.** — FIXED in ac1823d;\n"
        "   reaches the nightly job and the sweep; assumes the two never run at once.",
        "3. [record] [repair of 1.2] The reach line named the sweep alone where the nightly job "
        "reads the table too — CORRECTED in the record.",
    )
    review = review_of(corrected, "r.md")
    assert review.dispositions[2].fate is Fate.CORRECTED
    assert record_faults(review, "r.md") == [], "a correction is the writer's own re-read"


def test_a_bare_mark_a_verdict_that_says_neither_and_findings_without_the_section_are_faults():
    bare = RECORD.replace(
        "3. [seam] [repair of 1.2] **The nightly job reads the table too.** — FIXED in ac1823d;\n"
        "   reaches the nightly job and the sweep; assumes the two never run at once.",
        "3. [seam] [repair of 1.2] Still broken; no repair has been made.",
    )
    faults = record_faults(review_of(bare, "r.md"), "r.md")
    assert any(
        "no disposition marked `[repair of 1.2]` says what became of it" in f for f in faults
    )
    neither = RECORD.replace(
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: complete",
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: unable to read the files",
    )
    faults = record_faults(review_of(neither, "r.md"), "r.md")
    assert any("has not read the round" in f for f in faults)
    renamed = RECORD.replace("## Dispositions", "## Findings")
    review = review_of(renamed, "r.md")
    assert review.dispositions == [] and review.found == 5
    faults = record_faults(review, "r.md")
    assert any("counts 5 finding(s) and no `## Dispositions`" in f for f in faults)


def test_the_counts_are_findings_in_pass_order():
    """Two full-pass findings on one repair are two escapes; a break a
    reader named before the pass makes the later finding one caught
    event; a break named only after the pass leaves the finding escaped."""
    two = RECORD.replace(
        "1. [record] The earlier FIXED claim on the mailer was wrong — NO CHANGE",
        "1. [record] [repair of 1.1] The mailer's fix missed its twin — FIXED in bcd; reaches "
        "the twin; assumes nothing.\n3. [seam] [repair of 1.1] And its other twin — FIXED in "
        "bcd; reaches it; assumes nothing.",
    )
    review = review_of(two, "r.md")
    assert (review.caught, review.escaped) == (1, 2)
    later = two.replace(
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: complete",
        "Read cold by Codex (01a08a3b) on ac1823d, call 13: broke 1.1 — the twins",
    )
    review = review_of(later, "r.md")
    assert (review.caught, review.escaped) == (2, 0), (
        "a break named under the pass makes its findings caught"
    )


def _call(number: int, slot: str, *, landed: bool) -> Call:
    return Call(
        id=number,
        session_id="01a08a3a-0000-7000-8000-000000000000",
        slot=slot,
        name=f"{slot}-01a08a3a",
        note="/tmp/note.md",
        answer="/tmp/none/answer.md",
        brief="read",
        caller="/tmp/lane",
        called_at=NOW,
        moved=None,
        ended_at=NOW if landed else None,
        words="/tmp/none/answer.md landed at 2026-09-11T09:01:00+00:00: complete"
        if landed
        else None,
    )


def test_the_call_table_faults_a_missing_row_the_own_kind_and_an_answer_that_never_landed():
    review = review_of(RECORD, "r.md")
    rows = {
        12: _call(12, "codex", landed=True),
        13: _call(13, "codex", landed=True),
        14: _call(14, "codex", landed=True),
    }
    ok = verdict_faults(
        review,
        "r.md",
        call_of=rows.get,
        lane_slot="hrclaude",
        landed=lambda c: c.ended_at is not None,
    )
    assert ok == []
    missing = verdict_faults(
        review,
        "r.md",
        call_of={12: rows[12], 14: rows[14]}.get,
        lane_slot="hrclaude",
        landed=lambda c: True,
    )
    assert len(missing) == 1 and "names call 13, which the board has no row for" in missing[0]
    own = verdict_faults(review, "r.md", call_of=rows.get, lane_slot="codex", landed=lambda c: True)
    assert len(own) == 3 and all("of the lane's own kind" in f for f in own)
    claude_rows = {n: _call(n, "hrclaude", landed=True) for n in (12, 13, 14)}
    other = verdict_faults(
        review, "r.md", call_of=claude_rows.get, lane_slot="codex", landed=lambda c: True
    )
    assert other == [], "a Codex lane's cold reader is of Claude's make"
    never = verdict_faults(
        review, "r.md", call_of=rows.get, lane_slot="hrclaude", landed=lambda c: False
    )
    assert len(never) == 3 and all("never landed after the call" in f for f in never)
    unknown = verdict_faults(
        review, "r.md", call_of=rows.get, lane_slot=None, landed=lambda c: True
    )
    assert len(unknown) == 1 and "holds no session for this lane" in unknown[0]
