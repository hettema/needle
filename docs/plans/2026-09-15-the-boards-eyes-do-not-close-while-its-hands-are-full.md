# The board's eyes do not close while its hands are full

**Status:** SHIPPED
**Carries:** docs/slice-suggestions/2026-09-15-the-boards-eyes-do-not-close-while-its-hands-are-full.md
**Written:** 2026-09-15, at the owner's word after he asked why a planned card had waited six hours to start and was told the board had stopped reading while auto-fix worked.
**Effort gate:** medium — the shape is one counter split into two bounds inside two functions that already exist (`board/dial.py::running`, `api/dial.py::_take_next`), with no new owner setting and no change to the store; the risk is not the edit but the boundary it must not cross, the forty-readings-at-once the shared count was put there to prevent, and that is one test away.
**Sequencing:** none holds this. Beside #149's live plan, which draws a line through *which* defects are taken and leaves the count alone, and beside #151's, whose intent names "the readings cap" among what it does not change — this plan is that cap, and neither of the other two touches it.
**Class:** `uv --project /home/dennis/Work/needle run needle fixes all --reading-gaps --count` counts the hours in the last day in which a fix lane ran and no reading opened. Zero is the class closed.

## Intent

While auto-fix is busy, the board stops looking at anything — no defect is
graded, no new card's title is read, and no card parked on you is picked up —
so the work you can see and rank dries up exactly when the most is moving.

The two are counted as one thing against one number. A reading enters
nothing: it opens no lane, writes no commit, folds nothing; it reads one
document, lands one verdict, and until it lands, the card it judges cannot
move. Fixing a defect is the opposite — it plans, edits, runs the project's
whole suite and folds to the shared work. The moment auto-fix fills the
number with the second kind, the first kind stops.

After this plan, what commits and what only looks have a bound each, the
machine's memory still governs both, and the board can never be busy enough
to stop seeing.

