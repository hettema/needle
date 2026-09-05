"""Every live suggestion in Needle's own corpus says its kind and who fixes
it (plan 11, item 2).

The dial reads eligibility off a suggestion's head: `Kind:` puts it on the
defects rail, `Fix:` says whether it may enter execution without the owner.
A head the board has to guess at is a head the board decides for itself,
which INTENT forbids; and an unmarked defect reads as his, so a session that
forgets the line quietly parks its own finding on him. So the line is
refused here rather than remembered: one `Kind:` in the vocabulary, one
`Fix:` in the vocabulary, a `now` or `his` whose reason a later reader can
act on (plan 59, item 2), and a `when` whose trigger the signal parser can
read. The head only, as the parser reads it — a `**Fix:**` line under a
section is prose and is not counted. Other projects' corpora are read, never
held to this: their sessions learn the line from the briefs.
"""

from datetime import UTC, date, datetime

from board.parse import parse_document
from board.signals import read_or_decline
from board.triage import resolve_source, source_ref_of, why_is_a_reason
from domain.document import DocumentKind, FixMark, SuggestionKind
from tests.ratchets.paths import REPO

LIVE = REPO / "docs" / "slice-suggestions"
KINDS = {k.value for k in SuggestionKind}
REASON_RULE_FROM = date(2026, 9, 6)
"""From the day every filing brief carries the reason bar (plan 59, item 2).
A mark written before that was written under a rule that asked for the word
and not the reason."""


