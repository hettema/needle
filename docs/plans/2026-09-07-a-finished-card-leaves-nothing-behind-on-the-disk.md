# A finished card leaves nothing behind on the disk

**Carries:** docs/slice-suggestions/done/2026-09-07-a-finished-cards-lane-is-gone-from-the-disk-once-its-work-is-folded.md
**Status:** NEW — planned, not started; placed in Up next by the owner on 2026-09-07, after the cards that stop the machine crashing and make the board readable.
**Written:** 2026-09-07, from Dennis after twelve folded, clean lanes were found on Needle's disk for cards long since Done: "Let's make sure we make cleaning up after done a mechanical rule. Let's keep a nice and tidy house."
**Effort gate:** medium — the mechanics are one step added to the close and one count on the beat, both beside code that exists (`api/doors.py` close, `board/dial.py` counts); the judgment is the refusal rule, settled here: a lane with unmerged commits or a dirty tree is evidence and is never deleted by this plan.
**Sequencing:** none. Shares `api/doors.py` with whichever lane is on the close; the fold settles it.
**Class:** the beat counts folded, clean lanes still on any project's disk and the head shows the count; a close that skipped the removal is loud where the owner looks, and the loop below reads the count daily.

## Intent

The close ritual (HOW-WE-WORK §14) ends with the lane's removal, "with the
tools that refuse to delete anything unmerged". Every other step of the
ritual leaves a trace the board reads; this one leaves none, so it was
skipped silently for every card closed on this board: twelve worktrees for
Done and Executed cards on Needle's disk, each level with the trunk and
clean, and their kin on the Omarchy and Hello Revenue disks. The cost is
disk, and the board's word: a close read as complete when a named step did
not happen, and a session hunting for half-done work reads twelve finished
cards as candidates. After this plan a finished card's lane is gone the
moment its close lands, a lane that cannot be safely removed is named on
the card instead, and a leftover is counted on the head until it is gone.

What does not change: a lane with unmerged commits or uncommitted files is
never removed by the board. That lane is the half-done work #68 resumes,
and deleting it would be the doctrine's own failure.

## Items

### 1. The close removes the lane as its last act, and says so on the card
The close (`api/doors.py`, the close door; `runtime/` holds the worktree
and branch operations) ends by removing the lane's worktree and deleting
its branch with the git operations that refuse an unmerged branch or a
dirty tree, then writes one line on the card that the lane is gone. When
the removal is refused, the close still completes — the card is closed on
its record, not on its disk — and the refusal is written on the card with
what git found, so a lane kept is a lane named.
Done means: on the fixture, a close on a folded lane leaves no worktree and
no branch and the card carries the line; a close on a lane with one
unfolded commit leaves both, completes, and the card names the commit; the
close never runs a delete that could lose a commit (the operation used is
the refusing one, held by a test that plants an unmerged commit).

### 2. The beat counts what a close left behind, and the head shows it
On every beat the board lists the lanes on each registered project's disk
whose card is in Done or Executed and whose tree is level with the trunk
and clean, and the head shows the count beside the count of shipped cards
without a review record, in the same quiet form; `needle lanes` prints the
list with the reason each is still there.
Done means: with the twelve on Needle's disk the head reads their count;
after item 3 it reads none and the row is absent; a lane kept by refusal in
item 1 is not counted here — it shows on its card.
Hands out: search — the lanes on disk per project with card, column,
commits ahead of the trunk and dirty-file count; verifies the counts
against `git rev-list` and `git status` on two of them before the numbers
are used.

### 3. The first run clears the backlog on every board's disk
The rule of item 1 runs once over the leftovers item 2 lists — the twelve
on Needle's disk, the six on Omarchy's, Hello Revenue's Done lanes — with
the same refusing operations and the same line on each card. The eight
Hello Revenue lanes in Planned with unfolded commits are not touched: their
cards are not Done, and #68 owns them.
Done means: `needle lanes` lists none on any board after the run; every
card whose lane was removed carries the line; the review record names any
lane the run refused and why.

## Acceptance criteria

- A card closed after this plan has no worktree and no branch a minute
  after its close, or its card says why the lane was kept.
- No folded, clean lane older than a day is on any registered project's
  disk, and the head says so by showing no count.
- No commit was lost: every branch deleted was level with the trunk, held
  by the refusing operation and its test.

## Rulings

- **Refuse, never force.** Rejected: a forced removal for lanes of cards in
  Done, on the reasoning that Done means folded. Done is the board's word
  and the disk is the evidence; where they disagree the disk wins and the
  card says so. The refusing operation costs nothing and the alternative
  costs a commit.
- **The close does it, not a sweeper.** Rejected: a nightly sweep alone.
  The ritual names the close as the actor, and a step done by a sweeper is
  a step the close can still skip; the beat's count is the check on the
  close, not its replacement.

## Deliberately not

- Lanes of cards in Planned, Up next or Executing, whatever their state:
  #68's ground.
- The rescue horizon and what a dead lane's session leaves in the runtime's
  ledger: untouched.

## Loop

We think a removal at the close, held by a daily count, will keep every
project's disk free of finished lanes, because the step was skipped only
for want of a trace. If the count is ever above zero a day after a close,
that close is the finding: the removal did not run or was refused without
the card saying so, and item 1's refusal path is what changes.

Loop: no folded, clean lane is left on any project's disk a day after its close — command uv --project /home/dennis/Work/needle run needle lanes --left-behind --count expect 0 by 2026-09-21 every 1d
