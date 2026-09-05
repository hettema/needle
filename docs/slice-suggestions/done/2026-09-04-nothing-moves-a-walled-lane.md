# Nothing moves a walled lane; the board only says it is blocked

**Carried by:** docs/plans/2026-09-05-a-lane-the-machine-ended-comes-back-by-itself-and-the-boards-word-on-how-it-ended-is-true.md — folded from the board's Idea door on 2026-09-05 (conversation 6b683c8b), which read it beside #32, #33 and #68 as four findings about one loop; its first finding is already fixed, its second is item 3
**Kind:** defect
**Fix:** now
**Found by:** work-0c on the Omarchy board (2026-09-04 21:00), after the wall
detector was fixed and four lanes still sat still — the files were being
written correctly and nobody was reading them for action.

## Observation

`claude-acct handoff` files `<cache>/claude-acct/handoff/bg/<session>.json`
the moment a background lane's turn dies on a usage limit. The runtime reads
that directory in three places — `registry.sessions` (to mark the row
`blocked`), `launch.py:154` and `launch.py:288` — and every one of them is a
read. **No actor consumes a handoff file.** A walled lane therefore waits for
a human to type `needle move <short>`, exactly as it did before the detector
worked; the only thing that changed is that the board can now name it.

Between 20:12 and 20:36 on 2026-09-04 four lanes (cards 176, 26, 27, 196)
filed correct handoffs and none moved. They were moved by hand at 21:00,
roughly forty minutes after the first.

A second, smaller thing found in the same pass: **a handoff file is never
deleted.** `needle move` resumes the session and leaves the file, so the row
keeps whatever the file says. The one for card 26 survived its own move.

## What would hold it

An actor in the runtime's loop: for each readable handoff whose session is
still registered, run the move it names — `claude stop` under the old slot
first, then resume on the named one, which is the sequence `move` already
implements — then delete the file. Bounded the way the supervisor is bounded
(four moves in ten minutes stops the loop), so a slot that walls the moment
work lands on it cannot become a carousel.

Until that exists, the honest board behaviour is to say so: a row that is
`blocked` with a readable handoff is not waiting on the machine, it is waiting
on a person, and the card could offer the move as a door rather than leaving
`needle move` as folklore.

## Note for whoever builds it

`Model` accepts only the two rungs. `claude-acct` was writing a concrete id
(`claude-fable-5-1[1m]`) into the switch-back's `model`, which made every
background return-to-Fable unreadable; fixed on the claude-acct side the same
day — `model` is now always a rung and the exact id travels as `model_id`.
Prefer `model_id` when launching: the rung "fable" loses the 1M context
window that `roles.json` names.
