# Review — a running lane hears the board (slice 10)

**Plan:** docs/plans/done/2026-09-04-10-a-running-lane-hears-the-board.md
**Reviewer:** the build session (Claude Fable 5.1 at high for the build, Claude Opus 5 at high for the last two passes and the close, after a subscription run-out mid-review). No second session was in the loop; the live round on the served board is the sign-off this record cannot replace.
**Diff range:** 16a8023..HEAD on the lane `card-26-10-a-running-lane-hears-the-boar` — two code commits (the word, the route, the hook's PostToolUse arm, the heard table with migration 0008, the rewritten ratchet, the page line, twelve tests; then the review's own fixes). The docs commit that follows carries this record, the archived plan and one filed defect.
**Findings:** 11 — 8 fixed before this record, 2 no change with the reason, 1 filed.

## The passes

The review ran as a loop (`CLAUDE.md`): each pass one lens, the fixes landed, the next pass re-read the fixed work.

1. **The feature against the plan's "done means".** Item 1: the board holds one typed `Word` per live lane — the drift sentence when the verdict changes (appears, names different files, clears), every watercooler line said since the lane last heard by another lane or by the board and never its own, and the fold line, which arrives as the board's own watercooler line rather than as a fact of its own; a read moves the mark; the mark is in the store, so a restart forgets nothing; the open card shows when the lane last heard and what, beside the watercooler it already showed. The two-lane fixture test walks exactly the plan's acceptance criterion 1. Item 2: the hook is registered for PostToolUse, asks with a half-second ceiling, prints `hookSpecificOutput.additionalContext` and exit 0, and prints nothing on empty, 503, slow, unknown directory or a subagent's payload; the event is never queued or posted; the route reads the loop's last read and the store and never git. Item 3: the ratchet holds the intent, below. Findings 1 to 3 came from this pass.
2. **The seams.** Concurrency: the word takes a lock of its own, not the loops' lock, and the read of the mark, the compose and the write are one act under it. Failure and restart: a board that is down, hung or answering rubbish prints nothing and costs the session at most half a second; a board that has not read the machine yet returns an empty word and moves no mark, so nothing is lost across a restart; the mark survives in SQLite and is cleared with the lane record when the card is launched again. The truth of what the board shows: the card's heard line is stamped only by a word that said something, so a silent mark never claims the lane was told. Cost: the word runs on every tool call of every session on this machine, which made three of the findings. Findings 4 to 8 came from this pass.
3. **The boundaries.** Layers: `board/word.py` imports domain only and is pure — the caller reads the snapshot and the store and hands them in; `api/loops.py` is the one place that meets both. The board never runs: the word reads, spawns nothing, and the route takes no door. Typed edges: `HeardMark` and `Word` are Pydantic, `frontend/src/types/hook.ts` and `board.ts` regenerated, the page fixture regenerated, `tsc` clean, no `any`. One design system: the existing `Heard` primitive carries the open card's line, with one CSS rule for its open-card form; no new primitive. Nothing half done: no deferral marker. The store's shape is one schema with migration 0008. Finding 9 came from this pass.
4. **The seams and the feature again, after the fixes.** The fixed work re-read: the quiet baseline is written on the first word and the mark then reads only the lines past it; the page turns over only for a word that said something; the composer's contract with its caller is stated and pinned by a test; the ratchet's catch-all check reads a docstring and a trailing `return 0` correctly and still refuses a print from `main`. 297 backend tests and 33 page scenarios pass, `tsc` is clean, the lane's files lint and format clean. Nothing new. Clean.

## Dispositions

