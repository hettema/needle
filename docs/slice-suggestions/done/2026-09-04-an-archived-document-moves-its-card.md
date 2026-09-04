# An archived document moves its card

**Found by:** the coordinating session, 2026-09-04 15:30, when the owner
looked for slice 04 on the board and the three slices already shipped were
still sitting in Planned and Up next.

## Observation

Slices 01b, 02 and 03 folded, their plans moved to `docs/plans/done/`, and
the corpus watcher recorded "its document was archived" on each card. Nothing
moved the cards. The machine's exit rule only runs for a card in Executing
with a lane it has seen, and those lanes ran under worktrees named for the
slice, not for the card, before Needle's own close door existed, so no
DELIVERED row was ever written through Needle.

"Shipped means archived" is an intent (`docs/INTENT.md`). A document that is
archived while its card sits in Backlog, Planned, Up next or Executing is a
shipped piece of work the board is still calling pending.

## Done means

- On the corpus's `archived` effect, a card outside a shipped column with no
  live lane moves by the machine: to Executed when it carries a DELIVERED row
  and a readable WATCH row, otherwise to Decision moment with the reason "its
  plan was archived, but no session wrote it up on the board" — the same
  reason the exit rule already uses for a folded lane.
- The move writes an audit row naming the archived document.
- A test: archive a card's document while the card is in Up next with no
  lane; the card is in Decision moment on the next read with that reason.
- The owner's placements are never moved by this rule while a lane is live
  on the card; a live lane's close decides.
