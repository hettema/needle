# Review records

The review workflow has one source: `docs/HOW-WE-WORK.md` §13. This file
defines its record, not another review procedure. The owner restored the
finite review-and-fix workflow on 2026-09-11 (Needle #131).

One file per software change: `YYYY-MM-DD-<topic>.md`. Write it before
integration and keep it in this folder. Historical records and their old
pass/verdict formats remain evidence; do not rewrite them for today's form.

```markdown
# Review — <topic>

**Plan:** docs/plans/done/<plan>.md
**Reviewer:** <independent reader and how the review was obtained>
**Diff range:** <base>..<revision independently reviewed>
**Findings:** <total findings, including rejected and filed findings; zero when none>
**Verification:** <checks of the repairs and final revision, results and limits>
**Completion:** <why the reviewed findings are resolved, or what remains open>

## Dispositions

1. [feature] <file:line, violated promise and consequence> — FIXED in <sha>;
   <repair, affected dependencies and verification>
2. [seam] <allegation> — NO CHANGE: <evidence disproving it>
3. [boundary] <outside-scope finding> — filed as <suggestion path>

## Verification evidence

<Commands or probes actually run, results, final revision and any limits.>
```

A review with no findings names the reader, revision and checks and says
zero findings. A first clean independent review is sufficient. After repairs,
record the final revision and their verification without implying the first
review read later edits. An additional review, when needed, records its
specific reason and actual scope under the same shared rule.

Use the existing finding classes: feature, seam, boundary, verification,
record. The parser also reads historical pass sections.
Every verified in-scope finding is resolved. Every rejection gives evidence;
every filed finding names its destination. Record corrections do not require
a new code review. Cold-read call rows, `reaches`/`assumes` clauses, numbered
rounds and repeated completeness verdicts are no longer mandatory.

The close checks a nonempty Reviewer and verification evidence (a Verification
head or recognised evidence section; historical What was checked and Tests
sections remain accepted). It retains path, date and applicable plan-identity
checks. This checks that evidence was recorded, not that a written claim is
true or that the named reader was independent. Actual independent review and
verification remain the implementing colleague's responsibility.