1. **The word read the project's whole watercooler on every tool call.** `store.watercooler(slug)` with no bound, from a hook that fires thousands of times over a lane-day. FIXED: `Store.watercooler` takes `after=`, and the caller reads only the lines past the mark.
2. **A lane with nothing to hear kept no mark, so it re-read the whole watercooler forever.** The first version wrote a mark only when the word said something, so a quiet lane — the common case — recomputed its baseline from the entire table on every single tool call. FIXED: hearing that moved is written down even when nothing was said; only a word that said something stamps `at` and `text`.
3. **The hearing's baseline was the session's start, not the lane's.** A resume forks the session id (verified in slice 04), which moves `lane.hands_on_since`; a resumed lane would have re-heard every line said before the resume. FIXED: the baseline is the lane record's `first_seen`, which outlives a resume.
4. **The hook imported `urllib.request` at module level**, on a path that no longer used it — measured at about 15 ms of a ~40 ms interpreter start, on every tool call of every session on this machine. FIXED: `urllib.request` is imported inside `drain`, where the four session events post; the word is read with `http.client`, imported inside `answer`.
5. **`urllib.error.URLError` was still named in the drain's suppress list** after the import moved. FIXED: `URLError` is an `OSError`, so the one name covers it.
6. **A silent mark turned every open page over.** `live.bump()` fired whenever the mark moved, including for the baseline and for a lane's own line going by — a refetch for a card line that reads the same, on every tool call. FIXED: the bump is for a word that said something.
7. **The composer's contract with its caller was implicit.** `compose` needs the whole watercooler when there is no mark (the baseline is read from it) and only the lines past the mark otherwise; nothing said so, and a future session tightening the read would silently lose a line. FIXED: the contract is in the docstring and pinned by its own test.
8. **The ratchet's catch-all check refused a docstring and a trailing `return 0`.** It required the function body to be exactly one `Try`, which `main` and `answer` are not. FIXED in the check, which now skips a docstring and allows a trailing return of a constant — and still proves it sees a `print` from `main` and a `sys.stdout.write` at module level.
9. **`/api/word` takes an arbitrary `cwd` and is unauthenticated.** NO CHANGE: the board binds to 127.0.0.1 and every route on it is unauthenticated by design (it is one owner's machine, INTENT.md "not a team tool for humans"); the word answers only for a directory that is a lane of a registered project and carries what that lane's own brief already carries. A caller who can reach the port can already read the whole board.
10. **`Loops.word` does not sync the project list**, so a project registered in the last moment answers 404 until the next sync. NO CHANGE: the route's whole job is to be cheap enough for every tool call, and a project sync reads the store and the corpus; the lane gets its word one beat later, which is inside the minute the intent asks for.
11. **Eight of Hello Revenue's real card titles are in the public repository**, in eleven places across `docs/design/2026-09-04-the-colour-language/*.dc.html` (commit 16a8023), and `test_no_real_card_title_is_in_the_tracked_tree` is red on the trunk for every lane that rebases onto it. OUTSIDE THE CHANGE: filed as `docs/slice-suggestions/2026-09-04-real-card-titles-reached-the-public-repository-through-the-design-comps.md`, `Kind: defect`, and said on the watercooler to #27, whose live lane wrote them and inside whose change the fix belongs. The suggestion carries the larger half too: a fold that lands a red commit leaves every other lane holding a failure it did not cause, and `needle fold` does not run the ratchets.

## What was checked

- **The suite:** 297 backend tests including the ratchets — 7 new in `tests/board/test_word.py` (the drift said once and its clearing once, a drift naming different files, other lanes' lines once and its own never, the baseline before any mark, drift and lines as one word, the quiet lane's baseline, the caller's contract), 1 new in `tests/api/test_hook_script.py` (the real script on a PostToolUse payload: the context JSON, then empty, unknown directory, subagent, 503, slow past the ceiling, and no board at all — exit 0 and empty stdout every time), 1 new in `tests/api/test_cli.py` (`hook install` adds PostToolUse to a project that has the four, keeps a foreign hook, names the ceiling, idempotent), 1 new in `tests/api/test_doors.py` on the two-lane worktree fixture (the plan's acceptance criterion 1 end to end, including the mark read back from a reopened store), and the rewritten hook ratchet. `npx tsc --noEmit` clean; 33 vitest scenarios, the collision scenario extended with the open card's heard line.
- **The one red test on the trunk** is `test_no_real_card_title_is_in_the_tracked_tree`, from commit 16a8023 and not from this lane (`git diff --name-only 16a8023..HEAD` names no file under `docs/design/`). Everything else is green; disposition 11.
- **The cost, live:** measured before and after with the real script against the served board, below.

## The cost, measured

The prediction fixed in the plan: under 80 ms per tool call including the interpreter, and half a second at worst when the board is down or hung.

Measured on the lane's own machine with the real script and a real PostToolUse payload, old and new **interleaved run for run** so both carry the same noise. Taking them as two separate rounds is worthless here: the same unchanged old script measured 47.7 ms median in one round and 114.3 ms in the next. Load average is reported with every number, because it turned out to be the dominant term.

Under load 5–10 (three lanes and a served board), 40 rounds:

| load ~8 | median | p90 | max |
|---|---|---|---|
| before (four events, no word) | 114.3 ms | 266.1 ms | 344.3 ms |
| after, board up | 155.1 ms | 327.7 ms | 502.3 ms |
| after, board down | 113.6 ms | 318.9 ms | 615.8 ms |

Read alone, that says the word costs ~40 ms and the prediction is missed. Re-measured on the same machine an hour later at load ~4, the same pair, two rounds of 40:

| load ~4 | median | p90 | max |
|---|---|---|---|
| before | 59.5 / 51.4 ms | 119.1 / 57.1 ms | 181.4 / 85.3 ms |
| after, board up | 61.9 / 51.6 ms | 106.3 / 60.4 ms | 119.7 / 127.9 ms |
| after, board down | 50.6 → 41.9 ms | 58.2 → 58.4 ms | 70.5 → 67.1 ms |

**The prediction is met, and the ~40 ms was load, not code.** The word costs **0.2–2.4 ms of the median** over the old hook — a localhost round trip inside an interpreter start that dominates it — against the plan's 80 ms ceiling, and the new script's p90 is at or below the old one's. With the board down the new script is *faster* than the old (41.9 vs 50.6 ms median), because the word path no longer imports `urllib.request` at module level: `python3 -c pass` is 10.7 ms, the hook's standard-library imports take it to 24.7 ms, and `urllib.request` alone took it to 40.3 ms. That is finding 4, and it paid for the word twice over.

The worst case holds as designed: a hung board never held a call longer than the script's own half second (asserted in `tests/api/test_hook_script.py` against a server that sleeps past the ceiling).

**What this cost the review:** the first reading was written up as "the prediction is not met" before the re-measurement, on numbers taken under load 8. A performance number without the machine's state beside it is not a measurement, and this one would have sent the owner after a regression that does not exist. The WATCH row watches the delta on a quiet machine, not the absolute.

## What the build learned the plan got wrong

- The plan said "the board keeps a word for each live lane and says it once", and had the mark move only when the word said something. That makes a quiet lane — nearly every tool call — recompute its baseline from the whole watercooler forever. The mark has to move whenever *hearing* moved, and only the saying is what the card shows (findings 1, 2, 6).
- The plan named `lane.hands_on_since` nowhere but implied the session as the unit of hearing. The lane record's first sighting is the right one, because a resume forks the session id (finding 3).
- The plan's cost prediction ("under 80 ms per tool call") was fixed as an absolute, without naming the machine's state — and the absolute is mostly a property of the load, not of this change. At load 8 neither the old hook nor the new one is under 80 ms; at load 4 both are, comfortably. The measurable thing is the delta, and the prediction should have been written as one ("the word adds under N ms to the hook's median, measured interleaved on an otherwise quiet machine"). Fixing it as an absolute nearly bought a regression report for a 2 ms change.
- The plan said the word carries "the '#M folded over this lane's edits' line when a fold lands over it" as one of three facts. It already arrives as a watercooler line the board itself says at the fold (slice 07), so it needs no separate branch — the test proves it lands.

## Not done, stated

- **The collapsed card does not show when its lane last heard.** The open card does, in the watercooler section. The collapsed face already carries the lane's sentence, the collision and the watercooler's last line; a fourth line there is noise, and the plan asked for "the open card".
- **The word is not shown to the owner as it is said.** He sees the mark's last text on the open card and the watercooler in full; there is no feed of "what the board told which lane when". The card's history was the alternative and was rejected in the build: a history row per word would bury every card's real history under the machine talking to itself.
- **`needle hook install` has not been run on every project on the board.** That is the close-out's live step, recorded on the card after the fold; until then only Needle's own repository has the PostToolUse entry.
