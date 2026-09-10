# A card remembers which session it started, whatever that session is called into later

**Kind:** defect
**Fix:** now — the intent it breaks is written (`docs/INTENT.md`: the board's state is a machine fact with named evidence; plan 11: the board's own record of where a session it started runs), the fix stays inside the one row the runtime writes when it starts a session on a card, and it removes the class — a fact overwritten by a later, unrelated write — by keeping the card a session was started on beside the scope it runs in now, rather than in one field a call re-uses
**Found by:** the lane on card #110 (docs/plans/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes-and-a-colleague-checks-both-before-it-ships.md), in the review's fourth pass (call 83)

## The intent it breaks

When the board started a colleague on a card, that is a fact for the card's life: the close judges a review's cold readers against that colleague's kind, and the face says who is working. Today a warm call to that colleague overwrites the one row that said which card it was started on, with the call's own name, so an hour later the board no longer knows the lane's author from a reader that happened to run in its directory. What he loses while it does: a close that can refuse a legitimate cold read as the author's own kind, or accept the author's kind as a stranger's — the check card #110 built rests on a fact the board forgets.

## The evidence

`runtime/launch.py::call_codex` records the resumed worker with `record_session_slot(SessionSlot(session_id, slot, card=<the call's name>, scope=<the call's unit>))`, and `infrastructure/store.py::record_session_slot` keeps one row per session, replacing the previous card. Card #110's close reads a lane's make from the session on the lane's path that the slot row names the card for, else the one holding the worktree, else one that can write where a cold reader runs read-only — evidence that stands while nothing re-cards the row. The fourth cold reader of that card reproduced the loss with the production store in memory: a Codex author and a Claude reader in its directory, accepted; the author called warm, its row re-carded; the same record refused. The fix: the slot row keeps the card a session was started on as its own field, and a call writes its scope beside it, never over it.
