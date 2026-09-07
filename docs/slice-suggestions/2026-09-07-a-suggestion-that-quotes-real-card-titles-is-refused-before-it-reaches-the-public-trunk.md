# A suggestion that quotes real card titles is refused before it reaches the public trunk

**Kind:** defect
**Fix:** now — the intent is written (`tests/ratchets/test_the_fixture_project_is_synthetic.py` and CLAUDE.md's boundary that a real project's titles never enter this public repository), the fix stays inside its ring (arm the same check in `hooks/commit-msg`, already on every checkout through `core.hooksPath`, so a docs commit from the main checkout is refused the way a lane's suite refuses it), and it removes the class — a commit path that never runs the suite — not the instance, which the owner's session redacted in `20f6a33` an hour after it landed.
**Found by:** the lane on card #20 (docs/plans/done/2026-09-04-08-identity-and-the-record.md), in the review's boundaries pass, running the full suite after rebasing onto `origin/develop` at 379b6ce

## Observation

`docs/slice-suggestions/done/2026-09-07-a-decision-parked-on-the-owner-is-read-twice-and-leaves-his-column-when-the-record-already-answers-it.md`, line 14, quotes five card titles from Hello Revenue's board verbatim to show the classes of parked decisions. Commit `379b6ce` landed it on `develop` from the main checkout on 2026-09-07 without a lane, so no suite ran before it reached the public trunk, and `tests/ratchets/test_the_fixture_project_is_synthetic.py::test_no_real_card_title_is_in_the_tracked_tree` is red on `develop` for every lane that rebases. This lane's own files are green; its fold does not touch that file.

This is the second instance of the class `docs/slice-suggestions/2026-09-04-real-card-titles-reached-the-public-repository-through-the-design-comps.md` filed on 2026-09-04 (the design comps, commit `16a8023`), still open. The two share one cause: the ratchet runs in a lane's suite, and a docs commit made straight on the trunk runs no suite.

## What would hold it

- The five titles described, not quoted, in the one file — done in `20f6a33` (2026-09-07), which is why this suggestion is about the class alone.
- `hooks/commit-msg` — already armed on every checkout and worktree through `core.hooksPath` (card #54) — runs the synthetic-title check over the files a commit touches under `docs/`, so the refusal happens at the commit, on the main checkout too, not a suite later.
