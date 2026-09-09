# A defect filed from another project lands in the owner's words or not at all

**Kind:** defect
**Fix:** now — the intent is written (`docs/plans/README.md`'s title rule and `docs/vocabulary.md`, held on Needle's own live titles by `tests/ratchets/test_every_title_is_in_the_owners_words.py`); the fix stays inside the door a suggestion enters Needle's corpus through from another project's lane or the main checkout (the ratchet's own reading, run before the file is written, or a refusal at the commit hook `hooks/commit-msg` already runs on every commit); and it removes the class — any title written from outside a Needle lane — not this one file.
**Found by:** the lane on card #68 (docs/plans/done/2026-09-05-work-the-laptop-interrupted-comes-back-by-itself-and-the-board-says-truly-how-it-ended.md), in the review's boundary pass

## The intent it breaks

A card's title says what will be true when it is done, in the owner's words, and a check refuses one on Needle's board that uses a word he does not. The check holds a lane: it runs in the lane's suite before the fold. It does not hold a document that arrives on the trunk from outside a lane — from another project's lane, or from the main checkout — because nothing runs the suite on that path. On 2026-09-08 `docs/slice-suggestions/2026-09-08-a-docs-only-fold-never-carries-a-walked-framework-or-a-frozen-record.md` reached `origin/develop` in commit 66b7fca, written by Hello Revenue's card #474, with "fold" in its title; from that commit every Needle lane's ratchet suite is red on a file none of them wrote, and the owner reads a card whose title he was promised never to see. While this holds, he loses the promise the check made, and every lane loses a green trunk to fold onto.

## Evidence

- `tests/ratchets/test_every_title_is_in_the_owners_words.py::test_no_live_title_uses_a_word_the_board_defines` fails on `origin/develop` at 72e53f0 with: `'A docs-only fold never carries a walked framework or a frozen record' uses fold`.
- `git log --oneline -1 -- docs/slice-suggestions/2026-09-08-a-docs-only-fold-never-carries-a-walked-framework-or-a-frozen-record.md` → `66b7fca docs(suggestions): …`, a commit from the main checkout with no lane and no suite run.
- Card #20 met the same shape on 2026-09-07 (379b6ce, a suggestion quoting real card titles) and filed `docs/slice-suggestions/2026-09-07-a-suggestion-that-quotes-real-card-titles-is-refused-before-it-reaches-the-public-trunk.md`; this is the second instance of one class — a document reaching the trunk by a door no ratchet stands at — and the second time is a signal about the method (HOW-WE-WORK §9).

## What would fix it

One door. Either the commit hook the machine already runs on every commit (`hooks/commit-msg`, armed by `needle hook install`) reads a suggestion added under `docs/slice-suggestions/` against `docs/vocabulary.md` and refuses the commit with the ratchet's own sentence, or `needle` gains the verb that files a suggestion from any project and runs the title reading before it writes. Whichever door, the retitle of the one file is the first step and the mechanism is the fix; the lane on #68 did not retitle it, because the file is outside its change (CLAUDE.md, the rings).
