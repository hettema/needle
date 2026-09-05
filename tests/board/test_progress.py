"""A running card says how far its plan has come (plan 13): the item reader in
both corpus shapes, the record reader, and the count from the lane's copy."""

from datetime import UTC, datetime

from board.parse import items_of, parse_document, review_of
from board.progress import progress_of
from domain.document import DocumentKind, Stance

NOW = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)

HEADINGS = """# A storm warning reaches every skipper

**Status:** PENDING
**Effort gate:** high — one message to a list the office holds.

## 1. Intent

Every boat hears the gale warning the moment the office does.

### 1. Tonight's boats are one list
The bookings for tonight, read into one list. Done means: the list at
`office/tonight.py` names every boat with a booking tonight. Hands out:
execution — the read; verifies the count.
**Met:** the list at office/tonight.py; eleven boats on the fixture, each
with its skipper's phone.

### 2. One click sends the warning
Done means: `office/messages.py` sends to every boat from one click.

**Deviated:** sent from the tide clock instead; see the review's pass 1.

### 3. The log says who was reached
Done means: a line per skipper, reached or not, in the office log.

```
### 9. An example in a fence is not an item
**Met:** never read
```

## Acceptance criteria
1. Every boat is reached.
2. The log says so.
"""

LIST = """# Bid competitively

**Status:** SHIPPED

## Slices

1. **Serving coverage** — will the auction admit these keywords? SHIPPED.
2. **Seasonality** — when does demand exist? ✅ deliberately scoped to timing.
3. **[DONE 2026-06-20] Pricing.** The bid level itself.
   Done means: a bid per keyword.
4. **Pacing.** Spend per day.
   **Met:** the pacer at `engine/pacing.py`, judged against June.
5. **Reporting.** Done means: one table per campaign.

## Acceptance criteria

1. Every keyword has a bid.
"""


def test_heading_items_read_with_their_done_means_and_stance():
    items = items_of(HEADINGS)
    assert [(i.number, i.title) for i in items] == [
        (1, "Tonight's boats are one list"),
        (2, "One click sends the warning"),
        (3, "The log says who was reached"),
    ]
    first, second, third = items
    assert first.stance == Stance.MET
    assert first.text == (
        "the list at office/tonight.py; eleven boats on the fixture, each with its skipper's phone."
    )
    assert (
        first.done_means == "the list at office/tonight.py names every boat with a booking tonight."
    )
    assert second.stance == Stance.DEVIATED
    assert second.text == "sent from the tide clock instead; see the review's pass 1."
    assert third.stance is None and third.text is None
    assert third.done_means == "a line per skipper, reached or not, in the office log."


def test_a_list_plan_reads_the_bold_run_and_the_inline_habit_as_met():
    items = items_of(LIST)
    assert [i.title for i in items] == [
        "Serving coverage",
        "Seasonality",
        "Pricing",
        "Pacing",
        "Reporting",
    ]
    assert [i.stance for i in items] == [Stance.MET, Stance.MET, Stance.MET, Stance.MET, None]
    assert items[0].text == "will the auction admit these keywords?"
    assert items[2].done_means == "a bid per keyword."
    assert items[3].text == "the pacer at engine/pacing.py, judged against June."
    assert items[4].done_means == "one table per campaign."


BOLD_NUMBER = """# The pipeline lives in the client's CRM

## Acceptance criteria — behaviors

1. A client pastes URL, login and key and sees the company name.
2. A bad key reads a sentence naming the problem.

## Tasks — by intent

**0. Ground truth on the fixture before any production code.** Stand up the image locally.
*Done means:* every verify in this plan has a recorded verdict.
**Met:** the verdicts under Task 0 verdicts, probed 2026-09-05.

**1. Odoo is a connectable provider.** The four template surfaces, the credential shape.
*Done means:* acceptance 1 and 2 hold on the fixture; the template ratchets pass.

**2. The client's stages become HR's ladder, by judgment once.** The stage-map specialist.
*Done means:* the specialist proposes a map that assigns every stage.

---

## The loop
"""


def test_a_bold_numbered_paragraph_from_zero_is_a_task_list():
    """The shape on the first live Hello Revenue card after the fold: the
    number inside the bold, a task 0 that gates the rest, and an italic
    "Done means" — read as items, while the plain acceptance list is not."""
    items = items_of(BOLD_NUMBER)
    assert [(i.number, i.title) for i in items] == [
        (0, "Ground truth on the fixture before any production code"),
        (1, "Odoo is a connectable provider"),
        (2, "The client's stages become HR's ladder, by judgment once"),
    ]
    assert [i.stance for i in items] == [Stance.MET, None, None]
    assert items[0].text == "the verdicts under Task 0 verdicts, probed 2026-09-05."
    assert items[1].done_means == (
        "acceptance 1 and 2 hold on the fixture; the template ratchets pass."
    )


def test_a_plain_numbered_list_is_not_a_task_list():
    """Acceptance criteria and a ruling's reasons are numbered too; the bold
    lead on the first entry is what says "these are the items"."""
    assert items_of("# P\n\n## Acceptance criteria\n1. Every boat.\n2. The log.\n") == []
    assert items_of("# P\n\nOne promise, no items.\n") == []


def test_a_plan_document_carries_its_items_and_a_suggestion_none():
    plan = parse_document(
        HEADINGS, kind=DocumentKind.PLAN, path="docs/plans/p.md", archived=False, read_at=NOW
    )
    assert [i.number for i in plan.items] == [1, 2, 3]
    suggestion = parse_document(
        HEADINGS,
        kind=DocumentKind.SUGGESTION,
        path="docs/slice-suggestions/s.md",
        archived=False,
        read_at=NOW,
    )
    assert suggestion.items == []


