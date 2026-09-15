# The board's eyes do not close while its hands are full

**Carried by:** docs/plans/done/2026-09-15-the-boards-eyes-do-not-close-while-its-hands-are-full.md

**Kind:** defect
**Fix:** now — the intent is written in three places (plan 59: a defect's
mark is verified before it routes; card #74 item 3: every plan and idea has
its title read cold; card #82 item 1: every card parked on the owner is read
once per park), and all three stop happening whenever auto-fix is busy; the
fix stays inside `board/dial.py::running` and `api/dial.py::_take_next`, and
it removes the class — every reading starved by work that commits — rather
than today's one card.
**Found by:** the owner, 2026-09-15, asking why a planned card had waited six
hours to start

## The intent it breaks

A reading enters nothing. It opens no lane, writes no commit and folds
nothing; it reads one document and lands one verdict, and until it lands the
card it judges cannot move. A fix lane is the opposite: it plans, edits, runs
the project's whole suite and folds to the trunk.

The board counts them as the same thing against one number. So the moment
auto-fix fills that number with lanes, the board stops reading — no defect is
graded, no title is read cold, no card parked on the owner is looked at —
and it stops exactly when the most work is moving and the most cards are
arriving.

## The evidence

Hello Revenue's switch went on at 2026-09-15 10:05Z with the number at 4.
Readings an hour, from the board's own `title_readings` and `triages`, all
times UTC:

| hour | readings | what was running |
|---|---|---|
| 00–02 | 111 (≈37/h) | no fix lane; the machine quiet |
| 09 | 6 | the switch still off |
| 10 | 1 | the switch on at 10:05 |
| 11 | 0 | four fix lanes |
| 12 | 0 | four fix lanes |
| 13 | 2 | four fix lanes |
| 14 | 13 | three lanes, three more held below the line |

Two full hours with the board's eyes shut, and the recovery in hour 14 comes
from the line holding lanes back, not from anything that protects reading.

What it cost, concretely. Hello Revenue #500 is a planned card at the high
gate whose plan was written this morning. Its title was read on 2026-09-14
23:35Z and could not be placed; the owner retitled the document the same day
("yes pls retitle") and the new title answers the reading's objection in its
own words. Six hours later no reading has opened on it, so Start stays shut
and a fully planned card sits still. One session would clear it.

Why they share a number at all, in `board/dial.py::running`'s own words:

> a triage counts for the same reason — it is a live session on a machine
> whose ceiling is memory, and a rail of forty untriaged defects would
> otherwise open forty of them under a dial set to one (plan 59, item 3)

Memory is the reason, and memory already has its own guard: `_full()` stops
the beat opening anything while no machine holds the floor, read in GB per
machine — "the number is a ceiling the machine lowers, ruling 4". The number
is doing a second, cruder job in a currency that does not fit, and the two
kinds of session are nowhere near the same size. Measured on the rented
machine today at 14:47 CEST, while it sat at 0 GB available:

- card #129's fix lane: ~6.3 GB across four processes (its suite)
- card #197's: ~4.1 GB across four
- card #484's: ~1.4 GB
- a reading: one session, no suite

So four readings and four fix lanes are treated alike by a ceiling that
exists because of memory, while costing an order of magnitude apart.

## What would hold it

The forty-readings problem is real and must not come back: the fix is not to
stop counting readings, it is to stop counting them *against the lanes*.

1. **Readings get their own allowance.** The number caps what commits; a
   second, smaller bound caps readings in flight. `running()` splits, and
   `_take_next` checks each against its own. The floor still governs both,
   so memory is held where memory is measured.
2. **Or the beat spends its last slot on a reading before a lane.** Cheaper
   to write, and it guarantees the eyes never close entirely — but it only
   narrows the window rather than closing the class, and it makes the
   ordering rule harder to state.

Recommended: (1). It says the true thing — two kinds of work, two bounds,
one floor over both — and (2) leaves a board with a big enough rail still
reading at a trickle.

Whatever the shape, the measure is the table above: readings an hour must not
fall to zero because lanes are running.

## Live neighbours on this ground

Searched `docs/slice-suggestions/` (live and `done/`) and `docs/plans/` for
the number, the seat, the floor and the beat.
`2026-09-05-needles-own-defects-get-fixed-without-waiting-for-a-quiet-machine.md`
(card #34, `**Fix:** his`) is about *when* the beat may take a fix on
Needle's own board — the quiet rule, not the number. Card #109
(`done/…a-test-run-never-takes-the-memory-the-work-needs.md`) caps what one
test run may take from the machine; it is the reason a lane's suite is
survivable at all, and it does not bear on which work the number admits.
Card #149's live plan draws a line through *which defects* auto-fix takes;
it does not change how many, nor what else the number holds back — with its
line in place the board still shuts its eyes whenever four lanes are above
the line.
