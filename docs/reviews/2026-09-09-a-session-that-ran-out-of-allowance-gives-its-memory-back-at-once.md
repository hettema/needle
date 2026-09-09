# Review — a session that ran out of allowance gives its memory back at once, so the machine has room to bring it back (card #107)

**Plan:** docs/plans/done/2026-09-09-a-session-that-ran-out-of-allowance-gives-its-memory-back-at-once-so-the-machine-has-room-to-bring-it-back.md
**Reviewer:** the building session (Claude Fable 5.1, interactive, hrme 89b15944) read the done-means; a reader of the other make (Codex 0.153.4, `codex exec -s read-only`, reasoning effort high, run in the lane's checkout with each commit's patch) read the seams and the boundaries and re-read every fix cold. Its answers are verbatim in `codex-pass1.md` to `codex-pass4.md` of the building session's scratchpad and are quoted below where they bear.
**Diff range:** 74b5bbf (the plan on the trunk) to the lane's tip on `card-107-a-session-that-ran-out-of-allowa` — the feature commit 87f4a56, the fixes 2b8babf and edeafb4, and the close.
**Findings:** 17 across five reading passes — 13 fixed and re-read, 3 no change with the reason written, 1 filed as a defect in the corpus.

## The passes

1. **The work against its done-means (the building session, on 87f4a56).** Item 1: the stop landed at the floor park and the floor test showed the process gone in the parking pass, the ending named a wall on the next, and the relaunch on the handoff's account once the room held; the face reads "coming back", the board's word for a parked lane whose process is gone, where the plan's letter said "moving" — stanced as deviated, with the six-at-once clause held by the pass reading the machine per lane rather than by a test. Item 2: `MemoryHigh` on every lane adoption, asserted on the floor's `busctl` call and rehearsed on a throwaway scope of this machine's user manager (systemd 261, 5368709120 read back). Item 3: the constant moved to `domain/dial.py` with its reason, because the runtime cannot import the board. Findings 1–2 below.
2. **The seams and the done-means, read cold (Codex, on 87f4a56).** Seven findings, 3–9 below: the six real lanes were parked before the rule and would never have been stopped; a limit with no handoff, once stopped, is lost; the stop preceded the park; a hand stop on a walled session was resumed as a wall; a young handoff's rung reused after a long wait; "moving" and "cap" overclaimed. Fixed in 2b8babf.
3. **The fixed work, read cold again (Codex, on 2b8babf).** Four resolved; five findings new or partial, 10–14 below: the owner's stop after the board's floor stop was still brought back because the stored death said wall; the rung check read only the soonest reset and read an allowance spent with no return time as back; the check hung on a flag a restart forgets; a stop on a standing park left the snapshot a pass behind; two intent paragraphs still promised a cap and a moving face. Fixed in edeafb4. The boundaries lens: "nothing new in layers, process ownership, typed edges, or deferral markers."
4. **The fixed work, read cold a third time (Codex, on edeafb4).** "New defects introduced by this commit: nothing new beyond those incomplete fixes"; boundaries "nothing new". Two carried items: the owner's stop removed the handoff before writing the death over, so a crash between the two left a wall to recover (17, fixed by the reorder in the next commit); two servers may both stop a standing park's process and both write the line (14, no change with the reason). 
5. **The reorder, read cold (Codex, on 13970d8).** "Finding (3) resolved: the settled STOPPED death now commits before handoff removal, and recovery honors it after restart. nothing new." The clean pass after a pass with findings; the loop ends here.

## Dispositions

