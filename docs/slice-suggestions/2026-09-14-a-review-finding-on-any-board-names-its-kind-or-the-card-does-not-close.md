# A review finding on any board names its kind, or the card does not close

**Kind:** defect
**Fix:** now — the intent is written twice: #60's shipped plan (`docs/plans/done/2026-09-05-every-session-of-any-make-follows-the-doctrine-at-least-as-well-as-hello-revenues-did.md`, the Loop) says every finding line in a review record, in both repositories, begins with one of five classes from 2026-09-06, and `docs/reviews/README.md` names the five; the fix is one more presence check at the close door in `board/review_rules.py::record_faults`, which already refuses a record with no reader, so it removes the class of unreadable records instead of the six instances.
**Found by:** #60's reading, 2026-09-14

## The intent it breaks

Every finding a reviewer writes, on every board, says what kind of finding it is, so the count that judges whether the doctrine's rewrite worked reads every finished card and is never silently short. While it is not held, the count is wrong without anyone seeing it: on Hello Revenue six of the twenty-two cards finished since 2026-09-07 carry findings the count cannot read, and the reading that judges #60 had to set them aside by hand. The rule was written to hold by convention there, and it eroded within a week, which is the signal that it needs a check rather than a reminder.

## Evidence

Counted 2026-09-14 by #60's reading with `board.parse.review_of` over every record a REVIEW row names, both projects, closes after 2026-09-07.

Needle: twenty closes, 315 findings, every line opens with one of the five classes. The ratchet `tests/ratchets/test_every_finding_says_its_class.py` holds Needle's own records and nothing else.

Hello Revenue: twenty-six closes. Sixteen are readable. Five point at records dated 2026-09-05, before the rule, and are history. Six are off the lens after the rule:

- #452, `docs/reviews/2026-09-07-gpt-6-astra-has-sat-our-hardest-exams.md`: 19 findings, none classed.
- #456, `docs/reviews/2026-09-08-landing-pages-look-like-the-client-and-improve-with-every-test.md`: 259 findings, 63 in the five classes, 195 in classes the loop does not read (`[correctness]` 105, `[test-coverage]` 57, `[claim]`, `[regression]` and seven more), one unclassed.
- #503, `docs/reviews/2026-09-10-a-website-heavy-with-video-still-gets-its-analysis.md`: 160 findings, 7 in `[cosmetic]` and `[coverage]`.
- #514, `docs/reviews/2026-09-12-card-514-the-pictures-on-a-clients-site.md`: 8 findings, 4 in `[grounding]`, `[selection]`, `[record truth]`.
- #524, `docs/reviews/2026-09-13-card-524-a-repair-fixes-what-broke.md`: 9 findings, 8 in `[correctness]`.
- #520, `docs/reviews/2026-09-13-card-520-we-never-pay-twice-for-the-same-words.md`: 7 findings, one unclassed.

A finding filed as `[correctness]` may or may not be a verification-class finding; the loop cannot tell, so those records count as zero and the rate the loop reads is low by an unknown amount.

The close door (`board/review_rules.py::record_faults`) checks that a record names a reader and holds evidence, for every project. It does not read the dispositions' classes, so a record the loop cannot count closes a card on any board. Hello Revenue's `docs/reviews/README.md` points at Needle's for the classes and holds them by convention, which #60's plan chose on 2026-09-05 before there was evidence; six misses in a week is the evidence.

## What would hold it

The close refuses a record dated on or after 2026-09-06 whose dispositions include a line that does not open with one of the five classes, on every project, with the offending lines named, the way Needle's own ratchet does today. Then the rule has one holder and Needle's ratchet becomes a rehearsal of the door rather than a second way.

Neighbours on this ground: #60 (the loop that reads the count), #131 (the record's shape at the close). No live plan or suggestion on this board names finding classes or the close's reading of a record.
