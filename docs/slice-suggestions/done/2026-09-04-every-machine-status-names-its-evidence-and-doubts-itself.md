# Every machine-placed status names its evidence, and doubts itself when it is gone

**Found by:** the coordinating session, 2026-09-04 14:40, after the owner
asked "how do we know the status is accurate?" — five cards had sat in
Executing for three hours with nothing running, and nothing on the board said
so until he looked.

## Observation

A column is one of two kinds of fact. The owner's rulings (Backlog, Planned,
Up next, Not now, and the gate on entering Executing) are true because he said
so. The machine's placements (Executing, Executed, Done, and every fall back
out of Executing) are true only while a named piece of evidence holds:

| Column | Evidence that must hold now |
|---|---|
| Executing | a session with a live process (`/proc`, start time matched) in a worktree that exists on disk for this card |
| Executed | the card's plan is archived and DELIVERED was written in this life of the lane |
| Done | the WATCH row's signal was read and said delivered, at or after its due time |
| Decision moment (machine-placed) | the lane ended and the reason on the audit row still describes the card |

Today the evidence behind five Executing cards had died hours earlier (spare
processes alive, worktrees gone; a DELIVERED row from a previous life). The
loop only re-evaluated when a lane event arrived, and the rule trusted the
process over the disk. The rule is fixed (7124cdb), but the shape of the
failure is general: a claim outlives its evidence and nothing says so.

## Done means

- The predicate behind each machine-placed column is written once, in
  `board/`, as a function of the same facts the loop reads, and every
  machine move records which predicate it satisfied.
- On every read, each machine-placed card is re-tested against its predicate.
  A card whose evidence no longer holds carries a visible doubt mark on the
  page ("the board doubts this: no live session in its worktree") and counts
  in the attention rail, before and independent of any move the loop makes.
- The owner's own placements are never doubted and never re-tested; the
  history row names him.
- A test: a card in Executing whose session's process dies is doubted on the
  very next read, and the doubt clears when the loop moves it.
- The 0.1 card file import marks every card it placed in a machine column as
  "imported, evidence unknown" so the first read either confirms or doubts it,
  instead of trusting 0.1's word (card #223 sat in Executing on that word).
