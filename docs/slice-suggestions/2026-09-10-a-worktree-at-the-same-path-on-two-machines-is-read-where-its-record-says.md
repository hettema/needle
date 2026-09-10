# A worktree at the same path on two machines is read where its record says

**Kind:** defect
**Fix:** now — the intent is written (card #83's plan, item 4 and its Terrain: a lane's edits, tip and documents are read on the machine that holds the lane, and the board's own record of where it was last seen seeds the routing); the fix stays inside `runtime/service.py::worktrees` and removes the class — when a path is found on more than one machine, the board's record of the lane (`lanes.machine`) decides, and a path on two machines with no record is said on the card rather than silently given to the board's own machine — rather than pinning the one path that bit.
**Found by:** the lane on card #83, the first fold through the board on the rented machine (2026-09-10, 15:50Z; docs/reviews/2026-09-09-the-work-runs-where-the-horsepower-is.md, the thirteenth pass)

## The intent it breaks

The board reads a lane where it lives. `Runtime.worktrees` reads this machine's checkouts first and every other machine's after, and a path found here is never overwritten by a path found there ("the main checkout is on both; a lane is on one"). The lane of card #83 stood at the same path on both machines — the rented machine held a copy of it for running the suite — so the board on the rented machine read the lane as its own: `edits` answered nothing, and the fold pushed the rented copy's stale tip, which origin refused as not a fast-forward. The lane's own record said `laptop`; the read did not ask it.

## Evidence

- `runtime/service.py::worktrees`: `for path in found: self._lane_machines[path] = here`, then for each other machine `if path in found and self._lane_machines.get(path) == here: continue`.
- `/tmp/fold_pieces.py` on the rented machine, 15:52Z: `lane machine: rented rented True`, `edits: []`, `fold: pushed=False words="git push origin: hint: See the 'Note about fast-forwards' …" tip=12af44d` — the rented copy's tip, three commits behind the laptop's lane.
- The fold verb's refusal was silent from the laptop: the forwarded `needle fold` exited 1 with the watercooler printed and no "not folded" line, on the rented machine too; a second finding in the same reading, to settle with the first.

## What done looks like

A lane found on two machines is read on the machine its record names; with no record, the card says the lane stands on two machines and the board reads neither until one goes. A copy of a lane's worktree laid on another machine for a suite run is a different path, never the lane's.
