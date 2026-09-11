# A card worked on the rented machine can be closed once its review is done

**Kind:** defect
**Fix:** now — the close rule card #110 wrote into docs/reviews/README.md refuses a record whose readers the board holds no row for, and card #83 made the rented machine a place cards are worked; a reader asked from there is recorded only on that machine, so recording every reader where the board is, or having the close look on the machine the work is on as it already does for that work's sessions, lets every card worked there close, not one.
**Found by:** the lane on card #124 (docs/plans/done/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md), in the review's seams pass

## The intent it breaks

A card is closed the same way wherever its work ran: once its review is read
by a colleague of the other kind and written down, the close records what you
now have and the signal that will prove it. Today a card worked on the rented
machine cannot close at all, however complete its review, because the board
on the laptop cannot see the reads that were asked from the rented machine;
the card sits finished and folded but never closed, and every card run there
will meet the same wall.

## Evidence

- `needle close needle 124 …` on 2026-09-11 ~13:15Z refused: "docs/reviews/2026-09-11-a-sessions-message-is-answered-at-once-and-never-sent-twice.md:23 names call 91, which the board has no row for — a cold read goes through `needle call` so the call is a row, not a launch" and the same for calls 92, 95, 97 and one more.
- Every one of those reads went through `needle call codex --fresh` from the lane on the rented machine, and each answer landed (`~/.cache/needle/card-124/from-codex-fresh-*`).
- The rented machine's own store (`~/.local/share/needle/needle.db` there) holds call rows 90 to 100; the board's store on the laptop holds calls up to 83 and none of 91 to 99 — read 2026-09-11 with SQLite, read-only, on both machines.
- `api/doors.py::close` passes `call_of=self.live.store.call` (the board's store) to `board/review_rules.py::verdict_faults`, while a few lines earlier it finds the lane's sessions on the machine the lane is on (`self.runtime.lane_machine(where)`).
- In `api/runtime_cli.py` the `call` and `wait` verbs are not marked to run on the board, unlike the verbs registered with `set_defaults(board=True)`, so a lane's `needle call` records where the lane runs.
- Card #124 is folded (origin/develop 6ebc97c) with its review complete and cannot close until this is fixed; card #123, also worked on the rented machine, will meet the same refusal.
