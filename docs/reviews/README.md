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

**Every finding says its class**, from 2026-09-06 (card #60): a disposition
line begins with one of `[feature]` (the work against its plan's "done means"),
`[seam]` (concurrency, failure and restart, the truth of what the board shows),
`[boundary]` (a rule this project's `CLAUDE.md` names), `[verification]` (a
claim with no source, a hedge shipped as a fact, a primitive built beside an
existing one — the class `docs/HOW-WE-WORK.md` §8 exists to end) or `[record]`
(the plan, the review or the commit text itself). Why: the doctrine's
verification rules were rewritten on that card as a thesis, and the thesis is
read from the count of `[verification]` findings per carded close — a count
nothing could make before the line carried its class.
`tests/ratchets/test_every_finding_says_its_class.py` refuses a record dated on
or after that day with an unclassed finding.

```markdown
1. [verification] <finding> — FIXED in <sha>
```
