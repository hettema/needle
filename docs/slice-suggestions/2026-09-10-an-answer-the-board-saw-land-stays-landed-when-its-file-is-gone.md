# An answer the board saw land stays landed when its file is gone

**Kind:** defect
**Fix:** now — the intent it breaks is written (plan 17: `needle wait` and the loop make one reading of a call, so the two cannot drift apart; card #110, ruling 5: a landed answer the board saw arrive stands on the row), the fix stays inside the one reading `runtime/calls.py::judge` makes, and it removes the class — two readers of one row disagreeing about whether its answer landed — by having the judge read the row's own landed words before the file, as `runtime/calls.py::landed` already does
**Found by:** the lane on card #110 (docs/plans/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes-and-a-colleague-checks-both-before-it-ships.md), in the review's cold read of round twelve (call 81), beside its finding

## The intent it breaks

When a colleague's answer landed and the board wrote that down, the answer landed: a person waiting on it, or a close quoting it, gets the same word from the board however long ago the file was tidied away. Today two readers of one row disagree once the file is gone — one says the answer landed, the other says the colleague ended without it — so what the board tells him about a call depends on which verb he asked. What he loses while it does: one true state per call.

## The evidence

`runtime/calls.py::landed` (card #110) accepts a row whose stored words carry the loop's `landed at` wrapping, so the close door reads a landed call as landed after its answer file is gone. `runtime/calls.py::judge`, which `needle wait` and the loop's tending both use, reads the file first (`answer_landed`) and, when it is gone, falls through to the session's state — and for a colleague whose turn is over reports `ended … without its note`, exit 1. The cold reader of card #110's round twelve reproduced the transition: a landed answer file removed, `landed` true, `wait` ended. One reading: a row the board already ended with landed words is landed, whatever the file does afterwards.
