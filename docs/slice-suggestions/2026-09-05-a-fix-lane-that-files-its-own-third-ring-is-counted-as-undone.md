# A fix lane that files its own third ring is counted as undone

**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation a2d30083), watching the dial's first night on Hello Revenue: the first fix lane to fold, #377, was reported by `needle fixes all` as *undone* ten minutes after a clean fold.
**Kind:** defect
**Fix:** now — plan 11's item 6 is the written intent (*undone* means "a defect filed against it or its fold reverted since"), and its own cycle says a lane's third-ring findings go to the board by design; the fix is inside `api/dial.py::fixes` and the report it fills; it removes the class — every fix lane that files what it found — not the one card.

## Observation

`api/dial.py::fixes` decides `defect_filed_against` by searching every live suggestion's `Found by:` line for the card's number or its lane name. Hello Revenue's #377 folded green at 02:22 with a review record and a class-closer, then its own review filed two defects it found outside its rings, each headed *Found by: the lane on card #377*. The counter read both as defects filed **against** the lane and reported the lane as undone: `1 closed … 1 undone (a defect filed against it, or the fold reverted)`. The fold stands; nothing was reverted; nobody found anything wrong with its work.

## Evidence

- `needle fixes all` at 02:34 on 2026-09-05: `hellorevenue #377 … folded; review record; did not ask; defect filed against it; fold stands`, and the totals line above.
- The two suggestions: `docs/slice-suggestions/2026-09-05-a-page-section-whose-list-came-back-as-the-wrong-shape-…md` and `…-checking-an-answer-against-its-schema-is-its-own-piece-of-code.md` in Hello Revenue's corpus, both *Found by: the lane on card #377 … in the review's … pass* — the lane as finder, not as cause.
- `board/dial.py::filer_of` already reads the same `Found by:` grammar and classifies "the lane on card #N" as a lane filing, for the rail's split by filer.

## Why it matters

Plan 11's own loop reads this counter at ten lanes: *at most one undone, fewer than half stopped to ask, most carried a class-closer*. A lane that does exactly what the cycle asks — fix its two rings, send the third to the board — is the lane most likely to be marked undone, so the reading fails on the lanes that behaved best, and the finding carried forward ("fix lanes get undone") would be false. The volume of third-ring filings is a signal plan 11 wants (the rail fed by the path that drains it), but it is a different signal from a fold that was wrong, and the counter folds the two into one word.

## What would fix it

A suggestion found *by* the fix lane (the `Found by:` reads as a lane filing under `filer_of`, and the card it names is this one) is the lane's third ring: counted and shown on the lane's line as *filed N*, never as undone. *Against* is a suggestion whose finder is someone else and whose head names the card, or a fold the trunk reverted, as today. The totals line carries both counts, so the ten-lane reading sees how much each lane sent to the board beside whether any fold was wrong. The fixture gains the case: a fix lane that files one suggestion from its review reads *folded, filed 1, fold stands*, not undone.
