# Review — the loops move in (slice 04)

**Plan:** docs/plans/done/2026-09-04-04-the-loops-move-in.md
**Reviewer:** the build session (Claude Fable 5.1 at high), reviewing its own diff before the fold. No second session was in the loop; the owner's read of the batched question on 11 September, and of the doubted cards after the restart, is the sign-off this record cannot replace.
**Diff range:** 047355a..HEAD on `worktree-card-6-04-the-loops-move-in` (the evidence type and the audit row's evidence column with migration 0004; the predicates in `board/evidence.py`; the exit and landing verdicts carrying their evidence; the store's placements query and the whole-text history on a rewritten row; the runtime's focus verb and the fake compositor's active window; the doors row, the closed doors' reasons, the doubt mark, the standing and the batched list on the page; the tests; the README).
**Findings:** 9 — 7 fixed before this record, 2 no change.

## What was checked

- **Against the real compositor, once, with a throwaway store**: a window opened under `org.omarchy.board-watch-live-check-focus`, focus taken back to the terminal by the same Lua path, then `focus_window` bringing it forward and `hyprctl activewindow -j` reporting its address active on workspace 3; the owner's focus restored afterwards. The window ran `sleep 25` and closed itself; nothing else on the desktop was touched.
- **Against the real store, through `needle row`**: the 54 WATCH rows rewritten from this lane's checkout (the store migrated to 0004 on open, additively; the running slice-03 server kept serving), each row validated by `parse_watch` before it was written and the reader words checked out of every owner `what`; four history rows sampled afterwards and found to carry the whole original text; the measurement script re-run (54 of 54); the running board's attention line and Done column read over HTTP a minute later (#257 moved to Done on its command signal, #230 due to the owner).
- **The two command readers run through the runtime's own reader** (`runtime/signals.read`) from the Hello Revenue root before they were written: the review count read not delivered (2 of 3), the stamp read delivered (1 of 1).
- **The suite on the fixture floor**: 233 backend tests (26 ratchets, the store-shape ratchet covering migration 0004), `npx tsc --noEmit` clean, 22 vitest scenarios (four new: the doors row under the title with closed doors' reasons, Focus its window, the doubt mark and count, the batched list with one click each way).
- **The five acceptance behaviours** as scenarios: the mid-close kill and the import's unknown-then-tested placements in `tests/api/test_doors.py`; the predicates in `tests/board/test_evidence.py`; the machine move's evidence and the whole-text history in `tests/infrastructure/test_store_doors.py`; focus proved and refused in `tests/runtime/test_windows.py`; the door's label in `tests/board/test_lane.py`.
- **The boundary ratchets**: layers (`board/evidence.py` imports domain and board only); the board never runs; typed edges regenerated for `audit`, `board`, `evidence`, `window`; no deferral marker; one design system (the four new primitives use tokens only); the fixture regenerated with every card's standing.

## Dispositions

1. **The focus script's address guard kept hex only, and refused the fake's `0xfake0001`.** A real address is hex, but the guard's job is Lua-quoting safety, not hex. FIXED: alphanumerics are kept, everything else dropped.
2. **The fake compositor kept the previous focus when told not to honour a new one, so a refused focus read as landed.** FIXED in the fake: a refused focus leaves nothing active; the runtime's failure message names what the compositor reports instead.
3. **The plain kill never shows a doubt: the mover and the doubt read the same facts and the move lands in the same read.** NO CHANGE to the mover — the doubt exists for the reads where the mover waits or is refused; the acceptance test stages a close still landing (ruling 3).
4. **The first draft of the doubt scenario asserted zero doubts on the fixture board and found three.** The fixture's card file places three cards in machine columns on 0.1's word alone, and the first read doubts them. NO CHANGE: the doubts are true; the scenario measures the delta.
5. **The first draft of `standing_for` doubted the import's three Done cards.** 0.1's grammar made Done the owner's move. FIXED before commit (ruling 2): an unnamed placement in Done or Decision moment is trusted.
6. **`where_after` answered a tuple, so the signal loop's move had no evidence to record.** FIXED: a `Landing` model carries column, reason and evidence; the owner's reading door reads the same.
7. **The history cut a rewritten row's text at 140 characters, so the 54 originals would have been gone from the card.** FIXED: a rewrite's history row carries the whole previous text.
8. **The attention-line test and the store-door tests were written to the old contract.** FIXED: the two new counts, the evidence on a machine move, the whole-text history.
9. **`vitest` run from the repository root has no `jsdom`.** FIXED in the working notes only: run from `frontend/`.

## What the build learned the plan got wrong

- The plan asked for the comp to be "amended and re-signed in the plan's Rulings, not rebuilt"; `docs/design/README.md` freezes a signed comp. The two are reconciled by ruling 6: the amendment is the ruling, and the HTML file is untouched.
- The plan's item 4 sequenced Hello Revenue's edit behind card #387's fold. #387 folded and closed during this build and its lane already wrote the grammar line into the skill's close step; what remains is the per-reader examples, written out in the close-out for the coordinating session, since a lane's git never targets another repository.
- The plan's item 3 expected the batched question on the rail today. Under ruling 8's due-date rule only #230 (a kept date, 3 September) is due now; the other 51 come due on 11 September and arrive as one list then.
- The plan's item 1 expected a doubt on "kill a lane's process by hand" in the plain case; ruling 3 says why the mover answers that case and the doubt answers the others.

## Not done, stated

- **Hello Revenue's two instruction files are not edited by this lane**; the exact edit is in the plan's close-out.
- **The served page needs the main checkout's `frontend/dist` rebuilt and the login service restarted after the fold** (dist is git-ignored); until then the running board serves slice 03's page over slice 04's store, which it reads correctly (the 54 rows parse under both).
- **The doubted count on the live board (21 of Hello Revenue's Executed cards expected) is stated from the store's facts, not observed**, because the loop that tests them runs only under the served code; it is read after the restart and any difference goes on the card.