1. **The face after the stop reads "coming back", the plan said "moving".** A process that is gone is not moving; the board's word for a parked lane with no process is the true one. NO CHANGE to the code; the plan's item, intent and acceptance now say "coming back", and item 1 is stanced deviated on this clause.
2. **The six-at-once clause is not shown by a test.** The pass reads `headroom_now()` for every lane, so the room one stop frees is read for the next; the floor's memory is a file, and a test that rewrote it between two lanes of one pass would be testing the test. NO CHANGE; stanced deviated with the pointer.
3. **Lanes parked on the floor before this rule landed bypassed the stop.** The six real lanes of 2026-09-09 were exactly that. FIXED: a standing floor park whose walled process still stands is stopped on the next pass, and a test parks a lane through the store first (`test_a_lane_parked_on_the_floor_before_this_rule_has_its_process_stopped_next_pass`).
4. **A failed stop was never retried.** FIXED by the same path: the stop is asked again each pass while the process stands, and the "Asked" line is said once.
5. **A limit read from a stop-failure event with no handoff, once stopped, reads as a plain stop and the park lifts with nothing to bring back.** FIXED: only a session with a standing handoff is stopped (`_holds_room_it_waits_for`); the rest keep their memory and their evidence.
6. **The stop preceded the park, so two servers could both stop and a crash between the two lost the wait.** FIXED: the park is the claim, written once by the store, and the stop follows it; a crash between leaves a parked lane the next pass stops.
7. **A hand `needle stop` or the Stop door on a walled session was resumed as a wall, against the plan's own acceptance.** FIXED: `Runtime.stop` removes the handoff unless the board's own stop asks to keep it; a test shows the owner's stop taking the handoff with it and the lane staying down.
8. **A young handoff's rung was reused after a wait onto an account that may have walled meanwhile.** FIXED: `_rung_open` reads that account's own latest allowance reading before the rung is kept; a test walls beta between the park and the lift and sees the rule place the lane on alpha.
9. **`MemoryHigh` is a throttle the kernel may let a scope exceed, not a cap; the plan and the docstrings said "capped" and "never the reason the browser is".** FIXED in the words: high mark, throttle, presses on itself first.
10. **The owner's stop after the board's floor stop was still brought back: the stored death said wall, `_name_deaths` keeps a settled death, and `_interruption` recovered it.** FIXED: the owner's stop writes the death over as stopped, settled; a test stops after the floor stop, returns the room, and sees no launch.
11. **`_rung_open` read only the soonest reset and read a spent allowance with no return time as open.** FIXED: every spent allowance is read, and one with no return time closes the rung; the rung test runs with a known and with an unknown reset.
12. **The rung check hung on `waited`, which a restart between the lift and the resume forgets.** FIXED: the check runs on every pass whenever the wall is young; the flag is gone.
13. **A stop on a standing park did not set `changed`, so the snapshot could keep the stopped pid a pass longer.** FIXED: `_give_memory_back` answers whether the process is gone and the pass re-reads the machine on it.
14. **Two servers reading one standing park may both stop its process.** The second stop finds a process already gone and, with the "Stopped" line now said once from the history, adds nothing; a stop is idempotent. NO CHANGE beyond the dedupe and the comment, which no longer claims two servers cannot both stop.
15. **The plan's intent paragraph still promised "moving" and "can never hold more … capped".** FIXED in edeafb4.
17. **The owner's stop removed the handoff before the death was written over; a crash between left a settled wall death to recover after restart.** FIXED: the record goes first, the handoff second, so the crash leaves a settled stop the loop honours.
16. **A Codex reader run inside the lane's copy was read by the board as the lane's session; when it ended, card #107 showed "session died" in red with a Resume that cannot work on a Codex row.** Outside this change. FILED: `docs/slice-suggestions/2026-09-09-a-colleague-reading-a-cards-code-is-not-mistaken-for-the-session-building-it.md`, `**Kind:** defect`, `**Fix:** now`.

## What was checked

- The floor suite and the api suite in the lane after each pass; every suite but `tests/api` with the ratchets; ruff on the touched files. The one red on the trunk before and after this lane is the owner's-words ratchet on a 2026-09-08 suggestion whose title says "fold", outside this change and left.
- `MemoryHigh` on a real transient scope of this laptop's user manager (systemd 261): the property lands through the same `busctl` call and reads back as 5368709120.
- The frozen revision under each pass was the commit named; the fixes went into the next commit, and the next pass read that.

## What the build learned the plan got wrong

- The wait's face: "moving" is the board's word for a live process on its way; a parked lane with its process gone is "coming back". The plan's letter was written before the mechanism.
- "A lane can hold at most what the floor is" was a cap the kernel does not promise; `MemoryHigh` throttles and reclaims and may still be exceeded under pressure. The words now say so.
- The acceptance line for a hand stop assumed the handoff would be the difference; it was, in the wrong direction — the handoff made a hand stop resumable — until the owner's stop was taught to remove it.

## Not done, stated

- The six-at-once shape is held by a per-lane read of the machine, not by a test (disposition 2).
- The machine's own preference for what its killer takes first is filed in the machine's record (`/home/dennis/Work/omarchy-machine`, defect of 2026-09-09, commit 0de0913 there), not built here; until it lands, the killer's target on a full laptop is still the largest scope it sees.
- The `Loop:` lines are written as WATCH rows at the close; their first readings are due by 2026-09-23.

## The served board, after the fold

Written at the close.