def _live_suggestions():
    for path in sorted(LIVE.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        text = path.read_text(encoding="utf-8")
        yield (
            path,
            parse_document(
                text,
                kind=DocumentKind.SUGGESTION,
                path=f"docs/slice-suggestions/{path.name}",
                archived=False,
                read_at=datetime.now(UTC),
            ),
        )


def test_every_live_suggestion_says_its_kind_on_its_head():
    offenders: list[str] = []
    for path, document in _live_suggestions():
        line = next((f.value for f in document.head_fields if f.key.lower() == "kind"), None)
        if line is None:
            offenders.append(f"{path.name}: no Kind: line")
        elif line.split()[0].strip("`*").lower() not in KINDS:
            offenders.append(f"{path.name}: Kind: {line!r} is not defect or idea")
    assert not offenders, "\n".join(offenders)


def test_every_live_suggestion_says_who_fixes_it_on_its_head():
    offenders: list[str] = []
    for path, document in _live_suggestions():
        if document.fix is None:
            offenders.append(f"{path.name}: {document.fix_note}")
            continue
        if document.fix.mark == FixMark.WHEN:
            signal, why = read_or_decline(document.fix.trigger)
            if signal is None:
                offenders.append(
                    f"{path.name}: Fix: when names no signal the board can read: {why}"
                )
    assert not offenders, (
        "a live suggestion's Fix: line is missing or outside the vocabulary (now, when "
        "<signal>, his):\n" + "\n".join(offenders)
    )


def test_the_ratchet_sees_a_head_with_two_marks_and_a_line_that_is_prose():
    two = parse_document(
        "# T\n\n**Kind:** defect\n**Fix:** now\n**Fix:** his\n\n## O\n\nx\n",
        kind=DocumentKind.SUGGESTION,
        path="docs/slice-suggestions/t.md",
        archived=False,
        read_at=datetime.now(UTC),
    )
    assert two.fix is None and two.fix_note == "two Fix: lines: Fix: now / Fix: his"
    prose = parse_document(
        "# T\n\n**Kind:** defect\n**Fix:** extracted the resolver into one module\n\n## O\n\nx\n",
        kind=DocumentKind.SUGGESTION,
        path="docs/slice-suggestions/t.md",
        archived=False,
        read_at=datetime.now(UTC),
    )
    assert prose.fix is None and prose.fix_note is not None
    assert prose.fix_note.startswith("Fix: line is not a mark: Fix: extracted")


def test_every_now_or_his_mark_names_a_reason_the_ratchet_can_refuse():
    """Plan 59, item 2. A mark's `why` is the only thing a later reader has
    to work with, and the corpus had marks that said "a product call" and
    stopped. That names the shape of the decision, not the decision, and it
    told the second reader nothing it did not already know.

    Cheap on purpose, and named as cheap: this refuses an empty reason, a
    category word, and a reason too short to be one. It does not judge
    whether the reason is *true* — a backticked path and a card number are
    accepted affordances and nothing here treats either as a verified
    source. The proof is the triage reading (item 3), which resolves the
    source and reads it.

    Held from the day the briefs carry the bar and not before. Sixteen live
    marks were written under a rule that asked only for the word, and
    inventing reasons for other sessions' findings would be a worse lie than
    an absent one — the reading seat is what reads those. The doctrine hook's
    reader made the same call for the same reason: a suite that goes red on
    everything already written teaches a session to ignore it."""
    offenders: list[str] = []
    for path, document in _live_suggestions():
        if document.fix is None or document.fix.mark == FixMark.WHEN:
            continue
        if document.date is not None and document.date < REASON_RULE_FROM:
            continue
        refusal = why_is_a_reason(document.fix.why)
        if refusal is not None:
            offenders.append(f"{path.name}: Fix: {document.fix.mark.value} — {refusal}")
    assert not offenders, (
        "a live suggestion's Fix: now or Fix: his says who fixes it and not why:\n"
        + "\n".join(offenders)
    )


def test_the_bar_is_held_from_the_day_the_briefs_carry_it_and_the_older_marks_are_named():
    """The grandfathering is a fact, not a shrug: the count of live marks
    that predate the bar is printed here, so it is visible that it shrinks
    as those cards close rather than quietly becoming the resting place the
    debt line elsewhere exists to stop."""
    older = [
        path.name
        for path, document in _live_suggestions()
        if document.fix is not None
        and document.fix.mark != FixMark.WHEN
        and document.date is not None
        and document.date < REASON_RULE_FROM
        and why_is_a_reason(document.fix.why) is not None
    ]
    assert all(name.startswith("2026-09-0") for name in older), older


def test_the_bar_refuses_an_empty_reason_and_a_category_word_and_takes_the_valid_forms():
    """The four fixtures the plan names, read through the parser so the
    ratchet and the board agree on what a mark's reason even is."""

    def why_of(line: str) -> str | None:
        document = parse_document(
            f"# T\n\n**Kind:** defect\n**Fix:** {line}\n\n## O\n\nx\n",
            kind=DocumentKind.SUGGESTION,
            path="docs/slice-suggestions/t.md",
            archived=False,
            read_at=datetime.now(UTC),
        )
        assert document.fix is not None, document.fix_note
        return why_is_a_reason(document.fix.why)

    empty = why_of("now")
    assert empty is not None and "names no reason" in empty
    category = why_of("his — a product call")
    assert category is not None and "shape of the decision" in category
    bare_source = why_of("now `docs/HOW-WE-WORK.md`")
    assert bare_source is not None and "a source on its own is not one" in bare_source

    # Both valid forms: a backticked path, and a card number, each saying
    # what in it selects the outcome.
    assert why_of("now `docs/HOW-WE-WORK.md` §10 already writes this rule") is None
    assert why_of("his the two shapes #435 chose between are still both open") is None


def test_nothing_reads_a_source_shaped_reason_as_a_verified_source():
    """The affordance reader finds a path in a reason; it never claims the
    path exists. `docs/no-such-plan.md` reads exactly like a real path, and
    the whole point of the reading seat is that something opens the file."""
    assert source_ref_of("the rule in `docs/no-such-plan.md` settles it") == "docs/no-such-plan.md"
    assert why_is_a_reason("the rule in `docs/no-such-plan.md` settles it") is None
    nowhere = resolve_source("docs/no-such-plan.md", REPO, lambda number: None)
    assert nowhere is not None and nowhere.fingerprint is None
    assert "resolved nowhere" in nowhere.note
    real = resolve_source("docs/HOW-WE-WORK.md", REPO, lambda number: None)
    assert real is not None and real.fingerprint is not None