What does not change: who reads, what a reading is asked, the per-card fuse
that stops a third reading of the same text (card #138), the line #149 draws
through which defects are taken, and the number you set for work that
commits — it keeps its name and its meaning, and stops holding back work
that commits nothing.

## What was searched before naming anything new

The suggestion's own search is carried. Searched again at this door, over
four concepts.

*A second bound already there:* `board/dial.py::TRIAGE_ATTEMPTS` (487) is
per card and per park — how many readings may die on one card — not how many
may be open at once; `_readings_that_died` and `_parked_unread` both read it
that way. No concurrency bound for readings exists.

*A claim that already says this:* `domain/board.py::Claim.READINGS_STOPPED`
(106) reads "the board opened its cap of readings on this card's text and
none settled it" — card #138's per-card fuse, one card's text, not the
board's eyes closing. A reader meeting both must be able to tell them apart,
which item 4 is for.

*The memory guard:* `api/dial.py::_full` already refuses to open anything
while no machine holds the floor, read in GB per machine, and its own
docstring calls the number "a ceiling the machine lowers, ruling 4". Memory
has its guard; the number is holding a second, cruder one in a currency that
does not fit.

*Somebody else's plan on this ground:* #149 (`docs/plans/2026-09-15-auto-fix-stops-at-the-line-you-drew-and-leaves-the-rest-filed.md`)
and #151 (`docs/plans/2026-09-15-a-defect-auto-fix-planned-can-start-whatever-machine-wrote-the-plan-and-whatever-the-title-read.md`)
are both live on the beat. #149 changes which defects are eligible; #151
changes what happens to a planning session that lands nothing. Neither reads
or writes `running()`, and #151's intent names the readings cap as out of
its scope.

## Terrain — where to look, not what to write

`board/dial.py::running` is the counter and the whole of the arithmetic; its
docstring carries the reason readings were folded in (plan 59, item 3) and is
the thing to correct rather than delete. `api/dial.py::_take_next` holds the
two gates in order — `_full()` first, then the number — and `_triaging()`
beside it counts what is open. `api/dial.py::_triage` opens a reading;
`_wants_a_reading`, `_wants_a_title_reading` and `_parked_unread` are the
three doors that feed it, each with its own per-card rules that do not
change. The head's sentence and `needle dial`'s last line are in
`board/assemble.py` and `api/board_cli.py`. The tests that pin the beat's
arithmetic are `tests/api/test_dial.py` (the `acts`/`last_act` helpers count
what a beat opened), with `tests/api/test_the_triage_seat.py` and
`tests/api/test_defects_column.py` reading through the same floor.

## Items

### 1. Work that only looks is no longer held back by work that commits
Readings stop counting against the number that bounds fix lanes. The number
keeps its name, its setting and its meaning for everything that commits.

Done means: with the number at 1 and one fix lane live, a beat still opens a
reading on an unread card; the same test with the reading already open shows
the lane unaffected. Both directions pinned in `tests/api/test_dial.py`.

**Met:** `board/dial.py::running` no longer takes `triaging=`, and both
directions are pinned in `tests/api/test_dial.py::test_a_full_number_no_longer_stops_the_board_looking`:
at the number with one lane live, the next beat opens a reading; with a
reading open, the next verified defect is planned into the second lane.

Hands out: search — every reader of `running`, `_triaging`, `fix_lanes_at_most` and `LIVE_STAGES` across `api/`, `board/`, `infrastructure/` and `tests/`, with path and line, so item 2 corrects all of them and none is left counting the old way; verifies opening each hit and confirming it is a read of the count rather than of the stage.

### 2. A board with forty unread cards still opens only a few readings at once
Readings get a bound of their own, a constant beside `TRIAGE_ATTEMPTS` rather
than a setting you have to manage, because the thing it protects is the
machine and the machine already has a floor you never set by hand.

Done means: with the readings bound at its constant and that many readings
open, a beat opens no further reading and says so; the forty-untriaged-rail
case from plan 59 item 3 is a test that fails on a bound removed and passes
on a bound respected.

**Met:** `board/dial.py::READINGS_AT_ONCE` is 3, beside `TRIAGE_ATTEMPTS`;
`tests/api/test_dial.py::test_the_board_opens_a_few_readings_at_once_and_never_one_per_card`
opens three on a rail of unread cards, shows three further beats opening
nothing, and shows a landed result freeing a seat at once — so it is the
bound and not an exhausted rail. It fails with the bound removed.

### 3. Memory still stops everything, and it stops it first
The floor keeps its precedence: under it, neither a lane nor a reading opens,
whatever either bound says.

Done means: the existing floor tests still pass unchanged, plus one that puts
the machine under the floor with both bounds free and shows the beat opening
nothing.

**Met:** the floor is still read before either bound in `api/dial.py::_take_next`;
`tests/api/test_dial.py::test_the_memory_floor_stops_a_reading_too_and_stops_it_first`
puts the machine under the floor with nothing running and nothing reading,
and the beat opens nothing until there is room. The existing floor test is
unchanged but for the head's new sentence.

### 4. The board says which of the two it is holding back, and never confuses it with a card it gave up on
`needle dial`'s last line reports the two bounds and what is live against
each, in place of one count that meant both. A reader meeting
`Claim.READINGS_STOPPED` on a card can tell the per-card fuse from the
board's own bound, because the two no longer share a word.

Done means: `needle dial` prints lanes and readings separately with their
bounds; the head's sentence agrees with it; `docs/vocabulary.md` carries
whatever word this plan lands on, and the doctrine ratchets stay green.

**Met:** `needle dial`'s last line reads "N fix lanes at most across every
board; M live now; 3 readings at once, K open now", pinned by
`tests/api/test_dial.py::test_the_board_says_which_of_the_two_it_is_holding_back`
and restated wherever that line was already asserted. The head shows the same
two pairs, pinned where it is rendered rather than where it is printed:
`frontend/tests/board.test.tsx`'s two card-154 cases read "2 of 3 readings"
beside "1 of 1 live" and check that the readings pair claims nothing while
nothing is being read (the cold read caught the record claiming the terminal
test covered the page).
The word landed on is "reading", which `docs/vocabulary.md` already gives as
the owner's word for this (under **triage**), so the file needed no line; a
card the per-card fuse stopped still says the board stopped reading *that
card*, which no longer shares a word with the board's own bound.

Hands out: execution — runs the suite one module per process from the lane's worktree, then `tsc` and `vitest`, and reports every failure verbatim; verifies re-running each named failure alone before treating it as this change's.

### 5. The class is loud: an hour in which the board fixed and never looked is counted
`needle fixes <slug|all> --reading-gaps --count` prints how many hours in the
last day had a fix lane running and no reading opened. It is the plan's own
measure and the Loop's reader.

Done means: the command exists, prints a number, and prints a non-zero one
against a board seeded with the 2026-09-15 shape — four lanes and no reading
for two hours — so the count is proved to detect the thing before it is
relied on to show its absence.

**Met:** `needle fixes all --reading-gaps [--count]` prints the hours, or
their number; `tests/api/test_dial.py::test_an_hour_the_board_fixed_and_never_looked_is_counted`
seeds four lanes running for two hours with nothing read and reads 2, then
lands one reading inside one of those hours and reads 1.

## Acceptance — behaviours

- Auto-fix running at its full number never stops a defect being graded, a title being read cold, or a card parked on you being looked at.
- A board with a long rail of unread cards opens a few readings at a time, never one per unread card.
- A machine under its floor opens nothing at all, as today.
- The number you set still means what it meant: how much work that commits runs at once.
- You can see, in one line, what the board is holding back and why.

## Rulings

1. The readings bound is a constant, not a setting. The owner already sets one number and a line per board; a third knob for a thing whose real ceiling is memory would be a knob he has to think about to no benefit. If the constant is ever wrong, the evidence will say so and that is a one-line change with a reason, not a setting.
2. The number keeps its name and meaning. Renaming it would rewrite every citation in the archive to buy nothing; what changes is what it counts.

## Deliberately not

- Not an owner-settable readings bound (ruling 1), and not a per-board one: the floor is per machine and so is the pressure.
- Not a change to what any reading is asked, or to who reads: that is card #74's and card #82's ground and both are settled.
- Not a change to the per-card fuse of card #138: a third reading of the same text still stops, and should.
- Not a priority change between defects, titles and parked cards: the order is card #82's ruling 9 and this plan leaves it exactly as it is.

## Loop

The thesis: readings fell to zero because they queued behind work that
commits, so giving them a bound of their own restores them without letting a
long rail flood the machine. If an hour ever again has a fix lane running and
no reading opened, the split did not hold and the bound is the first thing to
look at.

Loop: WATCH: no hour passes in which the board fixed and never looked — command `uv --project /home/dennis/Work/needle run needle fixes all --reading-gaps --count` expect 0 by 2026-10-15 every 1d
