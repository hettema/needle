# A card whose machine is full never stops the board reading the rest

**Kind:** defect
**Fix:** now — the intent is written (card #138: no card waits forever because the board keeps re-reading the same one; card #83's plan, item 4: the rented machine takes the cards the laptop cannot hold), the fix stays inside `api/dial.py` where the seat chooses its candidate and opens the reading, and it removes the class — any candidate the runtime refuses to open this beat, for room or any other reason the refusal names — not the one card it was seen on
**Found by:** the session at the Discuss door of Needle #138, 2026-09-14 16:45Z, asked "how is the defect triage going?": the seat had landed nothing since 16:05Z, and the laptop's board had written the same refusal on Omarchy #3 twenty-four times, one per beat, from 16:06:56Z to 16:42:31Z

## The intent it breaks

The board reads one card at a time and never lets one card hold the rest: the seat takes the oldest card that can run, and a card it cannot open right now is not the seat's to wait on. Since 16:06Z today every beat has picked Omarchy #3 — the oldest unread title on the board — asked the laptop for a reading, been told the laptop is full (3.6 to 4.1 GB available under a 5 GB floor), written that on the card, and read nothing else. Behind it: 67 Hello Revenue defects and 60 Needle defects nobody has read, whose projects run on the rented machine with 25 GB free, and the owner's own question of the hour — can auto-fix go back on — waits on that grading.

## Evidence

- `api/dial.py::_take_next` (lines 356-462) sorts every unread candidate on every board by age and hands the first to `_triage`, then returns: one act per beat, by design (card #100). `_triage` (622-635) asks the runtime to start the reading on the machine the project records; when the launch is refused it writes `The board could not start a reading of …: <reason>` on the card and returns. Nothing takes the next candidate, and nothing remembers the refusal for the next beat, so the same card is chosen again sixty seconds later.
- `api/dial.py::_full` (341-354) opens nothing only when *no* machine has room. A full laptop beside an empty rented machine is "not full", so the beat runs, and the oldest candidate happens to be one only the laptop can read.
- The laptop's board, `audit` rows since 16:00Z on 2026-09-14: 24 rows on `omarchy #3`, all `The board could not start a reading of the title: laptop is the machine this project records and it is full (the machine is full: 3.9 GB available, 5 …)`, none on any other card. `needle machines` at 16:45Z: `laptop … the machine is full: 3.7 GB available, 5 GB needed`; `rented … 25.7 GB available`. Readings landed since the number went back to 4 at 13:53Z: 79 by 16:05Z, then none.
- This is card #138's sibling. #138 closed the loop where one text was re-read 850 times because the reading could not move its card; here one card is re-*attempted* every beat because the reading cannot open. #138's fuse counts readings that opened and does not see this, and its WATCH row (readings per text) reads 0.

**Searched before filing** (2026-09-14): `docs/slice-suggestions/*.md` for "machine is full", "under the floor", "next candidate", "head of the line". `2026-09-10-work-placed-on-a-machine-with-room-is-not-held-to-the-laptops-floor.md` is about the floor's value on the rented machine; `2026-09-09-nothing-at-the-top-of-the-board-is-pushed-off-screen-when-the-machine-is-full.md` is about the head's layout. Neither is about which candidate the seat picks when a machine is full.

## What done looks like

The seat's candidates are the cards it can open this beat: one whose recorded machine has no room is left out before the sort, or, when the runtime refuses the launch, the beat takes the next candidate in the same pass instead of returning. The card that cannot be opened says so once — when the spell begins and when it ends — not once a minute, so its history is a record and not a log. A machine with room reads its own boards' cards while the other machine is full, and the head says which machine is holding which cards. Loop: the count of `could not start a reading` rows on one card in one hour is at most one, read from the board's own memory.
