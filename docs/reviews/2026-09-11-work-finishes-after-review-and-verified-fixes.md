# Review — work finishes after review and verified fixes

**Plan:** docs/plans/done/2026-09-11-work-finishes-after-review-and-verified-fixes.md
**Reviewer:** Independent Codex session 01a090ab-7288-73b1-a71e-7f30accdb36d, Needle call 84, read-only.
**Diff range:** Needle base 1ecfa89 plus the frozen uncommitted implementation read by call 84; external instruction diffs at HR b8c0099f3, machine 3cda66b and HR3 a3a6a56. Repairs below were subsequently verified by the implementing colleagues, not represented as part of that earlier independent reading.
**Findings:** 3
**Verification:** Initial close-path checks: 22 passed; final absolute shared-pointer test passed. After the fenced-evidence repair, all 13 review-rule tests passed. Template parsed through review_of and progress_line: 3 found, 1 fixed, 1 no change, 1 filed. The complete remote suite passed across 93 modules and 719 tests at 9bbd860; distribution is complete.
**Completion:** Complete: all three independent findings repaired and verified; canonical code and instructions active on both machines; #124 and #504 closed using unchanged reviews.

## Dispositions

1. [boundary] CLAUDE.md:62-63 still required the next pass to re-read inside-change fixes, contradicting the adopted finite rule — FIXED in this change; replaced that last sentence with a pointer to §13. Verified no next-pass instruction remains in CLAUDE.md and inspected shared instructions.
2. [seam] docs/reviews/README.md omitted the Findings head that the existing board reader uses, so its three example dispositions displayed zero findings — FIXED in this change; restored the total head, retaining the existing parser and historical format. Drove the template through review_of and progress_line and verified all four counts.
3. [feature] board/review_rules.py discarded a legitimate fenced verification transcript and refused its record — FIXED in this change; fenced contents count only inside a real evidence section, while fenced example metadata cannot identify a reviewer or open that section. The original failed reproduction now passes; empty fences, fenced fake metadata and output outside the evidence section remain refused. Thirteen review-rule tests passed.

## Verification evidence

The independent reader reproduced findings 2 and 3 directly and found no remaining call-row dependency in the close. It reported normal pytest unavailable in its read-only sandbox; its direct invocation of eleven test bodies is not treated as a suite run. The implementing sessions ran the actual targeted pytest commands and recorded the counts above. Reader output is held by Needle call 84 and /tmp/needle-131-independent-review-answer.md.

Inspected active canonical instructions: Needle HOW-WE-WORK, HOW-WE-HOLD-IT, INTENT, CLAUDE and review README; HR review skill and README; machine review README; HR3 AGENTS. dennis-os, rented-machine and dennishettema entrypoints did not add a recursive requirement in the inventory. Both machines' user-level Claude/Codex instructions are symlinks to canonical Needle HOW-WE-WORK.

External documentation commits: HR 8fd1420e5; machine 387bc81; HR3 476da5b. These four external edits had no independent review findings. No production application code changed in those projects.

Existing worktrees contain historical instruction snapshots. Their target files were clean at inventory time; they were not overwritten while their owners may be reading or testing them. The canonical doctrine governs their older project methods. The owner ruling was recorded on Needle #131 and delivered through the Needle and Hello Revenue watercoolers. Delivery is recorded by the board; receipt and adoption by every existing session are not claimed.

The earlier research is preserved separately as historical evidence. It did not complete a controlled policy comparison and does not establish the token savings or final quality of this change. This change tests removal of mandatory recursive obligations, not the rest of the harness or a Kanban redesign.

Compatibility verification against the actual remote records: #124 was accepted unchanged; #504 exposed verification interleaved under Dispositions, which is now recognised as a legacy evidence container. This remains a presence check, not a claim that every disposition proves a test. A regression covers that old layout and an empty section. Seventeen targeted tests passed after compatibility and brief-fixture repairs. The partial local full run then exposed two bare # Review fixtures in test_dial; it was interrupted to move the comprehensive run to the rented machine in isolated module processes. This is not reported as a full-suite pass.

Final comprehensive verification: on rented, 93 isolated module runs covered 719 tests at `9bbd860880bf96fb83d6294abe67586a2c87f131`, Python 3.14.7, with zero remaining failures, errors or skips. The initial launch omitted `.venv/bin` from PATH, causing 17 failures in four modules that use the nested fake Needle command. Those four complete modules (50 tests) were rerun with the proper environment and all passed; no product code changed for that setup error. Initial run: 697.74 seconds; reruns: 135.28 seconds. Raw logs, JUnit XML, initial/rerun summaries and the combined result are under `/home/dennis/.cache/needle/card-131-suite{,-rerun}/` on rented. The initial failed run is retained and not represented as green. Subsequent source changes are documentation only. Ruff passed for every changed Python file.

The last instruction inventory found no mandatory recursive review wording in active canonical instructions, relevant skills or hooks across Needle, HR, HR3, machine, dennis-os, rented-machine and portfolio. Historical material and worktree snapshots were explicitly excluded. HR3's required hosted Verify run passed for 476da5b: https://github.com/hettema/hr3/actions/runs/34605188865 . HR, machine and HR3 current roots are synchronized on both machines.

Dennis reported clicking Watch on #131 and seeing a dead session. The actual implementation continued in the local card-131-review-once worktree and verification on rented. No Watch/session-status bug was changed.

Activation: Needle develop/main were promoted at d7ea496 and both main checkouts synchronized. The board restarted and GET /api/projects returned successfully. SHA-256 comparison confirmed twelve canonical instruction and enforcement files identical across laptop and rented. Both global colleague instruction links resolve to canonical Needle HOW-WE-WORK. #124 and #504 then closed into Executed with their existing delivered/watch text and original review paths, with no new review or copied call. #130's remote-close outcome is therefore met by #131; its old mechanism is explicitly superseded. #117's proposed per-repair obligation storage is retired rather than implemented.
