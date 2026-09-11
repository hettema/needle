# Why review keeps creating work

**Historical research assessment, September 11, 2026, before the owner adopted the finite workflow in card #131.** The later owner ruling and implementation are recorded in `docs/plans/done/2026-09-11-work-finishes-after-review-and-verified-fixes.md`; the recommendations below describe the earlier research stage.

**Research scope.** Requested by Dennis after investigating Needle #123/#124 and Hello Revenue #503/#504. Keep Kanban; focus on execution throughput. This document reports findings and proposes a bounded change in method. No shared rule, worker, experiment, account or runtime was changed. No new experimental model calls were launched.

## Conclusion and its limits

The strongest diagnosis is a recursive acceptance process with an unreliable boundary between a reviewer allegation and a required repair. The full-review stopping rule was improved on September 9, but the cold repair-check cycle can still generate another obligation on every read. Documentary and process findings can be promoted to behaviour findings, reopening the larger loop. Faulty checks add more work independently.

There is one directly reproduced enforcement defect: a cold reader's broken claim cannot be disposed of as a reasoned NO CHANGE or FILED by the current close validator. A record correction is allowed, but that is not an explicit disposition for a disproved allegation or an out-of-scope finding. This is an amplifier, not proof that it caused every historical loop: enforcement applies to review filenames dated September 11 onward; #503's record is dated September 10 and therefore exempt.

These observations establish avoidable work and a plausible system-level mechanism. They do not establish the percentage of elapsed time or subscription allowance wasted, or that removing review improves final quality. The existing experiment did not complete a comparison.

## Direct reproduction: the gate cannot dismiss a cold finding honestly

`board/review_rules.py:125–132` admits only FIXED and CORRECTED as answers to a cold reader's break. `:108–151` matches every break to such an answer. `:156–173` then requires a further cold read after a fix. Ordinary NO CHANGE and FILED are parsed, but do not discharge the cold reader's obligation.

I ran the actual `board.parse.review_of` and `board.review_rules.record_faults` against the existing synthetic RECORD from `tests/board/test_review_rules.py`. In memory, I replaced its repair disposition with three alternatives; the subsequent COMPLETE verdicts stayed in place. No files or board records were changed by this probe.

| Disposition of the original break | Actual validator result |
|---|---|
| NO CHANGE: a concrete reproduction disproves it; later cold verdict complete | Refused: broke 1.2 has no qualifying disposition |
| FILED: outside the agreed supported inputs | Refused for the same reason |
| CORRECTED in the record: the reader withdrew the allegation | Accepted |

This does not mean the author should be free to dismiss a demonstrated bug. It means the workflow needs an evidence-backed adjudication outcome, preserving the original finding and reason. A fallible review is evidence to assess, not an instruction that becomes true because it arrived from another model. Adding structured verdict storage through existing #117 does not by itself solve the disposition problem.

## How the remaining loop grows

1. **The stopping rule governs two different loops unevenly.** `docs/HOW-WE-WORK.md:313–327` requires cold reads of repairs while limiting additional full passes to live or latent behaviour. A fix from a cold read is another repair. The process can recurse without another full pass. The three-same-shape rule at :330 asks for a representation diagnosis, but does not itself demonstrate convergence.
2. **Old unconditional instructions remain alongside the new rule.** Needle `CLAUDE.md:68` and HR `.claude/skills/hr-feature-review/SKILL.md:19` say a first-pass stop is not a review. Needle `CLAUDE.md:94` still says to continue until a pass finds nothing new. Those sit beside the conditional September 9 stopping rule. Doctrine wins formally, but redundant conflicting instructions leave agents resolving policy while doing the work.
3. **The work and its documentation share the behaviour-grade escape hatch.** In HR #503's remote review, pass 13 found twelve issues, none in code; a renamed test cited by the plan was graded live. Pass 15 graded the remaining occurrence of the same old name as latent behaviour. Correcting an evidentiary claim matters, but a stale citation should not routinely reopen verification of otherwise unchanged product behaviour. The required response should follow what the incorrect claim could cause someone to believe or do.
4. **The boundary can settle too late.** The rule explicitly says before the final reading, not before the first review. #503 wrote its special boundary after twenty-five readings. That gave several rounds room to pursue the monitor's parsing of internal reason tokens inside client text. Some of these probes also demonstrated supported failures in the actual failure-message writers, so calling all late work imaginary would be false. Early agreement about promises, accepted inputs and evidence would make the classification less retrospective.
5. **Some safeguards add regressions to prevent other regressions.** #503's pass 24 records a false alarm introduced by round 14; pass 25 demonstrates a token in an accepted URL changing failure copy. #110's own stop record says thirteen later rounds chased the review-record validator's edges. These are concrete cases of growing verification machinery creating additional supported defects.

