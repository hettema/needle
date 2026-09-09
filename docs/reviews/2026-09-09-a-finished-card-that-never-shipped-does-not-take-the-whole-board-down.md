# Review — a finished card that never shipped does not take the whole board down (card #105)

**Plan:** none — a `now` defect fixed at the owner's word ("get the Hello Revenue needle back up and fix the bug", 2026-09-09 13:30) while Hello Revenue's board answered 500 on every read; the suggestion is `docs/slice-suggestions/done/2026-09-09-a-finished-card-that-never-shipped-does-not-take-the-whole-board-down.md`, filed by card #41's lane and carried by the fix.
**Reviewer:** the building session (Claude Fable 5.1, interactive, hrclaude then hrme 89b15944), on its own work. No reader of the other make was in the loop: the board was dark for the owner and the fix was two seams in one file. The served board after the fold is the sign-off this record cannot replace.
**Diff range:** 75a6df1 to c60022b on the branch `defect/one-face-never-darkens-the-board` — one commit: `board/assemble.py`, two tests, the carried suggestion.
**Findings:** 2 — both fixed before the fold.

## The passes

1. **The work against the suggestion's "what would fix it".** Two fixes, both landed: `_lane_died` reads `close_landed`, the same fact the lane's sentence reads, so a card whose close landed is finished on the face as in the sentence wherever it sits; and `summarize` builds the face or, when `CardState`'s validator refuses it, a red face carrying the validator's own words, so a refusal is one card's face and never the project's board. Each held by a test in `tests/board/test_language.py` and `tests/board/test_assemble.py`; the first was run once against the old line and raised the same `ValidationError` before it counted.
2. **The seams.** The fallback face keeps the validator's bar (a lying face is still never shown; a red face saying the sentences disagreed is) and the head counts no new claim for it — a new `Claim` member would have crossed the typed edge into the frontend for a case the fix removes. The three cards that tripped it (Hello Revenue #219, #246, #253: archived plan, DELIVERED row, no fold on record, all in Decision moment) read "your move" with the quiet lane sentence after the restart; no `ValidationError` in the journal since.
3. **The boundaries.** Layers unchanged; the board still runs nothing; every suite except `tests/api` green with the ratchets, the api suite green in the lane; the one red is the owner's-words ratchet on a 2026-09-08 suggestion titled with "fold", outside this change.

## Dispositions

1. [feature] **The face called a finished lane dead while its sentence called it finished.** FIXED: `_lane_died` excludes a card whose close landed.
2. [seam] **A validator raising inside the assembly took the project's whole board down.** FIXED: the refusal is one card's red face with the validator's words.

## Not done, stated

- No independent reader read this fix; the second and third passes are the author's. The owner's rulings of the same afternoon ("1. yes") sent the next defect, card #107, through the full loop with Codex, and the record there names what an independent reader found in work of this size — seven findings on a first commit — which is the reason this record says so plainly.

## The served board, after the fold

Read at 15:14 on 2026-09-09, after `needle fold` from the lane and `systemctl --user restart needle-serve`: every project's board 200; #219, #246 and #253 "your move" with "Nothing for you: its close landed and the session on it ended 5 d ago."; zero `validation error for CardState` lines in the two minutes after the restart.
