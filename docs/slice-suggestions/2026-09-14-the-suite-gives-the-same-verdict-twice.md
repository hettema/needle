# The suite gives the same verdict twice

**Kind:** defect
**Fix:** now — "a lane folds when its suite is green; nothing lands red" is
written in CLAUDE.md and in the doctrine's §12, and a suite whose failures
change between runs cannot hold it; the fix is inside Needle's own test
floor, and it removes the class — every future lane reading a red it did not
cause — rather than tonight's three tests.
**Found by:** the lane on card #138, 2026-09-13, when a full-suite failure
could not be attributed to the change that ran it

## The intent it breaks

Every lane folds on one question: is the suite green. Tonight the same suite,
on the same two commits, answered it four different ways. A lane that reads
red cannot tell whether it broke something, so it either holds work that is
fine or folds over a failure that is real — and the only way to find out is
to re-run the suite, which costs half an hour and answers differently again.

## The evidence

Five runs, two commits: `33e3140` (`origin/develop`, before #138) and
`6efa8db` (#138's lane, one commit on top of it, four lines in
`api/dial.py`).

| run | commit | scope | failed |
|---|---|---|---|
| A | 6efa8db | whole suite | `close_record::…second_machine…`, `defects_column::…shows_its_word` |
| B | 33e3140 | those two tests alone | `defects_column::…shows_its_word` |
| C | 6efa8db | `close_record::…second_machine…` alone | none |
| D | 33e3140 | `tests/api` | `defects_column::…shows_its_word`, `doors::…citing_suggestions…` |
| E | 33e3140 | whole suite | `defects_column::…shows_its_word`, `defects_column::…read_again_before_it_is_taken`, `doors::…citing_suggestions…` |

Read down the column: one test fails in all five (a real defect, filed
separately as the graded defect's face). Three others each fail in some runs
and pass in others, and no two runs agree on the set. `close_record` failed
only with the whole suite around it and passes alone on the same commit;
`doors` failed twice on the base and never on the lane; the second
`defects_column` test failed only in run E.

What this cost, concretely: proving that #138's one change did not cause
run A's failure took four extra suite runs, roughly ninety minutes, and the
proof is still only an argument from the table above rather than a fact the
suite states.

## What would hold it

The mechanism is not established and that is the first job. Two candidates,
both testable cheaply:

- **Order.** `pytest -p no:randomly` is not in use, so the order is stable
  per scope but changes when the scope does — which is exactly the pattern
  above (alone / `tests/api` / whole suite). If state leaks between tests —
  a shared floor root under `~/.cache/needle/floors`, a registry, a served
  board — then the scope decides the verdict. `pytest --lf`, or re-running
  run A's exact scope, would say.
- **Timing.** The floor uses real sleeps and real subprocesses, and these
  runs shared a laptop with three lanes' suites on the rented machine. A
  test that waits a fixed interval for a launch fails under load and passes
  idle. The runs above do not record the load, which is itself the gap.

Whichever it is, what has to end is a lane reading a verdict it cannot trust.
The ratchet to aim for: the same commit, run twice in the same scope, fails
the same tests — and when it does not, the suite says which tests are
unstable rather than leaving a lane to find out.

## Live neighbours on this ground

Searched `docs/slice-suggestions/` (live and `done/`) for flaky, order,
non-deterministic and "the same suite": nothing carries it. The nearest is
card #109 (`2026-09-10-a-test-run-never-takes-the-memory-the-work-needs.md`,
shipped), which caps what a test run may take from the machine — the load
that a timing-dependent test would feel, but not the verdict it returns.
