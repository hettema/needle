# A finished card stays finished when its old session is asked to read someone else's work

**Kind:** defect
**Fix:** now — `docs/HOW-WE-WORK.md` §11 says a column is either the owner's ruling or a machine fact with its evidence, and Executing's evidence is hands on *the work*; a session woken to read another card's change is not hands on this card's work, so the read that moves the card is wrong wherever it is made, and correcting that one read ends the class rather than this card's instance
**Found by:** the session on card #123 (`docs/plans/done/2026-09-10-the-board-asks-another-machine-one-question-a-pass-and-answers-a-click-in-a-second.md`), asked through the board's call to read card #80's change, and seen pulling its own finished card open while it did

## The intent it breaks

A card the owner has seen finished stays finished. Today a card that shipped
is dragged back to Executing whenever a colleague asks its old session for
help on a different card: the board reads someone sitting in that card's
workspace as work on that card, and the owner, looking at his board, sees a
card he was told was done reported as under way again, with no one working
on it. He asked the obvious question — "is that card not finished yet?" —
and the honest answer was that nothing was happening on it at all.

## Evidence

- Card #123's own history on the served board, read from the board's memory
  on 2026-09-12: `2026-09-11T17:41:03Z moved Executing → Executed — closed
  by the session: DELIVERED and WATCH written`; `17:44:34 stopped … the lane
  folded and closed, so its session gives its memory back`; then
  `2026-09-12T14:20:57Z moved Executed → Executing — hands on: 8d7fb4a3 on
  gmail in card-123-the-board-asks-another-machine-o`.
- That session was woken by card #80's lane through `needle call` to be the
  independent reader its review needed (HOW-WE-WORK §13). Every act it made
  was card #80's: the findings note, a RULING row on card #80, a watercooler
  note to card #80. It committed nothing to card #123's work, which had
  folded to `origin/develop` and `origin/main` the day before.
- The owner met it on the board and could not place it: he asked why a
  question about card #80 appeared on card #123, and whether #123 was
  finished.
- The reading that moves the card is the one in `board/lane.py` that calls a
  live session in a card's worktree hands on that card (`lane_for`,
  `should_enter_executing`); the session's own record already names the card
  it was started for (`session_slots.card`, and the scope it runs in), so
  the fact has a truer source than the directory it sits in.
- Not the same thing as a lane whose work is genuinely unfinished: the card
  had its close recorded, its plan archived, its review record written and
  its work folded, and the board had already stopped its session once.
