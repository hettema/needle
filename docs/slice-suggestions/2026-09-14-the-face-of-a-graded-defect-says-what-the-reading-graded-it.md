# The face of a graded defect says what the reading graded it

**Kind:** defect
**Fix:** now — both rulings are already the owner's, so which one governs a
graded `his` defect is execution, not his call; the fix is inside one branch
of `board/assemble.py::_defect_state` and its test, and it removes the class
(two cards writing the same face with no order between them), not one card.
**Found by:** the lane on card #138, 2026-09-13, running Needle's full suite
before folding

## The intent it breaks

Card #100 gave defects their own column, graded by the reading that verifies
them, gravest first, and promised the card's face carries the grade's word.
Card #82 gave a defect the reading left with the owner a face that says
`your ruling` and opens the Rule door. A defect that is both — graded, and
left with him — can only show one, and nothing says which. Today the second
silently wins, and the test the first shipped has been red on the trunk ever
since.

## The evidence

`tests/api/test_defects_column.py::test_a_defects_reading_without_a_grade_is_refused_and_a_graded_one_shows_its_word`
fails on `origin/develop` (33e3140), in isolation, every time:

    assert face["state"]["word"] == "lies"
    AssertionError: assert 'your ruling' == 'lies'

`board/assemble.py`, the branch that wins, with its own comment saying it is
deliberately ranked above what follows:

    # Yours before live, as every branch above it is …
    if routed is not None and routed.state == Routing.TRIAGED_HIS and doors.answer.offered:
        return _state("your ruling", Meaning.YOURS, …)

The grade's word is returned further down. The `your ruling` branch landed in
950d8a8 on 2026-09-05; the assertion expecting `lies` landed with card #100
in e03a46f on 2026-09-12 19:59Z — a week later, over a branch that already
outranked it. So the test appears to have been red the moment it was written,
and #100 folded on it. (If it passed at its fold, then something between
2026-09-12 19:59Z and now changed `doors.answer.offered` for that fixture,
and that is what to find instead.)

## What would hold it

Decide which face a graded, his-marked defect shows, and make the other
unreachable rather than merely lower: either the grade's word with the Rule
door still offered — the grade says how bad it is, the door says whose it is,
and they do not compete — or `your ruling` with the test rewritten to say so
and #100's promise narrowed in its own words. Whichever wins, the branch
should not be able to shadow the other silently: the two rulings meet in one
function and nothing there names the collision.

The red test itself does not belong to #138 and was left where it was found
(the review rule: outside the change, file it and leave it outside).

## Live neighbours on this ground

Searched `docs/slice-suggestions/` for the face, the grade and the word:
nothing live carries it. The nearest is card #66
(`2026-09-05-one-word-never-names-two-different-things-on-the-board.md`),
which renames "triage" across the board's words — it changes what things are
called, not which of two rulings wins on one face.
