# A lane the board opened and nobody closes leaves nothing behind

**Kind:** defect
**Fix:** now `CLAUDE.md`'s close ritual already says the lane is removed at the close, and a lane no person ever closes is the one case where nothing carries that out
**Found by:** the lane on card #59 (docs/plans/2026-09-05-a-defects-mark-is-verified-before-it-routes.md), in the review's seams pass

## Observation

Card #59 gave the board a second kind of lane: a corpus lane, opened by the
board itself to apply a split or the owner's ruling, in its own worktree
under `.claude/worktrees/split-<n>-<slug>` or `ruling-<n>-<slug>`. It ends
when the corpus says what it was opened to write; its session is stopped;
its record is closed.

Its worktree is never removed.

A card's lane has the same gap — nothing on the board removes a worktree —
but a card's lane ends at a close somebody runs, and the ritual says the
lane is removed there. A corpus lane has no close and no card of its own:
nobody ever looks at it again. So they accumulate, silently, one per split
and one per ruling and one per retry, in `git worktree list` and on the
disk, until somebody notices the directory.

## What would hold it

One way for the board to remove a lane's worktree when its work is in the
trunk, used by the corpus lane and by whatever removes a card lane's
worktree — not a second path for the machine-opened kind. It refuses to
remove anything unmerged, as the ritual says, and it says on the record what
it removed.

## Rejected

Removing the worktree from inside the corpus lane's own session: a session
cannot remove the tree it is standing in, and asking it to try is the wish
this document exists to replace.
