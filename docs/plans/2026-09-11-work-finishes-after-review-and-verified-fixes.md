# Work finishes after review and verified fixes

**Status:** NEW — owner authorised implementation in conversation on 2026-09-11.
**Written:** 2026-09-11, Dennis: "go into the relevant files and just make this way of working clear again"; "fix all findings"; "make sure there are no contradictions". Adopted sequence: code, independent review, fix all verified findings within scope, verify repairs, done; no mandatory recursive cold reads.
**Effort gate:** high — shared instructions and the close validator must agree across projects and machines without rewriting historical evidence.
**Sequencing:** none; preserve concurrent #123/#124 and #130 work.

## Intent

Work finishes when independent review's verified findings are fixed and the repairs are checked, without an automatic new review cycle. One shared rule governs every project's instructions and the board's close.

## Terrain and search

Read docs/research/2026-09-11-review-fix-loop-diagnosis.md. Existing sources: HOW-WE-WORK §13, HOW-WE-HOLD-IT §13; CLAUDE.md and project AGENTS links; board/brief.py::completeness_read; board/review_rules.py and api/doors.py's close; docs/reviews/README.md; HR hr-feature-review and other live skills. Search active project and user entrypoints, excluding historical records, frozen experiments and archived plans. #117 proposes structured recursive verdicts; #130 concerns remote call rows. Neither justifies preserving a recursive requirement after this owner's ruling. No new review platform or UI change.

## Items

### 1. One shared rule, consistent active instructions
Replace §13's method with the owner's finite workflow; keep scope, independent judgment, truthful records and meaningful repair verification. Project instructions point to it. Done means: canonical active instructions on registered projects and both machines contain no contrary automatic-loop requirement; historical and experimental records retain their original wording as history.
Hands out: search — inventory instructions and links; verifies the reported files and a final contradiction search.

### 2. The board accepts the adopted workflow
Align the opening brief, review record shape and close validator; retain record existence, ownership and meaningful evidence, and allow verified no-change/outside-scope dispositions. Done means: a single independent review plus repairs and verification can close without per-repair cold call rows; missing review evidence is refused; existing records remain readable.

### 3. Verify, review and distribute
Run applicable suites, one independent review, repair its verified findings and verify repairs. Integrate without overwriting other lanes; update active canonical copies and report any running-session delivery limitation. Done means: the current code and instructions agree on both machines, with a record of the inspected projects, tests and any unresolved delivery limits.

## Acceptance

A first clean independent review can finish; a reviewed change with checked repairs can finish; another review is justified by changed behaviour or unresolved risk, never automatic. A disproved allegation does not compel a code change. Existing verified defects cannot be silently waived. No archived review or frozen experiment is rewritten to claim compliance with today's rule.

## Rulings

The owner's September 11 instruction supersedes mandatory repeated passes and cold reads of every repair. "Fix all findings" means every verified in-scope finding, with evidence-backed rejection and separate filing available; it does not mean accepting every allegation. Preserve Kanban and unrelated harnesses. Additional review remains an execution judgment with a concrete reason.

## Loop

Loop: the adopted workflow and its refusal cases pass the targeted checks — verified — close-path fixtures and the active-instruction inventory in this change's review record