Sources for #503: on rented, `/home/dennis/Work/hellorevenue/docs/reviews/2026-09-10-a-website-heavy-with-video-still-gets-its-analysis.md`, lines 69–105, especially passes 13, 15, 24, 25 and the boundary. Its head records 160 findings over twenty-five readings plus a final clean read; 60 findings are about the record. Counts alone do not establish waste. #110: `docs/reviews/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes.md:7`.

## Independent source of friction: false-positive ratchets

Needle #124's remote test output records 725 passes and one failure after 2,093.36 seconds: `test_one_design_system.py` matched `#124` inside a comment as a raw colour. I independently ran the current RAW_COLOUR expression against that comment and `color: #124`; both match `#124`. The implementation at `tests/ratchets/test_one_design_system.py:15–45` scans text without distinguishing comments from CSS values.

That proves the failure was unrelated to the intended design-system boundary. It does not mean the entire 35-minute run was wasted: those tests still verified the work. The avoidable part is the false rejection and any work it subsequently caused. The unfinished-work check similarly rejects the HTML attribute `placeholder`; the September 9 focus review records changing the interface to satisfy it.

## Earlier research located

- **September 2:** HR `docs/research/2026-09-02-the-line-and-the-harness-reexamined.md`, with `...-evidence.md` and `...-deliberation.md`. This mixes research into the campaign-generation system with an engineering-harness audit. Its engineering section records real product catches and harness self-policing separately. It is historical evidence, not a measurement of the review rules adopted on September 8–10. Its keep-review recommendation does not validate the subsequent recursive enforcement.
- **Broad Card 456 trial:** the private remote experiment reports no builder ever started. Preparation and runner review produced multiple rounds of their own. It cannot compare broad harness-on against harness-light performance.
- **September 10 missing-page review-policy pilot:** superseded the broad build experiment for this question. Its protocol changes only review policy within each model pair; both policies omit board/commit/fold rituals. Therefore even a completed result would not measure all Needle overhead or all ratchets.

## What actually happened to the pilot

Remote source directory: `/home/dennis/.local/share/hr-harness-trial/worktree/experiments/coding-harness-trial/`. Read `PROTOCOL-review-pilot.md`, both policy files, `pilot-review-rubric.md`, `REPORT-review-pilot.md` and `STATUS.md`. Private evidence root: `/home/dennis/.local/share/hr-harness-trial/card456-20260910/`.

| Arm | Verified artifact state |
|---|---|
| Codex / lighter | Manifest assessed; final judge FAIL. One supported redirect defect remained. |
| Claude / current | Builder finished; policy interrupted in its first round. Manifest finished_unassessed; no repair edits recorded. |
| Codex / current | Prepared; never started. |
| Claude / lighter | Prepared; never started. |

The lighter arm's raw metrics show 479.75 seconds building, then 503.10 reviewing, 477.34 repairing, and 472.16 checking repairs. The report's total policy time is 1,757.08 seconds including coordinator work: about 29 minutes following an 8-minute build. That is overhead, not automatically waste: review did identify a real origin-divergence defect, which the repair removed.

The final judge found another-host redirect ending in 404 incorrectly authorised an overwrite. I read the mock-only reproduction script and stored before/after traces: baseline zero uploads, first patch one, final patch one. The defect existed before repairs. It was missed by the lighter review/check and absent from the current arm's first review too. I did not rerun these historical patches or edit them. This supports testing better initial counterexamples; it does not show that another recursive review would necessarily catch the issue.

