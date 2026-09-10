# A card never shows another project's session as its own

**Kind:** defect
**Fix:** now — the intent it breaks is written (`CLAUDE.md`: the board reads what runs; `docs/INTENT.md`: the card's state is a machine fact with named evidence), the fix stays inside the one selector that matches a session to a card's work, and it removes a class — matching by name where a name carries no project — rather than an instance: match by the path of the session's own copy of the code, which is the project's
**Found by:** the lane on card #110 (docs/plans/done/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes-and-a-colleague-checks-both-before-it-ships.md), in the review's cold read of round eight (call 77)

## The intent it breaks

A card's face says who is working on it, and that is a machine fact with its evidence. Two projects on the board can each have a card 1 with the same title, and the board then pairs a session working on one of them with the other project's card too, so a card can say a colleague is on it who is on something else, and the close of that card judges its cold readers against the wrong colleague's kind. What he loses while it does: the face of a card he trusts to say who is working, and a close that can accept a reader of the author's own kind on the strength of a stranger's session.

## The evidence

`board/lane.py::_sessions_in` (line 177 as this is written) takes a session for a card's work when its worktree or its cwd is the card's own copy of the code, **or when its name matches the card's** — and a card's work is named `card-<number>-<slug>` with no project in it (`board/brief.py::lane_name`), while card numbers are allocated per project (`infrastructure/store.py`, `next_number`). The cold reader of card #110's round eight reproduced it: an ended Codex session on one project's `card-1-same-title` and a live Claude session on another project's lane of the same name; `lane_for` chose the foreign Claude session as the card's. Card #110's close reads a lane's kind from a session on the lane's own path instead and never from this selector, so its close is safe; the face is not. The fix is one clause: a session is the card's when it is on the card's path, and a name alone is not evidence.
