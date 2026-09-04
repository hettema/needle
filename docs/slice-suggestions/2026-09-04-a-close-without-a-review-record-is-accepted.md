# A close without a review record is accepted

**Kind:** defect
**Found by:** the lane on card #23 (plan 09), translating Hello Revenue's #178 signal — "the next lane close refuses until a review record exists" — and finding the refusal was the first board's, not Needle's (2026-09-04).

## Observation

`needle close SLUG N --delivered … --watch …` moves a card into Executed with
`--review` optional (`api/board_cli.py`, the `close` parser). `CLAUDE.md` says
nothing is done without a review record and that a code-shipping slice closes
with one under `docs/reviews/`; `docs/HOW-WE-WORK.md` carries the same rule for
every project on the board. The first board refused the close without one
(Hello Revenue card #178), and that refusal did not carry over: on Needle the
rule is a convention again, held by the session remembering it.

## What would hold it

The close refuses a card whose lane folded code — a lane whose edits touch
anything outside `docs/` — without a `--review` path that exists in the
project's tree, and says so in one sentence with the path it expected. A
docs-only close (a plan archived with its rulings, a suggestion filed) passes
without one. The board's attention line counts shipped cards with no REVIEW
row, as the first board's red row did, so a close that slipped through by
another door is still visible.
