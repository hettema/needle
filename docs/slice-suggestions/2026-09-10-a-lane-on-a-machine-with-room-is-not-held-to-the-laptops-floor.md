# A lane on a machine with room is not held to the laptop's floor

**Kind:** defect
**Fix:** now — the intent is written (card #83's plan, item 4: the horsepower takes the cards the laptop cannot hold; card #107: every lane's scope carries the floor as its high mark so a lane never takes the memory the laptop needs); the fix stays inside the room's rule (`domain/dial.py`, `runtime/service.py::room`) and removes the class — the mark a lane's scope carries is that machine's floor against that machine's memory, not the laptop's five gigabytes everywhere — rather than a number changed by hand.
**Found by:** the lane on card #83 (2026-09-10, 18:36Z): the first card the board placed on the rented machine, Hello Revenue #503, ran under a scope whose high mark was 5 GB on a machine with 24 GB free, and the head read `rented horsepower the machine is full: needle-card-503-….scope holds 5.1 GB, past the 5 GB high mark`.

## The intent it breaks

The five-gigabyte floor is the laptop's: the memory the owner's own work needs kept free on a 16 GB machine, and the high mark every lane's scope carries (card #107) so that a lane that grows is held before the kernel kills something else. On a 32 GB machine with 24 GB free the same mark throttles the one lane the machine exists to run, and the head calls the machine full while it is nearly empty. Item 4's placement rule already reads each machine's room; the mark and the sentence should read the same machine.

## Evidence

- `needle machines` on the laptop's board at 18:36Z: `rented  horsepower  the machine is full: needle-card-503-a-website-heavy-with-video-still.scope holds 5.1 GB, past the 5 …`, beside `30.3 GB available` on the same machine's line an hour earlier.
- `api/loops.py::headroom_now` sets every machine's lane scopes' high mark to `MEMORY_FLOOR_BYTES` ("every lane's scope carries the floor as its high mark, whoever made the scope, card #107: set where it is missing on every machine").

## What done looks like

A machine's floor is a machine's fact (its own `room` answers it, from its total and what the owner keeps free there), a lane's scope on that machine carries that floor, the head's "full" reads it, and a lane on the rented machine grows to what the machine has.
