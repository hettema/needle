# A finished card's lane is gone from the disk once its work is folded

**Kind:** defect
**Fix:** now — the intent is written (HOW-WE-WORK §14, the close ritual: "the lane is removed, with the tools that refuse to delete anything unmerged"), the fix is inside the close and the beat, and it removes the class — twelve folded lanes on Needle's own disk and every future one — rather than deleting twelve directories by hand
**Found by:** the owner's session in Needle on 2026-09-07, counting worktrees while reading the boards for half-done work: thirteen under Needle's `.claude/worktrees/`, twelve of them for cards in Done or Executed whose branch is level with the trunk and whose tree is clean (#26, #27, #34, #36, #38, #50, #51, #54, #57, #59, #60, #73); the thirteenth is #20, running. Omarchy's disk holds the same pattern for #7, #12, #14, #16, #35 and Hello Revenue's for its Done cards.

## Observation

- The close ritual names five steps in order and the last is the lane's removal. The first four leave a trace the board reads (the archived plan, the level trunk, the closed card, the review record); the fifth leaves none, and it is the one that did not happen for any of the twelve.
- Each of the twelve is safe to remove: `git rev-list --count origin/develop..HEAD` is zero and `git status --short` is empty for every one. Nothing unmerged is at risk; the ritual's tool would have refused otherwise.
- The cost is not memory. It is disk (each worktree carries a full checkout and, for Needle, a `frontend/node_modules`), and it is the board's word: the close reads as complete when a step it names was skipped, and a session that later lists worktrees to find half-done work — as this one did — reads twelve finished cards as candidates before checking each by hand.

## The intent it breaks

HOW-WE-WORK §14: every finished piece of work is closed the same way, and a close that was interrupted never reads as done. A step that leaves no trace is a step that can be skipped silently (§5), and this one was, twelve times.

## What would fix it

1. The close removes the lane's worktree and branch as its last act, with `git worktree remove` and a branch delete that refuse anything unmerged or dirty, and writes one line on the card saying the lane is gone; a refusal is written on the card too and the close still completes, since a lane with unmerged work is evidence, not garbage.
2. The beat counts lanes on disk whose card is in Done or Executed with a level, clean tree, and the head shows the count beside the shipped-with-no-review count, so a skipped removal is loud where the owner looks.
3. The first run of the beat removes the twelve on Needle's disk and their kin on the other boards' disks by the same rule, with the same refusal.