RECORD = """# Review — the waiting list

**Plan:** docs/plans/done/2026-09-05-the-waiting-list.md
**Reviewer:** the build session
**Diff range:** abc..def
**Findings:** 9 — 8 fixed before this record, 1 filed.

## The passes

1. **The feature against the plan's "done means".** A 9-metre boat offered a
   9-metre berth; the fit test read length only; findings 1 to 4.
2. **The seams.** Two offices matching the same vacancy at once; findings 5 to 8.
3. **The boundaries.** The matcher reaches the office's mailer directly — finding 9, open.

## Dispositions

1. **A 9-metre boat was offered a 9-metre berth.** FIXED in 1a2b3c.
2. **The fit test read length only.** FIXED in 1a2b3c.
3. **Beam was compared as text.** FIXED in 2b3c4d.
4. **Draught was ignored at low water.** FIXED in 2b3c4d.
5. **Two offices matched the same vacancy at once.** FIXED in 3c4d5e.
6. **The offer was sent twice on a retry.** FIXED in 3c4d5e.
7. **The vacancy stayed open after the offer.** FIXED in 4d5e6f.
8. **The catamaran was judged by length.** FIXED in 4d5e6f.
9. **A berth is let twice when two offices book in the same second.** Outside this
   change — filed as docs/slice-suggestions/2026-09-05-a-berth-is-let-twice.md.

## Not done, stated
"""


def test_a_record_reads_its_plan_passes_findings_and_dispositions():
    review = review_of(RECORD, "docs/reviews/2026-09-05-the-waiting-list.md")
    assert review.plan_stem == "2026-09-05-the-waiting-list"
    assert [(p.number, p.lens) for p in review.passes] == [
        (1, 'The feature against the plan\'s "done means"'),
        (2, "The seams"),
        (3, "The boundaries"),
    ]
    assert review.passes[0].text.startswith("A 9-metre boat offered a 9-metre berth;")
    assert not review.clean
    assert (review.found, review.fixed, review.no_change, review.filed) == (9, 8, 0, 1)
    assert review.filed_names == ["A berth is let twice when two offices book in the same second"]


def test_a_clean_pass_closes_the_loop_and_no_change_is_counted():
    text = RECORD.replace(
        "## Dispositions",
        "4. **The fixed work again.** Re-read the three fix commits. Nothing new. Clean.\n\n"
        "## Dispositions",
    ).replace("FIXED in 4d5e6f.\n8.", "NO CHANGE: the beam rule is the harbour's, verified.\n8.")
    review = review_of(text, "docs/reviews/r.md")
    assert len(review.passes) == 4 and review.clean and review.passes[-1].clean
    assert (review.fixed, review.no_change, review.filed) == (7, 1, 1)


def test_a_record_without_the_sections_has_none_of_their_counts():
    review = review_of(
        "# Review\n\n**Findings:** 6\n\n## What was checked\n- x\n", "docs/reviews/old.md"
    )
    assert review.plan_stem is None and review.passes == [] and not review.clean
    assert (review.found, review.fixed, review.no_change, review.filed) == (6, 0, 0, 0)


def test_progress_counts_the_lanes_copy_and_reads_the_record_only_once_every_item_is_met():
    reads: list[int] = []

    def reviews() -> list[tuple[str, str]]:
        reads.append(1)
        return [
            (
                "docs/reviews/other.md",
                RECORD.replace("2026-09-05-the-waiting-list", "another-plan"),
            ),
            ("docs/reviews/2026-09-05-the-waiting-list.md", RECORD),
        ]

    partial = progress_of(
        HEADINGS, plan_stem="2026-09-05-the-waiting-list", read_reviews=reviews, now=NOW
    )
    assert partial is not None
    assert (partial.met, partial.deviated, partial.total) == (1, 1, 3)
    assert partial.last == "One click sends the warning"
    assert partial.line == "1 of 3 met, 1 deviated · last: One click sends the warning"
    assert partial.review is None and reads == []

    done = HEADINGS.replace(
        "Done means: a line per skipper, reached or not, in the office log.",
        "Done means: a line per skipper.\n**Met:** the log line, in the office log.",
    )
    whole = progress_of(
        done, plan_stem="2026-09-05-the-waiting-list", read_reviews=reviews, now=NOW
    )
    assert whole is not None and whole.review is not None and reads == [1]
    assert whole.review.path == "docs/reviews/2026-09-05-the-waiting-list.md"
    assert whole.line == "review · pass 3 · 9 found, 8 fixed, 1 filed"

    clean = RECORD.replace(
        "## Dispositions", "4. **The fixed work again.** Nothing new.\n\n## Dispositions"
    )
    after = progress_of(
        done,
        plan_stem="2026-09-05-the-waiting-list",
        read_reviews=lambda: [("docs/reviews/2026-09-05-the-waiting-list.md", clean)],
        now=NOW,
    )
    assert after is not None and after.line == "review clean · 4 passes · 9 found, 8 fixed, 1 filed"


def test_a_plan_with_no_items_has_no_progress_and_nothing_marked_shows_zero():
    assert progress_of("# P\n\nOne promise.\n", plan_stem="p", read_reviews=list, now=NOW) is None
    bare = progress_of(
        HEADINGS.replace("**Met:**", "Note:").replace("**Deviated:**", "Note:"),
        plan_stem="p",
        read_reviews=list,
        now=NOW,
    )
    assert bare is not None and bare.line == "0 of 3 met" and bare.last is None
