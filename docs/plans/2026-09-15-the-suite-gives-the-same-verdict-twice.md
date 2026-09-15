# The suite gives the same verdict twice

**Status:** PENDING
**Carries:** docs/slice-suggestions/2026-09-14-the-suite-gives-the-same-verdict-twice.md
**Written:** 2026-09-15, at the owner's word after a second one-line change cost more to prove innocent than it cost to write.
**Effort gate:** high — the edit may turn out to be small, but nothing about it is known yet: the cause is unestablished, the suspects are a shared floor root, a served board, real sleeps and real subprocesses, and the thing being fixed is the one gate every lane folds on, so a wrong diagnosis leaves the gate looking fixed and still lying.
**Sequencing:** none holds this, and nothing should wait for it — every lane folding today is already paying for it.
**Class:** `uv --project /home/dennis/Work/needle run needle fixes all --unstable-tests --count` counts the tests that answered differently across the run pair the check itself makes. Zero is the class closed.

## Intent

Today the same code, checked twice, gives two different answers, so nobody can
trust the one check that stands between a broken change and a client.

It costs twice over. A session that meets a failure spends half an hour or
more proving the failure is not its own — that has happened twice this week,
both times on a one-line change. And in the other direction, a break that
shows up one run in three is waved through by the run where it hid, so work
that passed its check may never have been safe.

After this plan, the same code checked twice gives the same answer; and where
a test genuinely cannot be held still, the check names that test instead of
leaving the next session to discover it.

## The evidence this starts from

Six runs over three commits, gathered 2026-09-13 and 2026-09-15.

| run | commit | scope | failed |
|---|---|---|---|
| A | 6efa8db | whole suite | `close_record::…second_machine`, `defects_column::…shows_its_word` |
| B | 33e3140 | two tests alone | `defects_column::…shows_its_word` |
| C | 6efa8db | `close_record::…second_machine` alone | none |
| D | 33e3140 | `tests/api` | `defects_column::…shows_its_word`, `doors::…citing_suggestions` |
| E | 33e3140 | whole suite | `defects_column::…shows_its_word` ×2 variants, `doors::…citing_suggestions` |
| F | b2f9c9c | `tests/api` | `defects_column::…shows_its_word` |

No two runs of the same scope agree on the set. `close_record::…second_machine`
failed only with the whole suite around it and passes alone on the same
commit. `defects_column::…shows_its_word` was deterministic on 2026-09-13,
passes alone on 2026-09-15 after card #138's fuse landed in that file, and
still fails inside `tests/api` the same afternoon — so at least one test has
moved from broken to unstable, which is the harder failure and reads as
fixed.

## What was searched before naming anything new

`pytest-randomly` is not installed and no `-p randomly` appears anywhere, so
the order is stable per scope and changes when the scope does — which is the
pattern above. `tests/floor.py` builds every floor under
`~/.cache/needle/floors/pytest-of-dennis/pytest-<n>/`, a shared root whose
per-run directory is pytest's, not the test's. `tests/fakes/bin/ssh` stands in
for the wire, so no test reaches a real machine. Card #109
(`done/2026-09-10-a-test-run-never-takes-the-memory-the-work-needs.md`) caps
what one run may take from the machine and is the reason a run survives at
all; it says nothing about whether two runs agree. No live suggestion or plan
in this repository names flakiness, ordering, or a test that answers twice —
searched over both words and the concept across `docs/plans/`,
`docs/plans/done/` and `docs/slice-suggestions/`.

## Terrain — where to look, not what to write

`tests/floor.py` is the floor every one of these tests stands on: its root,
what it shares between tests and what it tears down. `tests/api/test_doors.py`
holds the `client`, `repo` and `quick` fixtures the failing tests import, and
`tests/api/test_dial.py` holds the beat helpers (`tick`, `acts`, `last_act`)
that count what a beat opened. The three tests that have moved are
`tests/api/test_defects_column.py`, `tests/api/test_close_record.py` and
`tests/api/test_doors.py`. Time and subprocesses are the two suspects with
teeth: `infrastructure/clock.py` and the floor's real `sleep`s for the first,
`tests/fakes/bin/ssh` and the launch fakes for the second. `pyproject.toml`
holds the suite's configuration and is where a plugin or a marker would go.

