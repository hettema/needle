# A plan is carded and its lane started before the plan is committed

**Kind:** defect
**Fix:** now — the planning brief already states the intent ("the board cards the plan the moment it lands", `board/brief.py`), and every lane brief assumes the lane's worktree carries the plan its card reads; the fix is one gate on the dial's start — the plan's path is in the main checkout's HEAD (or in `origin/develop`) — and it removes the class, not the instance.
**Found by:** the owner's session on 2026-09-05, reading the board's "not level with origin/develop" notice while auto-fix ran on Hello Revenue; card #405 there is the instance.

## Observation

The board reads a project's corpus from the working tree (`api/loops.py`,
`_plan_footprint` and the corpus read around it), so a plan is a document the
beat after the planning session writes it, before `git commit`. The dial
then opens the Start door on the linked card (`api/dial.py::_start`) and the
lane's worktree is branched from the main checkout's HEAD
(`runtime/launch.py::start`, `worktree=request.card`) — a HEAD that does not
yet contain the plan. Nothing between the link and the start checks that the
plan is committed anywhere.

Card #405 on Hello Revenue, 2026-09-05, all UTC:

- 10:56:30 the planning session moves the suggestion to done/ and writes the
  plan; the board links #405 to the plan that beat.
- 10:56:41 the dial takes it; 10:56:49 the lane starts, worktree at
  baff95e29 — no plan, 29 commits behind `origin/develop`.
- 10:58:13 the planning session commits the plan (7952c360e) and pushes. Its
  `**Carried by:**` edit was never staged, so the main checkout stayed dirty.
- The lane, told by its brief that its plan is in the tree, copied the plan
  and the suggestion from the main checkout into its worktree, committed
  them (a second commit of the same plan, which later conflicted on its own
  rebase), and at 11:03 "cleaned up" the main checkout's copies — by then
  tracked files, so the main checkout carried two deletions.
- `runtime/git.py::level` refuses a checkout with tracked changes, so the
  trunk sat 28 behind. Lanes #395 and #399, folded and reviewed, retried
  their close in a loop for an hour, holding their sessions and their memory,
  until the owner's session restored the files by hand.

The cost is not the one lane: it is every folded lane on the project waiting
on a human, silently, behind a notice that names a file and not a cause.

## Rejected

Telling lanes to keep their hands out of the main checkout. The deletion was
the second symptom, not the defect; a lane that starts with its plan in its
tree has no reason to look outside it. A rule remembered by a brief is a
wish, and the gate is one `git cat-file -e HEAD:<plan path>` in the dial.
