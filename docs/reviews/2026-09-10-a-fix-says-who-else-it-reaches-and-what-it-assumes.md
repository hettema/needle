# Review — a fix says who else it reaches and what it assumes, and a colleague checks both before it ships (card #110)

**Plan:** docs/plans/done/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes-and-a-colleague-checks-both-before-it-ships.md
**Reviewer:** the build session (Claude Fable 5.1, card #110's lane) for its own passes; a fresh Codex thread at high effort in a read-only sandbox, reached through `needle call codex --fresh` and `needle wait` — the call this card adds — for every round's cold read, each a row of the board's call table named on its verdict line
**Diff range:** 8033487 (the trunk at the lane's birth, #109's close) .. the close commit that carries this record — the build 07b0372, then one commit per round's repairs, named below
**Findings:** 2 so far — 2 the author's on the first pass, both fixed in 6de3898; the cold reads' verdicts are the lines under each pass
**Stop signal:** open — the loop is running; the line is rewritten at the fold

## What was checked

- The reader, on fixtures and on the three real corpora: `tests/board/test_review_rules.py` (the forms, the fate token, the addresses, the halves, the marks, the verdict lines read apart, the counts) and `tests/board/test_progress.py`; the corpus table over Needle's 35, Hello Revenue's 92 and the machine's 23 records before and after the repair (`/home/dennis/.claude-accounts/hrclaude/jobs/bff81378/tmp/before.tsv`, `after.tsv`, the numbers below), verified by an execution role that opened the campaign record and two records the table said carry no halves.
- The close door, on the floor: `tests/api/test_close_record.py` — a bare fix line refused by line and both halves closing; a record dated on or before the fold closing as before with the old head; an absolute path, a `..` path, an undated name and another card's plan refused; a docs-only lane's record validated; a round without a verdict, a verdict without its row, a reader of the lane's own kind, an answer that never landed and a broken claim unanswered, each refused by name; a lane the board's record places on the second machine read there over the wire; the opening brief's sentence.
- Needle's own records through the same rules: `tests/ratchets/test_every_fix_says_who_else_it_reaches.py`, and the class ratchet now reading dispositions through the one reader.
- The card: the progress line's two counts (`tests/board/test_review_rules.py`), the review block's chased line and verdict rows (`frontend/tests/board.test.tsx`), the fixture regenerated from a record carrying a verdict and a mark; `npx tsc --noEmit` and `vitest run` green.
- The call: `tests/api/test_fresh_call.py` (a fresh thread recorded as a row and landed by `wait`; the other make named; a low effort passed through; the picked line on a bare-name call with the session's effort and sandbox; a tool error reported by `wait`) and `tests/runtime/test_a_call_reaches_a_colleague_fit_to_answer.py` (a row's effort and sandbox from the rollout's `turn_context`; the log's last tool error; the judge's words); then the real thing, twice — the throwaway round below (call 68) and this record's own cold reads (call 69 on).
- The doctrine: the diff of `docs/HOW-WE-WORK.md` is the two sentences the owner ruled at the Plan door and nothing else (read back with `git diff` before the commit); `tests/ratchets/test_every_rule_says_what_holds_it.py` and `tests/ratchets/test_a_doctrine_edit_lands_on_a_card.py` green; the commit names #110.
- The suites: ratchets, board, runtime and infrastructure green on the lane but for the title ratchet, red on the trunk itself since 2026-09-08 over the docs-only-fold suggestion (outside this change, filed by #87's lane); the api suite's run is named at the fold.

## The passes

1. **The author's read of the build, the three lenses in one pass (on 07b0372).** Against the "done means": every item's cases are tests that ran, and the two live reads the plan asked for — a fresh reader breaking a false premise and an omitted reader, and a fresh call answering in the Answer shape — are on the record below verbatim with their rows. The seams: the close checked a record's plan stem before its date, so a Hello Revenue record written today under that project's old template — headed `**Card:**`, no plan line — would have been refused at a close the date rule exempts (1.1); a lane whose worktree is not on this disk is read from the project's checkout, which the fold has levelled, the same shape `lane_files` already has, and stands as a boundary; the fault list the door prints caps at four and counts the rest. The boundaries: `board/review_rules.py` imports only `domain`; the door reaches `runtime.calls` as `api` may; the other make is named through `domain.slot.Make` and not a literal; one reader, and the class ratchet now reads through it. The claims that stand on nothing: the Codex row's effort and sandbox were read from the first 64 KB of a rollout on the strength of one sample, and forty real rollouts measured this morning put the first `turn_context` at 24 KB, 275 KB and 3.1 MB (1.2). Two findings, both inside the change, both fixed in 6de3898.

## Dispositions

### Pass 1's findings

1. [seam] The close checked a record's plan stem before its date, so a Hello Revenue record written today under that project's old template (a `**Card:**` head, no plan line) would be refused at a close the date rule exempts — FIXED in 6de3898; reaches `api/doors.py::_refuse_a_record_that_skipped_the_read` only (the ratchet never checked a stem, and `board/progress.py` matches a record to its card by stem for the face without refusing anything); assumes a record dated on or before 2026-09-10 owes the door nothing but a dated name and a file inside the project's tree, and every other reader of a record's plan stem tolerates a record that names none.
2. [verification] A Codex row's effort and sandbox were read from the first 64 KB of the rollout, and the first `turn_context` sits at 24 KB to 3.1 MB in forty real rollouts, so every row would have said unknown — FIXED in 6de3898; reaches `runtime/codex.py::_context_of` and every caller of `rollouts()` — `sessions()`, `find()`, `warm()`, `fresh_since()` — through `_rollout_of`, plus the fake floor's rollouts (`tests/floor.py::write_rollout`, `tests/fakes/bin/codex`), which now carry a `turn_context`; assumes a rollout is appended to and never rewritten in place, so the first `turn_context` found stands for the file's life, and a scan that found none may resume from where it stopped.

## The throwaway round (item 2), verbatim

A scratch project of one module (`meter.py`: `bill` writes the `billed` flag; `sweep` and `nightly` both read it; `invoice` reads `id` and `amount` and never `billed`) and a note holding two FIXED lines, one whose stated premise is false and one whose reach omits a real second reader the reader is not told about:

```
1. [seam] The sweep re-billed a row on a retry — FIXED in 4d1e2f; reaches the sweep alone; assumes only the sweep reads the billed flag
2. [feature] The invoice printed the amount before the bill was written — FIXED in 5e2f3a; reaches the invoice line only; assumes bill() writes the row's amount before invoice() reads it
```

The call, from the scratch directory (`needle call codex --fresh …/round-one.md --objective "Try to break each FIXED line's reach and its premise against meter.py; answer complete, or broke <line numbers> with what you found."`):

```
call 68: a fresh codex thread 01a08aa2 is working on /home/dennis/.claude-accounts/hrclaude/jobs/bff81378/tmp/scratch-round/round-one.md, effort high, sandbox read-only, in /home/dennis/.claude-accounts/hrclaude/jobs/bff81378/tmp/scratch-round
  the answer lands in /home/dennis/.claude-accounts/hrclaude/jobs/bff81378/tmp/scratch-round/from-codex-fresh-092511-re-round-one.md
  wait for it: needle wait 68
```

`needle wait 68`, 34 seconds after the call:

```
landed: /home/dennis/.claude-accounts/hrclaude/jobs/bff81378/tmp/scratch-round/from-codex-fresh-092511-re-round-one.md landed at 2026-09-10T09:25:45+00:00: broke 1, 2
1. Both halves broke: the reach omits nightly(), which also reads billed at line 21, disproving the premise that only sweep() reads it. bill() writes that flag at line 10.
2. The premise broke: bill() writes only billed and returns the row (lines 10–11); it never writes amount. invoice() reads the caller-supplied amount directly at line 26 without calling bill(). The reach search found no other amount reader in meter.py.
```

The answer file, in the shape asked (`how_known: checked`; `sources`: `round-one.md: FIXED lines 1–2`, `meter.py:8–11 bill()`, `meter.py:14–16 sweep()`, `meter.py:19–21 nightly()`, `meter.py:24–26 invoice()`, `rg search of meter.py for billed, amount, and all four function names`). The row, read from the shared store: id 68, session `01a08aa2-ab01-71c0-b8bb-49d8bc91e7d5`, slot `codex`, called at 09:25:11Z, ended at 09:25:54Z with the verdict's words. So the reader drove the false premise (line 2: `bill()` never writes `amount`) and found the omitted reader (line 1: `nightly()`), named by function and line, with the reach search it ran.

## The corpus table (item 1)

The reader run over the three corpora before and after its repair, 150 records: the pass count differed on one record, Hello Revenue's campaign record of 2026-09-08 (157 before, 22 after; the execution role counted 22 margin entries between lines 169 and 411 by hand); 1,958 FIXED lines by the word, 0 carrying both `reaches` and `assumes`. The fate token moved 55 dispositions on the first reading — 30 an all-caps `FILED`, 3 a token after a semicolon, 1 after a closing quote, which the pattern now takes — and 26 after the repair, all in records dated on or before the fold and all of one shape: a fixed finding whose line goes on to a sibling's `NO CHANGE` or `filed`, which the last-token rule reads as the sibling's; the README now says one finding, one line. Three records name no token a clause opens with (`(FIXED with 22)`, "PARTLY FIXED, PARTLY FILED", "first answered NO CHANGE (…), then FIXED") and read as no fate, where the old reader read the first word it found.

## The baseline reading of Hello Revenue #456 (item 3)

The plan's Loop carries the counts — 82 escaped, 37 caught, by the record's own words — and the rule that counted them. The reading itself, every finding with its section, its line, the repair it blames and its verbatim quote, made by a search role over the record's 541 lines on 2026-09-10, follows so the number has a source someone can re-read.

