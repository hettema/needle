# Review records

One file per code-shipping slice, written before the fold: what was checked,
what was found, and what happened to each finding. A slice is not done without
one (`CLAUDE.md`). The record proves the review ran; a review with zero
findings is still a record.

## The shape

Filename: `YYYY-MM-DD-<slice topic>.md`.

```markdown
# Review — <topic>

**Plan:** docs/plans/done/<plan>.md
**Reviewer:** <who ran it, and on what model>
**Diff range:** <merge-base>..<head reviewed>
**Findings:** <count>

## What was checked
- <each surface, and how — a test family, a run against real data, a screenshot, a driven browser>

## Dispositions
1. <finding> — FIXED in <sha>
2. <finding> — NO CHANGE: <why, verified>

## What the build learned the comp got wrong
## Not done, stated
```

Rules: every finding gets a disposition and there is no "defer"; new scope
goes to a plan or a suggestion and the disposition names it. The diff range is
the real one — a range that predates later commits is a record of a review
that did not cover them. Records never archive.
