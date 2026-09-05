# One word names two different things on the board

**Kind:** defect
**Fix:** his one of the two surfaces is already shipped and its name is on a URL and in the page's own language, so which word moves is a call about what the owner reads, not a call the code can make
**Found by:** the lane on card #59 (docs/plans/2026-09-05-a-defects-mark-is-verified-before-it-routes.md), in the review's boundaries pass

## Observation

"Triage" now names two unrelated things on this board.

Plan 05 shipped the **triage lens**: the view that lists every unread verdict
as one line, ruled from the attention rail. It is a word on the page
(`frontend/src/board/Triage.tsx`, `TriageList`, `TriageGroup`, `TriageRow`,
the `triage` lens in `dnd.ts`) and on a URL
(`POST /api/projects/{slug}/triage/accept`).

Card #59 shipped the **triage seat**: the independent reading that verifies
who fixes a defect before it routes. It is `SessionWork.TRIAGE`,
`RowKind.TRIAGED`, `needle triage`, `board/triage.py`, `domain/triage.py`.

Neither is wrong on its own. Together they are the failed alignment
`CLAUDE.md` names: a session reading "triage" in one place learns the wrong
thing about the other, and the first search for "the existing one" finds a
false match.

## What would hold it

One of the two takes a different word, everywhere it appears — the code, the
page, the URL and the corpus — and nothing on the board says "triage" of the
other thing. The lens is a *ruling* view of verdicts; the seat is a
*reading*. Both readings are available and neither is obviously right, which
is why this is a decision rather than a rename.

## Why it is the owner's

The lens's name is what he sees on the head and reads in the page's own
language, and its URL is shipped. The seat's name is what he and Sol used
throughout card #59's plan and challenge, and it is the word in the doctrine
he ruled on. Choosing which one moves is choosing which vocabulary the board
teaches, and that is his.
