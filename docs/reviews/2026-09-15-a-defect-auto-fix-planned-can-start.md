# Review — a defect auto-fix planned can start, whatever machine wrote the plan and whatever the title read

**Plan:** docs/plans/done/2026-09-15-a-defect-auto-fix-planned-can-start-whatever-machine-wrote-the-plan-and-whatever-the-title-read.md
**Reviewer:** an independent cold claude reading session with no share of this lane's context, called warm through Needle's own verb (`needle call bab7fb8a`, call 183, session 3cfc4e0a on armana). It was given the frozen revision, the plan, `docs/HOW-WE-WORK.md` §13 and ten surfaces to read, and was asked for findings in §13's terms.
**Diff range:** f89c770..08496b3 independently reviewed; repairs at 9bc708a, and one further repair this lane found afterwards (disposition 8). The lane was then rebased twice while it worked — onto 68e3d66 (#143's comeback change in `api/loops.py`, untouched here) and onto c40383b (#154, which lands in exactly this change's files). The final state is that second rebase's head, and the verification below is the full suite run there, on the merged tree.

**The merge with #154**, resolved keeping both sides in all six conflicts: `_take_next` keeps #154's two separate bounds, and its lanes half now reads `not self._under_the_number(fix_lanes)` — the one reading of the owner's number, which #151's second door into execution (the re-open) asks too, so a new door cannot become a second path past his ceiling. `running()` takes #154's signature with no `triaging=`. `held_lanes` carries both readers. `needle fixes` carries both flags, and `--reading-gaps` refuses to mix with `--stranded` as it does with the other two. Nothing of this change touches `running()`, `READINGS_AT_ONCE` or the readings bound. One consequence worth naming: #154 gives readings their own ceiling, so the deadlock that forced item 3's mid-build realignment — a live writer and the reading that must judge its title could not both run under a number of one — no longer exists on the merged tree. The realigned design is kept, because it is the safer of the two and needs nothing from that bound: only one of a card's sessions runs at a time either way.
**Findings:** 5 (3 from the independent read, standing against the reviewed revision and repaired; 1 the read reached that this lane had already repaired; 1 this lane found after the read, by reading the live board). Two further observations too small to be findings were taken as well. One hypothesis the reader could not settle received an evidence-backed no-change.

**Verification:** the full suite on the merged tree (this lane rebased onto #154's c40383b), one module per process, six at a time: 110 modules, 107 clean on that pass. The three that were not are accounted for individually, because a red nobody accounts for is the same as a red nobody ran:

- `tests/api/test_a_defect_auto_fix_planned_can_start.py` — mine, and genuinely broken by the merge: three assertions counted the raw launch log, which #154 made wrong on purpose (a beat may now open a reading beside its act), and one snapshotted the resume count after a rail walk that had already ticked the beat. The code was right in every case; the tests were reading the wrong thing. Fixed, and the module now passes whole, 15 cases.
- `tests/api/test_defects_column.py::test_a_defect_verified_before_the_scale_is_read_again_before_it_is_taken` — not mine and not reproducible: it passes run alone on a quiet machine. Load-sensitive, which is #145's live class.
- `tests/api/test_doors.py::test_a_post_is_answered_while_a_pass_is_stalled_and_the_passes_it_causes_coalesce` — not mine, and checked rather than assumed, because it failed twice and that is not evidence of innocence. It passes alone on this branch on a quiet machine, and passes on a clean clone of the trunk at c40383b with its own fresh environment. Load-sensitive, the same class.

`npx tsc --noEmit` clean on the merged tree; `npx vitest run` 2 files, 88 tests, all passing. `uv run ruff check` and `ruff format` clean on every changed file; the single E501 in `api/board_cli.py`'s module docstring is the trunk's own, verified by running ruff against the trunk's copy of that file.

**Baseline:** `tests/api/test_dial.py` was run before any edit, at the plan-only commit whose code is identical to f89c770: one failure, `test_a_held_plan_does_not_count_and_the_memory_floor_stops_the_beat`. It passes at the final revision. Recorded because a red met mid-lane must not be mistaken for this change's, and because #145 is live on exactly that instability.

**Completion:** every verified finding is repaired inside the change and verified by the checks above. The work is complete. What is *not* verified here: the served board itself. The fold and the laptop's restart are the close's own steps, and the Loop's command (`needle fixes all --stranded --count`) cannot run from the rented machine until then, because `needle fixes` is a board verb forwarded to the machine the board serves from, which runs the trunk's code. It is held in-process by test instead, and named as the close's last check.

## Dispositions

1. [feature] `api/dial.py:1182` and `api/dial.py:1157` — the hour was two clocks. `_hours_up` refused a resume on the fix lane's clock (`fix.planning_started_at`), while `_follow_title` tended the resumed writer with `ceiling_seconds=PLANNING_SECONDS` measured from the *new record's* `started_at` (`api/loops.py:2866`). A refusal arriving in the fifty-ninth minute was therefore handed back and opened a fresh hour, so one card could hold a fix slot for about two — and hold it against the number the whole time, so on a board set to one nothing else started. This breaks item 3's own realignment paragraph ("the hour is therefore the fix lane's … being handed a third refusal buys no more time than the first") and ruling 1. — FIXED in 9bc708a: the record's ceiling is now the lane's hour expressed in the record's terms (`PLANNING_SECONDS` less the seconds the lane had already spent when the record opened), so `now - record.started_at >= ceiling` is exactly `now - fix.planning_started_at >= PLANNING_SECONDS` and the rewrites share one bound. Verified by a new test, `test_a_rewrite_never_buys_a_second_hour`, which resumes a writer partway through the lane's hour and shows its record ended on what was left of that hour, not on a fresh one.

2. [feature] `api/dial.py:1213` — when the dial's hour ran out between turns, the beat returned silently. The card was left Planned with its Start still showing `board/title.py:157`, "The writer rewrites the title, and Start opens by itself when a reading of the rewritten title passes" — advice addressed to a writer nobody would resume. That is the exact failure Hello Revenue #453 was filed for, and it breaks item 3's done-means ("the card saying the hour ran out") and acceptance behaviour 2. The reader noted the branch two lines below it already does the right thing with `_say_once`. — FIXED in 9bc708a: the hours-up branch says so on the card once per spell, through a new `HOUR_SPENT` prefix, in the owner's words. Verified in `test_when_the_hour_runs_out_the_title_is_the_owners_and_the_lane_stays_planned`, which asserts the line is written, that a second beat does not repeat it, and that the card is countable as stranded.

3. [verification] `tests/api/test_a_defect_auto_fix_planned_can_start.py:565` — the assertion under the comment "And the board says so where the Loop can count it" was `main(["fixes", "all", "--stranded", "--count"]) == 0`, which is the process exit status and is 0 whatever the number printed. Item 4's second shape — a planned lane a failing title holds with no writer on it, which is what #453 becomes — therefore had no assertion on the count anywhere in the module, and the test would have passed had `stranded_words` returned None for it. — FIXED in 9bc708a: the test takes `capsys`, asserts the count prints `1`, asserts the lane's own line names why, and asserts the count returns to `0` once the card starts.

4. [feature] `board/dial.py:65` at the reviewed revision — `FOLLOWED_STAGES` added `FixStage.ENDED` to the set `api/dial.py` tested before calling `reconcile_now()`. Ended lanes are terminal and fix-lane rows are never deleted, so one historical ended lane made that guard true for ever and bought a machine pass on every 60-second beat. — ALREADY FIXED in a17d829, which landed while the read was in flight: `LIVE_STAGES` is restored and the read is paid inside `_follow_ended` by the one card actually re-opening. The reader confirmed the repair is at the right altitude. Found independently by this lane's own re-read before the review returned; recorded because the reader reached it too and the record should not imply the frozen revision was clean.

5. [seam] `api/dial.py` hand-back — `latest.verdict != TitleVerdict.UNPLACEABLE` was unreachable, since `title_hold` above it already required that verdict. — FIXED in 9bc708a (removed). Named by the reader as too small to be a finding; taken because a condition that cannot fire is a claim about the code that is not true.

6. [feature] `api/dial.py` `fixes()` — `store.latest_title_readings(fix.project)` ran once per lane inside a loop whose neighbour `graded` is memoised per project, on the command the Loop now runs daily across every board. — FIXED in 9bc708a (memoised per project, beside `graded`).

7. [feature] `api/dial.py:816` — the reader offered, explicitly as a hypothesis it could not settle: a lane staged ENDED because `start_windowless` was refused also has `planned_at` and `started_at` None, so `_follow_ended` admits it; if the owner later writes a plan for that card at the Plan door, the next beat opens Start without him. — NO CHANGE, with evidence. This is the dial's standing ruling correctly applied, not a widening: the card is one the dial took (`_ran` holds it), its board's switch is on, and a plan now exists — which is precisely the state in which the owner has already ruled that work enters execution without him. `_start` still reads the switch, the line and the release at the door, so every hold he owns still applies. The reader is right that item 2's prose describes the planning-session case only; the plan's words, not the code, are the narrower thing, and the behaviour is the one the dial is for. Recorded here rather than silently.

8. [feature] `api/dial.py::_follow_ended` — found by this lane after the review, by reading the live board rather than the tests. Every ended fix lane whose card carries a plan re-opens, and `_follow_ended` called `_start` for each in the same beat; `_start` is gated by the machine's room and the card's doors but never by the owner's number. A query against the board's own store on the laptop found seven cards on Hello Revenue standing in exactly that shape, so the first beat after the restart would have opened seven lanes at once on a board whose number is four. — FIXED before the fold: the beat brings back at most one card, and only while `_under_the_number` says the dial may put more work into execution. That reading is now written once and asked at both doors that enter execution — `_take_next` and the re-open — rather than being a second path past his ceiling. Verified by `test_the_beat_brings_back_one_card_a_beat_and_never_past_the_number`, which plants three such lanes under a number of one and shows a beat brings back at most one.

## Verification evidence

Commands actually run from the lane's worktree, with their results:

```
# the full suite, one module per process, six at a time, at a17d829
bash suite.sh            # 110 modules, 110 clean, 0 failures, 0 errors
                         # graded by reading every module's log: each reaches 100%
                         # with no FAILED/ERROR line and no "failed"/"error" in its summary

# the baseline, before any edit (code identical to f89c770)
uv run pytest tests/api/test_dial.py -q -p no:randomly
                         # 1 failure: test_a_held_plan_does_not_count_and_the_memory_floor_stops_the_beat
                         # passing again at the final revision

# after the three repairs, at 9bc708a
uv run pytest tests/api/test_a_defect_auto_fix_planned_can_start.py -q -p no:randomly
                         # 14 passed
bash affected.sh         # the 14 modules the repairs can reach: all clean

cd frontend && npx tsc --noEmit        # clean
cd frontend && npx vitest run          # 2 files, 86 tests, all passing
uv run ruff check <changed files>      # clean but for api/board_cli.py's
uv run ruff format --check <changed>   # pre-existing docstring E501, verified on f89c770
```

Probes run to settle specific claims rather than assume them:

- The board's own checkouts, read on the laptop over ssh, because the settle now turns on whether a levelling can run there: both `/home/dennis/Work/needle` and `/home/dennis/Work/hellorevenue` are on develop, clean, and 0 behind. The dirty-and-behind case the challenge raised is therefore latent rather than live, and is held by a test and made loud on the card.
- `first_read` (`api/loops.py:348`) levels every project once at startup, so `TrunkState.read_at` is never None on a served board. This corrected a test of mine that asserted its absence; the test now measures the stamp's movement, which is the real claim.
- `runtime/service.py:952` — `session(ref)` accepts a full session id, which is what `_wrote_the_plan` hands `resume`; it raises `NoSuchSession` when no registry holds the row, which is why that call is caught by name.
- `board/reconcile.py:301` — an imported card is never retitled from its document, which is the fact ruling 8 and #150 rest on.

## The challenge round, before the build

Recorded because the plan's head carries its line and the round changed what was built. A cold claude session (call 173) was given the plan, its terrain and the intended edits, and returned six material corrections. Three would have shipped broken: item 3 kept a planning session alive while the number counted it as held (eight live sessions under a number of four); the settle read `level`'s note rather than its verdict, which would have stalled every planning turn on a board merely off develop; and `session.updated_at or now` would have fetched once a beat against the plan's own ruling 3. The other three were the re-open's machine read, the selector guard that made the plan's own Loop command exit 1, and the plan's stale terrain line numbers. Two more came from this lane's own search at the same time: a card imported from the first board never shows its plan's title (#150), so handing its reading back would burn the hour on a rewrite that cannot pass; and the corpus lanes push through the same line, so they shared the defect and the fix.

Building the first of those corrections then showed item 3's own shape could not hold — a live writer and the reading that must judge its title cannot both run under a number of one — and the item was realigned during the build, with the reason written into the plan beside it.
