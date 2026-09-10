# A session's message is answered at once and never sent twice
**Carried by:** docs/plans/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md

**Kind:** defect
**Fix:** now — the intent is written (plan 10, item 1: "a running lane hears the board", whose hook posts and queues; card #83's plan: the board feels like it is on your laptop), the fix stays inside the board's intake and the hook script, and it removes a class: every message a session sends, on every machine, is answered before the pass it causes.
**Found by:** the lane on card #83 on the first evening a lane ran on the rented machine (2026-09-10, 18:20Z–18:45Z), reading why the rented machine's five queued events had not reached the board.

## The intent it breaks

A session's hook posts what happened to the board and gives it two seconds to answer, then leaves the event in a queue beside the store to be sent again with the next one; the board answers a post only after the full pass the post causes. That pass took 26 s on 2026-09-10 (a hundred lanes on the laptop and one machine over the wire), and had taken longer than two seconds for a day: the laptop's queue held 263 events reaching back 21 hours, and every hook firing re-sent all of them. The board still held every one — a post the hook gave up on is finished by the server — so the board did not lie, but each firing cost it a pass and wrote the batch again (1,582 groups of the same event recorded more than once before the day began; the rented machine's turn end at 18:23Z is in the store twice). What he loses: a board busy answering its own echoes, and a hook that has never once heard its answer, which is the trace plan 10 built the queue to be.

## What fixes it

- The board records what a session sent and answers at once; the pass the post causes runs after the answer, once, however many posts arrive while it runs.
- An event the board already holds — the same session, kind and moment — is kept once, so a re-sent batch costs nothing and the day's echoes are folded to one.
- The hook keeps its two seconds — a session is never slowed by its board — and drains its queue on every answer, which now comes.

## What would settle it

Live, the queue file beside the store is empty on both machines a minute after the fold and stays so; on the fixture, a post is answered in under a second while a pass is stalled behind a machine that does not answer, and the same batch posted twice records once.
