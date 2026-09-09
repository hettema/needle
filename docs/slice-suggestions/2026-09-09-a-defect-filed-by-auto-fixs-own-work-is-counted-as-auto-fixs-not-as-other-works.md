# A defect filed by auto-fix's own work is counted as auto-fix's, not as other work's

**Kind:** defect
**Fix:** now — plan 11's item 6 (`docs/plans/done/2026-09-04-11-defects-fix-themselves.md`) is the written intent: the defects at the top of Backlog are counted by who filed each, a fix the board started apart from other work, so the owner can see whether the path that drains the strip is also feeding it, and its ruling says a class-closer is mandatory for exactly that reason; the fix stays inside `board/dial.py::filer_of` and the count it feeds, reading the card the Found by line names against the board's own record of the fixes it started (`fix_lanes`) instead of the words, and removes the class — every wording a fix session uses for itself
**Found by:** #34's reading, 2026-09-09

## The intent it breaks

When auto-fix has run, the owner is meant to see how many of the defects waiting at the top of Backlog were filed by auto-fix's own work and how many by other work, because a fix path that files as many defects as it removes is feeding the strip it drains. Today the count says auto-fix filed none of them on Hello Revenue, when sixteen of the live defects there were filed by the fixes the board itself started. The number he reads to judge whether auto-fix pays for itself is wrong on the one axis it exists for.

## Evidence

- `needle fixes all`, read 2026-09-09, closes with `rail hellorevenue: 42 (was 26 at dial-on) — feature lane 22 (was 8), reading session 7 (was 3), owner 2 (was 3), unknown 11 (was 12)`: no line for a fix the board started, on the board where it started 41.
- `board/dial.py::filer_of` decides the filer from the opening words of the Found by line: it says *fix lane* only when the line contains the words "fix lane" or "started by the dial", and reads "the lane on card #N" as other work. Every fix the board started wrote its own filings as "the lane on card #N (docs/plans/done/…), in the review's … pass" — the same wording every other session uses, since the filing brief teaches one wording.
- Read the same way over Hello Revenue's live suggestions on 2026-09-09 with the board's own function: 24 classified as other work, 16 of those name a card the board's `fix_lanes` record says auto-fix ran (#384, #399, #405, #420 three times, #422, #423, #425, #430 twice, #433, #434 twice, #436 twice). The board's record of which cards it started is the fact; the words are a guess at it.
- `docs/slice-suggestions/2026-09-05-a-fix-that-files-what-it-found-outside-its-change-still-counts-as-done.md` (#48) reads the same line for the *undone* count and already proposes deciding *by* against *against* from the card number; the filer count is the sibling reading of the same line and is not in #48's fix.

## What would fix it

The filer is read from the board's own memory: a Found by line that names a card the board started as a fix is a fix's filing, whatever words it uses; the prose heuristic stays only for the three filers the board has no record of (the owner, a reading, other work). The count at the moment the dial was turned on is re-read the same way so the two columns compare like with like. A test drives one Found by line in the wording the filing brief teaches, on a card the record says auto-fix ran, and asserts it counts as auto-fix's.
