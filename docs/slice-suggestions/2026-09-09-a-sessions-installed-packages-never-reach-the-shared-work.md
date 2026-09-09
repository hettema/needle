# A session's installed packages never reach the shared work

**Kind:** defect
**Fix:** now — the intent is written (`frontend/.gitignore` line 6 ignores `node_modules/`, and CLAUDE.md's "the board reads what runs; it never is the thing that runs" — a checkout's installed packages are the machine's, not the work's); the fix stays inside the door the close uses to stage its files (`git add -A` in the close) or the ignore rule itself (`node_modules` without the trailing slash also matches a link), and it removes the class — any link or file a session lays under an ignored name — not this one link.
**Found by:** the lane on card #68 (docs/plans/2026-09-05-work-the-laptop-interrupted-comes-back-by-itself-and-the-board-says-truly-how-it-ended.md), in the review's boundary pass, when the type check would not run

## The intent it breaks

The shared work carries the code and the documents, never what a session installed to run them; every colleague installs its own packages in its own copy. On 2026-09-09 card #99's close committed `frontend/node_modules` to the trunk as a symbolic link to the main checkout's packages (commit 89ff839), because the ignore rule names a directory and a link is a file; when the main checkout followed the trunk, its own packages became a link to itself, and from 12:13 no session could type-check the page or build the board's dist from there — every lane's `tsc` and `vitest` died without a word, and the served board could not be rebuilt. While this holds, the owner loses the page's rebuild after every fold, and every lane loses a check it cannot see fail.

## Evidence

- `git show 89ff839 --stat` → `frontend/node_modules | 1 +`; `git ls-tree origin/develop frontend/` → `120000 blob … frontend/node_modules`, a link.
- `frontend/.gitignore:6` → `node_modules/`; git's pattern with a trailing slash matches only a directory.
- `stat /home/dennis/Work/needle/frontend/node_modules` → `symbolic link … -> /home/dennis/Work/needle/frontend/node_modules`; `./node_modules/.bin/tsc` → *Too many levels of symbolic links*; `npx tsc` exit 216 with no output.
- Card #68's lane removed the link from the tree in its second-pass commit and reinstalled its own packages; the main checkout's link was replaced by a real install at the fold, and both are said on the watercooler.

## What would fix it

The ignore rule loses its slash (`node_modules`, matching a directory and a link alike) and a ratchet under `tests/ratchets/` refuses any tracked path named `node_modules`, `dist` or `.venv` — the names a session installs under — so the close's `git add -A` can never stage one again, whichever lane lays it and whatever shape it has.
