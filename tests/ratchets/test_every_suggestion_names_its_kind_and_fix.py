"""Every live suggestion in Needle's own corpus says its kind and who fixes
it (plan 11, item 2).

The dial reads eligibility off a suggestion's head: `Kind:` puts it on the
defects rail, `Fix:` says whether it may enter execution without the owner.
A head the board has to guess at is a head the board decides for itself,
which INTENT forbids; and an unmarked defect reads as his, so a session that
forgets the line quietly parks its own finding on him. So the line is
refused here rather than remembered: one `Kind:` in the vocabulary, one
`Fix:` in the vocabulary, and a `when` whose trigger the signal parser can
read. The head only, as the parser reads it — a `**Fix:**` line under a
section is prose and is not counted. Other projects' corpora are read, never
held to this: their sessions learn the line from the briefs.
"""

from datetime import UTC, datetime

from board.parse import parse_document
from board.signals import read_or_decline
from domain.document import DocumentKind, FixMark, SuggestionKind
from tests.ratchets.paths import REPO

LIVE = REPO / "docs" / "slice-suggestions"
KINDS = {k.value for k in SuggestionKind}


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