The stops were separate from review quality: an initial access-expiry handling failure, coordinator model capacity, then the pinned Claude participant's allowance rejection at 18:38:24 UTC on September 10. The coordinator service inspected this turn is inactive. The blocked participant metadata and manifests agree with the stopped status. Access renewal had already been repaired. The runner still hardcodes `hrclaude` (`run.py:394–440`); the later continuity note explicitly distinguishes fixed model from fixed account and allows same-model account selection in principle. Current availability of alternative accounts was not checked.

One claim in the report is too strong: it says the pilot consumed roughly a week's capacity. Its own quota trajectory begins at 0.86 and ends at 1.0 in one reported window, while another window ends at 0.51. This establishes exhaustion of the available remainder, not consumption of a full week's allowance or sole attribution to the experiment. Coordinator token telemetry is missing. Do not convert cached-token counts or nominal API list prices into subscription usage.

The evaluator needed three documented adapters because its fake internals depended on implementation shapes. Raw failures and adaptations were preserved; the independent judge caught a defect despite the adapted assertions passing. This is useful measurement work, but also demonstrates how broad private fake interfaces can make an experiment spend effort maintaining the evaluator. Preserve outcome assertions while testing at stable boundaries.

## External evidence and what it can establish

Anthropic's March 2026 [harness study](https://www.anthropic.com/engineering/harness-design-long-running-apps) describes removing scaffolding as model capability improved. It retained useful planning and evaluation while removing the sprint structure; it also reports that removing many components together initially made attribution difficult. This supports targeted subtraction, not a universal one-review rule or a claim about our present models.

Its [agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) recommends evaluating outcomes rather than rigid action sequences and inspecting transcripts to distinguish agent mistakes from grading failures. Our colour-comment rejection and private evaluator adapters are local examples of that distinction. These articles are practice reports, not controlled evidence that our lighter policy will preserve quality.

## Recommended action

First repair the enforcement and instruction contradictions, through existing work where possible: preserve a supported, auditable outcome for disproved or outside-scope cold findings; reconcile duplicate stopping instructions with the adopted rule; keep ordinary record corrections from impersonating product failures; remove semantic false positives from delivery-blocking checks. No known behavioural defect may be waived merely to finish faster. These are concrete corrections to the existing intent, not a proposal to delete all tests or trust authors uncritically.

Then test the review structure, rather than restarting the broad Card 456 experiment unchanged. Keep the original evidence frozen. For a new bounded comparison, copy each identical frozen first patch into both review-policy arms, so initial builder variation cannot masquerade as policy effect. Use more than one patch/defect shape and replicate before generalising. Keep models, effort, tools, task contracts and final evaluator matched; record account provenance without unnecessarily pinning one exhausted subscription.

The candidate policy should front-load one independent review of the whole promise and relevant seams, adjudicate allegations against evidence before mutation, batch accepted repairs, and check those repairs and affected dependencies. A further full read needs a demonstrated reason in the changed behaviour. Repeated findings on the same failure should trigger diagnosis of the representation, not another local patch by default. This is a test candidate; existing evidence does not justify making it the permanent policy today.

Measure supported defects remaining, defects removed, defects introduced by repairs, rejected reviewer allegations, review/repair time and model usage separately from setup, outages and evaluator maintenance. Include a clean patch to test unnecessary changes. The final blinded evaluator must be identical across arms and must not feed repairs. Do not reuse disclosed held-out defects as if still unseen; the redirect can become a known regression check, with separate unseen cases for evaluation. If a budget expires, record incomplete; do not call that evidence of lower quality caused by review policy when provider downtime caused the stop.

Success is equal or better supported behaviour with less avoidable rework. Fewer rounds, less prose, a faster green suite, or an exit-zero coordinator are not sufficient on their own. Kanban and remote independence remain; no UI redesign is needed to test this diagnosis.

## Verification boundary

This was source/history inspection, remote read-only artifact and process inspection, external primary-source research, and two in-memory reproductions against current Needle code. It did not rerun the large production suites, restart the experiment, change review policy, or perform an independent review of this research. The search-role delegation capability was unavailable; the author performed that search directly.