## Items

### 1. The cause is established before anything is changed
Run the same scope twice on one commit, with the order recorded, and say which
of the three it is: state left between tests, order changing with scope, or
time and load. Name it with evidence, not a guess.

Done means: a written finding in the review record that names the mechanism
and shows the run pair that proves it — the same test, the same commit, two
verdicts, and the difference between the two runs identified.

Hands out: execution — runs the same scope twice on one commit and reports both verdicts verbatim, then runs the identified test alone and under `-p no:cacheprovider` with the order printed; verifies re-running each disagreement once more before it is reported as a disagreement.

### 2. The cause is removed for the three tests that have shown it
Whatever item 1 names, the three tests that have answered differently answer
the same way twice.

Done means: `tests/api/test_defects_column.py::test_a_defects_reading_without_a_grade_is_refused_and_a_graded_one_shows_its_word`, `tests/api/test_close_record.py::test_a_lane_on_the_second_machine_has_its_record_read_there` and `tests/api/test_doors.py::test_a_plan_that_lands_citing_suggestions_takes_the_first_card_and_folds_the_rest` each give the same verdict in two consecutive runs of `tests/api` and two of the whole suite, on one commit.

### 3. A test that cannot be made repeatable says so itself, rather than a lane finding out
Where a test's answer genuinely depends on something it cannot hold still, it
is marked as such and the suite reports it apart from the rest, so a lane
reads one verdict for what is settled and a named list for what is not.

Done means: the suite's output distinguishes the two, and a lane reading a
failure can tell in one line whether the failing test is in the named list.

### 4. The class is loud: the suite can be asked whether it agrees with itself
`needle fixes <slug|all> --unstable-tests --count` runs the pair and prints
how many tests answered differently. It is the plan's own measure and the
Loop's reader.

Done means: the command exists and prints a number; run against a commit with a deliberately unstable test it prints a non-zero one, so the count is proved to detect the thing before it is relied on to show its absence.

Hands out: execution — runs the suite one module per process from the lane's worktree, then `tsc` and `vitest`, and reports every failure verbatim; verifies re-running each named failure alone before treating it as this change's.

## Acceptance — behaviours

- The same code, run twice in the same scope, fails the same tests.
- A lane that meets a red suite can tell in one line whether that test is known not to hold still.
- No lane has to run the suite a second time to decide whether a failure is its own.
- A test that hid a real break in one run out of three is no longer possible without the suite naming it.

## Rulings

1. Item 1 comes first and alone. The suggestion named three candidate causes and this plan refuses to pick one before the evidence does — a wrong diagnosis here leaves the gate looking fixed and still lying, which is worse than today, where at least the lying is visible.
2. Marking a test as not-repeatable is a last resort per test, with its reason written at the mark, never a blanket setting. A named list of three is a fact a reader can act on; a suite that tolerates any disagreement is the defect again with a nicer face.

## Deliberately not

- Not a rewrite of `tests/floor.py`'s design: only whatever item 1 names.
- Not a change to what any test asserts. A test that disagrees with itself is not evidence that its assertion is wrong.
- Not retries, and not a rerun-until-green plugin: that buys a green verdict by hiding the thing this plan exists to remove.
- Not the two open defects those runs found along the way — the graded defect's face and the stranded cards — both already carded and neither this plan's.

## Loop

The thesis: the disagreement has one mechanism, not three, and naming it
removes all three tests' instability at once. If item 2 fixes the named
mechanism and any of the three still disagrees, the cause was plural and the
remaining ones are a second reading, not a second guess.

Loop: WATCH: the suite agrees with itself — command `uv --project /home/dennis/Work/needle run needle fixes all --unstable-tests --count` expect 0 by 2026-10-15 every 1d
