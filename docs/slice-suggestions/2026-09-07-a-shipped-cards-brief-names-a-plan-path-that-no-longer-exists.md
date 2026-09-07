# A shipped card's brief names a plan path that no longer exists

**Kind:** defect
**Fix:** now — HOW-WE-WORK §14 says "the plan is archived and every citation follows it", and the brief's `also:` line is the board's own citation list; the fix is in `board/assemble.py`'s `other_citations` (or wherever a card's citations are resolved): a citation whose stem is the archived document's is the same document and is dropped, not shown as a second file — which holds every shipped card on every project rather than one
**Found by:** the review on Omarchy card #25 (`omarchy-machine/docs/reviews/2026-09-07-25-codex-on-a-key-beside-claude.md`), 2026-09-07

## Observation

Read live on 2026-09-07 with `needle card omarchy 25`, `… 20` and `… 23`.
Each shipped card's brief prints its archived plan on the `open:` line and
then, on an `also:` line, the same plan's pre-archive path under
`docs/plans/`, which no longer exists:

```
   open: docs/plans/done/2026-09-05-21-codex-on-a-key.md (archived)
   also: docs/plans/2026-09-05-21-codex-on-a-key.md
```

The card's citation of the live path was made when the plan was live; the
archive move relinked the card's document but left the citation, so the
brief names a file a session cannot open. Nothing in the project's own repo
cites the old path (grepped); the stale name lives only in the board's card
record.

## Why it matters

The brief is what a lane opens with, and it says where to look. A path that
is not there costs each session that trusts it one failed read and one
doubt about the rest of the brief. Small per card, and on every shipped card.
