# A colleague reading a card's code is not mistaken for the session building it

**Kind:** defect
**Fix:** now — the intent is written (`docs/INTENT.md`: the board shows what runs, truly; plan 57's ruling that a Codex worker is a row of the same list, read from its rollouts and checked in /proc; HOW-WE-WORK §11, a red word is a machine fact with named evidence); the fix stays inside the seam that names a card's session from the sessions whose directory is its lane (`board/lane.py::lane_for`, the winner among rows in the worktree), and it removes the class — every reader of either make that is run inside a lane's copy of the code, a review pass or a search, and not this one card.
**Found by:** the owner, 2026-09-09 16:26, from Needle's board: card #107 read "session died — the session on it ended 2 min ago with nothing landed … the cause is not established", with a Resume door that failed ("01a0868c is a Codex session: it runs on no subscription slot and has no wall to move away from"), while the lane's own session (hrme 89b15944, interactive) was building it

## The intent it breaks

A card's red word names something wrong with the work on that card. On 2026-09-09 the building session ran a Codex review pass with `--cd` set to the lane's worktree, as the review ritual asks (a reader who was not the author). The board read the Codex rollout as a session of the lane — its directory was the worktree — and when the pass ended a minute later, the card turned red with "session died" and offered a Resume that cannot work on a Codex row. The owner read a lane in trouble; nothing was wrong, and the building session was alive in the same directory the whole time.

## Evidence

- `needle sessions` at 16:20: `codex 01a0868c ended background codex-01a0868c /home/dennis/Work/needle/.claude/worktrees/card-107-…` beside `hrme 89b15944 working interactive` — two rows in one directory, and the ended Codex row was the one the card spoke for.
- The face: "session died", `Meaning.BROKEN`; the sentence "the process disappeared after its last activity at 2026-09-09 14:24Z; the cause is not established"; the Resume door's refusal text names plan 57.
- The five Codex rows the same board listed at 15:24 for Hello Revenue #456's lane (`codex 01a0864c … /home/dennis/.claude-accounts/gmail/jobs/9a7c49a7/tmp/head-snapshot`), every one a reader that lane had called, all "ended".

## What would fix it

Among the sessions in a lane's directory, a live session of the building kind outranks an ended reader: the winner is the live row when one stands, and a Codex worker or a `claude -p` reader that ended while another session of the lane is alive is not the lane's death. When only readers are left, the face says a reader ended, in the reader's own words, and offers no Resume for a row the runtime cannot resume. A test on the floor: a lane with a live interactive session and an ended Codex rollout in the same worktree reads as working, never as died.
