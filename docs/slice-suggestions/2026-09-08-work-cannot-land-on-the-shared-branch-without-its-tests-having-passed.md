# Work cannot land on the shared branch without its tests having passed

**Kind:** defect
**Fix:** now — CLAUDE.md states the bar ("the fold is a fast-forward push to `origin/develop` when the suite is green"; "nothing lands red"), the fix is inside the one verb that lands work, and it removes the class rather than one lane's slip.
**Found by:** the lane on card #63 (docs/plans/done/2026-09-05-the-strongest-model-with-room-to-run-drives-the-card-claude-or-codex.md), in the review's feature pass

## The intent it breaks

Everyone builds on the shared work, so what lands there is supposed to have
passed its tests — but nothing checks. Landing finished work runs a
fast-forward push and nothing else: whether the tests passed is something
each session is trusted to have done, and a session that skipped it, ran
only part of the suite, or ran it before its last change lands red work that
everyone else then builds on. It has happened: on 2026-09-07 the shared
branch was red for every session because a document came in from the main
copy of the code without a session and no tests ran.

## The evidence

`runtime/git.py::fold` reads the worktree for uncommitted work, pushes
`HEAD:develop`, fetches and proves the remote equals HEAD. It never runs a
test. `CLAUDE.md` says the fold happens "when the suite is green" and
"nothing ships half-done"; the only thing holding that today is each
session's own discipline, which is the convention §5 calls the weakest
defence — the failure is silent and arrives on somebody else's next rebase.

Card #63 met this from the other side: its plan said the fold would run the
suite for a session of another kind, because that session could not run one
itself. It turned out it can (`docs/reviews/2026-09-08-the-strongest-model-with-room-to-run-drives-the-card.md`),
so the card left the fold alone rather than growing a second shape of fold
for one make. The general fix is one shape for every session: the fold runs
the project's suite before it pushes, and a red suite leaves the branch
unpushed with the failing tests named on the card. The cost is real — a full
suite run per landing — so the fix names what it runs and how a session that
has just run it green avoids running it twice.

Also on 2026-09-07, `docs/slice-suggestions/2026-09-07-a-suggestion-that-quotes-real-card-titles-is-refused-before-it-reaches-the-public-trunk.md`
filed the same day's incident from its own angle: that one is about what a
document may contain, this one about nothing landing untested at all.
