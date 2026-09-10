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
**Stop signal:** <which rule of HOW-WE-WORK §13 ended the loop, and the pass of the last live or latent-behaviour finding>

## What was checked
- <each surface, and how — a test family, a run against real data, a screenshot, a driven browser>

## The passes

1. **<the lens, e.g. the work against its "done means">.** <what it found, in the record's words; "nothing new" or "clean" when it found nothing>
Read cold by <who, with its session id> on <sha>, call <n>: complete
2. **<the next lens>.** <what it found>
Read cold by <who> on <sha>, call <n>: broke 1.2, 1.3 — <the reader's words: the sibling or reader the line left out, what driving the premise showed>

## Dispositions

### Pass 1's findings

1. [<class>] <finding> — FIXED in <sha>; reaches <who else the fix reaches: the sibling cases, the other readers of the surface>; assumes <what it assumes about who else reads or writes the thing, and in what order>
2. [<class>] <finding> — NO CHANGE: <why, verified>
3. [<class>] <finding> — filed as docs/slice-suggestions/<file>.md

### Pass 2's findings

1. [<class>] [repair of 1.2] <a finding an earlier round's repair caused, naming that repair's address> — FIXED in <sha>; reaches <…>; assumes <…>

## What the build learned the comp got wrong
## Not done, stated
```

Rules: every finding gets a disposition and there is no "defer"; new scope
goes to a plan or a suggestion and the disposition names it. The diff range is
the real one — a range that predates later commits is a record of a review
that did not cover them. Records never archive. One finding, one line: a
finding's fate is the token that opens the last clause of its line — `FIXED`,
`NO CHANGE`, `filed` — so a sibling's fate written onto the same line ("…
FIXED; the twin is filed as …") is read as the sibling's, and a sibling gets a
line of its own.

**A fix says who else it reaches and what it assumes, a cold reader tries to
break both before the round ships, and a finding a repair caused says so**,
from 2026-09-11 (card #110; the three forms above, read by
`board/parse.py::review_of` for the close door, the card and the loop alike):

- A `FIXED` line ends `FIXED in <sha>; reaches <…>; assumes <…>`. *Reaches*
  is who else the fix touches — the sibling cases it covers, the other readers
  of the surface it changed. *Assumes* is the premise it stands on — who else
  reads or writes the thing, and in what order. Free words; both halves,
  always, since a fix scoped by the finding alone and standing on its author's
  premise is what the next pass finds, an hour later (Hello Revenue #456:
  thirteen of thirty-four passes found a defect an earlier round's own repair
  had made).
- Dispositions sit under `### Pass N's findings`, numbered from 1 within each
  pass, so a finding's *address* is `<pass>.<number>` and a verdict or a
  repair mark can name it.
- Every round of repairs — a pass and the fixes it caused — is read cold by a
  colleague of the other make through `needle call codex --fresh <note>` and
  `needle wait <n>`, handed the round's FIXED lines with one job per line:
  re-run the search behind the reach and name a sibling or a reader the line
  left out; drive the premise and say what it saw. Its verdict goes on a line
  of its own under the pass, `Read cold by <who> on <sha>, call <n>: complete`
  or `…: broke <address>, <address> — <its words>`. The close checks the row:
  the call exists, its colleague is of the other make, its answer landed after
  the call. A verdict is read apart from the pass's text, so it never makes a
  pass read clean.
- Every address a reader broke gets a disposition after it, marked
  `[repair of <address>]` after the class: a fix with its own reach and
  premise, or a record-only correction (`— CORRECTED in the record`), which
  §13 lets the writer make and re-read alone.
- A finding a full pass makes whose cause is an earlier round's repair carries
  the same mark. The board counts the marks at two stages — *caught*, when a
  verdict broke the address before the round shipped; *escaped*, when only a
  pass's line carries it — which is the number the card's loop reads.

The close refuses a record dated on or after that day that skips any of it,
in any project on the board (`api/doors.py::close`); records dated before are
history. `tests/ratchets/test_every_fix_says_who_else_it_reaches.py` holds
Needle's own records through the same rules.

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
