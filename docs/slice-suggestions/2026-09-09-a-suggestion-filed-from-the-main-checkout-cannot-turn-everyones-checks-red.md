# A suggestion filed from the main checkout cannot turn everyone's checks red

**Kind:** defect
**Fix:** now — `docs/plans/README.md`'s title rule and `tests/ratchets/test_every_title_is_in_the_owners_words.py` already state the bar; the fix is a refusal at the one door a suggestion lands through from the main checkout (the commit hook in `hooks/`, which today refuses only a doctrine edit without a card), so a title that uses a listed word never reaches the trunk, rather than a retitle of one document
**Found by:** the lane on card #87 (docs/plans/done/2026-09-07-you-name-what-matters-now-a-colleague-finds-what-holds-it-back-and-the-board-sorts-every-card-by-whether-it-moves-that.md), in the review's boundaries pass

## The intent it breaks

Every card title says what will be true in the owner's words, and the shared work is green for every session that builds on it. While a suggestion that uses a word he does not use can land on the trunk from the main checkout, where no suite runs, every session inherits red checks it did not cause and either deselects the check or retitles a document that is not its own.

## Evidence

On 2026-09-09 the trunk carried `docs/slice-suggestions/2026-09-08-a-docs-only-fold-never-carries-a-walked-framework-or-a-frozen-record.md` (66b7fca), whose title uses the listed word "fold". `tests/ratchets/test_every_title_is_in_the_owners_words.py::test_no_live_title_uses_a_word_the_board_defines` refused the tree in #87's lane from its first run; the session deselected that one check for the length of its work. The same shape as the defect #20 filed on 2026-09-07 (a suggestion quoting real card titles), which was also filed from the main checkout without a lane: the door is the commit hook, and it reads only the two doctrine files today.
