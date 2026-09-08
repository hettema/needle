# News that arrives late still corrects the card, and nothing is thrown away unread

**Found by:** Codex, reading #68 from its Discuss door on 2026-09-08 (round one, point 15), verified by Claude against `hooks/needle_hook.py`
**Kind:** defect
**Fix:** now — §11 is the written intent (a machine fact with named evidence, or the board lies while he is away) and §4's (only what is written survives); the fix is inside `hooks/needle_hook.py`'s drain and the death reader, and removes the class — every event that reaches the board after the board has already spoken — not one card. Filed outside #68 by its ruling 6, which makes the death reader revise on evidence at hand but leaves the transport alone.

## Observation

A session's Stop, StopFailure and SessionEnd events are queued on disk while the board is down and drained on the *next* event (`hooks/needle_hook.py:279–293`), so the last event of a session that ended while the board was away sits in the queue until some other session fires a hook. The drain drops events older than seven days unread (`:162–190`). Meanwhile the board has already written the lane's ending from what it could see — the registry's state, the scope's journal — and the late event, when it lands, changes nothing on the face: #68's item 1 makes the reader revise from evidence it holds, but a queued event is evidence it does not yet hold.

## Evidence

- `hooks/needle_hook.py:162–190`: the drain and its seven-day cut; `:279–293`: the queue drains only when a new event arrives.
- `api/loops.py:569–573` (before #68): the first epitaph is kept for the process's life.
- A night the board is down: every lane's last hook waits for the first hook of the morning.

## Why it matters

The card's word on how a lane ended is what the owner reads; a Stop that says "asked the owner" arriving eight hours late leaves eight hours of "not established" or worse on the face, and a week of absence loses the ending altogether.

## What would fix it

The queue drains on the board's return as well as on the next event (the board asks the hook's queue at start, or a timer drains it), and a dropped event is posted with its age rather than discarded; the death reader treats a late SESSION_END or Stop as evidence that revises the ending, with the card's history saying when it arrived. Fixture: an event queued while the board is down, delivered after the board has written an ending; the ending changes and the row says why.
