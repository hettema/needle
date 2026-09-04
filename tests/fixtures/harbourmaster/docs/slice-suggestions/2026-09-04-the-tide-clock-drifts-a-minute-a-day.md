# The tide clock drifts a minute a day

**Kind:** defect
**Fix:** now — the tide table plan says the harbour's own clock is the reference, and the quay display keeps its own
**Found by:** the review of card #241 (`docs/reviews/2026-09-03-the-deploy.md`, finding 2), carried out.

## Observation

The quay display shows high water from a clock it winds itself at boot. It gains about a minute a day, and after a fortnight the board on the pontoon disagrees with the office by a quarter of an hour.

## What would hold it

The quay display reads the time from the office on every refresh, never from its own clock, and a check at boot refuses to start when the two disagree by more than a minute.
