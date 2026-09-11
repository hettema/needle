# Work waiting for an allowance never names a return time that has already passed

**Kind:** defect
**Fix:** now — #68's item 3 (`docs/plans/done/2026-09-05-work-the-laptop-interrupted-comes-back-by-itself-and-the-board-says-truly-how-it-ended.md`) is the written intent: a lane whose allowance ran out waits until the reset that allowance carries, and the card says what it waits on and until when as a machine fact with its evidence — a time already behind the clock is neither; the fix stays inside the park writer (`api/loops.py::_park`) and the store's park opener, and removes the class: the board's memory refuses any park whose end is not after its start, whichever reading supplied the end
**Found by:** #68's reading, 2026-09-11

## The intent it breaks

When work stops because its allowance ran out and the machine is too full to bring it back, the card is meant to say truly what the work waits for and until when. When the account's last reading still shows the allowance spent after the return time it names has passed, the board writes that passed time as the end of the wait, ends the wait on its next look, finds the machine still full, and writes the same passed time again — every half minute, until a fresh reading arrives. The owner reads "comes back at 14:39Z" at 14:53Z, and each card's history fills with two lines every half minute that bury the lines saying what actually happened.

## Evidence

- The board's memory on the laptop (`~/.local/share/needle/needle.db`, opened read-only on 2026-09-11): `parks` for hellorevenue holds 128 rows whose `until` (2026-09-09T14:39:59Z) is earlier than their `started_at` — 32 each on #409, #419, #426 and #483, started from 14:40:22Z to 14:53:52Z. Each was lifted 4 to 46 seconds later with *the wait ran to its end at 2026-09-09 14:39Z* and replaced on the same pass by a new park with the same end. The words of one (id 23): *it waits: Session (5-hour) on gmail comes back at 2026-09-09 14:39Z (the account's own reading of 14:39Z), or an account has room sooner; the machine is full: 3.7 GB available, 4.6 GB swap free, 5 GB needed; … it comes back once the room has held for a whole beat*.
- `audit` holds 66 `rescued` notes on each of those four cards between 14:40Z and 14:55Z, alternating *The wait ended: the wait ran to its end at 2026-09-09 14:40Z.* and *Waiting to bring it back after its allowance ran out on gmail (…) … comes back at 2026-09-09 14:39Z*.
- The same query over every project finds no other park born past its end, before or since; the conditions (a spent allowance read before its reset, and a full machine after it) have not met again. Nothing has changed the path: `api/loops.py::_park` (lines 1515–1521) takes the end from `runtime/limits.py::next_reset`, which returns the soonest reset of any spent allowance without comparing it with the clock (lines 54–66), and `_park_lifts` (line 1449) ends any park whose end has come before it looks at the machine's room. `git log --since=2026-09-09T14:50 -S"comes back at" -- api/loops.py runtime/limits.py` is empty.

## What would fix it

A reset already behind the clock is not an end: the wait says the account's reading is older than the return it named and asks the rule on every pass, as it does when no reading names a return. The board's memory refuses a park whose end is not after its start, so no other source of an end can start the same loop. A test on the test board drives a spent allowance whose reset is behind the clock, with the machine full, across several passes, and asserts one wait, no passed time in its words, and one note on the card.
