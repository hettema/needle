# A loop cannot close itself the moment it is written

**Carried by:** docs/plans/2026-09-05-16-every-loop-a-plan-names-is-watched-until-it-closes.md — folded from the board's Idea door on 2026-09-05 (conversation 6b683c8b), which read it as plan 16's item 2 written a second time
**Kind:** defect
**Fix:** now `docs/INTENT.md` already says done is a closed loop and not a claim, and the close already refuses a row for one reason, so the refusal has somewhere to live
**Found by:** the lane on card #59 (docs/plans/done/2026-09-05-a-defects-mark-is-verified-before-it-routes.md), at its own close — this card's first WATCH row did it

## Observation

A `command` signal with no `expect` is delivered as soon as the command exits
0. `runtime/signals.py`: with `expect` absent the reader returns True on a
zero exit and nothing else is asked.

So a WATCH row of the shape *"…— command `<some command that runs>` by
<date>"* is delivered on its first read, whatever the command printed. The
card leaves Executed for Done, the loop is recorded closed, and the green
reading says only that a program ran.

It happened on card #59, at its own close, minutes after it shipped. The row
was *"the owner's decision pile drains faster than it grows … command uv
--project /home/dennis/Work/needle run needle kinds needle by 2026-10-05
every 7d"*. The signal loop read it, `needle kinds` exited 0 as it always
will, and the card moved to Done with the reading *"`uv --project … needle
kinds needle` exited"*. The pile had not moved. The row was rewritten as a
`session` signal that says what would decide it, and the card moved back.

The sibling defect — *a WATCH row the reader cannot run is accepted at the
close and fails a day later* — is the same door letting through the opposite
failure. That one is loud a day later. This one is silent for ever: a closed
loop nobody will look at again.

## What would hold it

The close refuses a `command` or `url` signal with no `expect`, by name, the
way it already refuses a code lane with no review record — because without
one the row states no observation, only that something ran. A `file` signal
needs none: the file existing *is* the observation.

The refusal names the row and says what to add, so a session meets it at the
moment it is writing the row rather than a month later when the loop it
thought it wrote has been green since the day it shipped.

## Rejected

Reading every closed loop again to find the ones that self-closed: worth
doing once as evidence, but it is a sweep and not a mechanism, and the next
row written the same way would pass the same way.
