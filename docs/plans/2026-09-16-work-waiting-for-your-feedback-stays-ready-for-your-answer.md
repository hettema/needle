# Work waiting for your feedback stays ready for your answer

**Status:** PLANNED
**Written:** 2026-09-16, prompted by Dennis: "It looks like something corrupted 601 on the needle. Can you carefully find the root cause and resolve it?"
**Effort gate:** high — a bounded lifecycle correction across recorded human decisions, session endings and recovery; preserve existing close precedence and distinguish stale requests from current ones.

## Intent

Work that has reached a planned human-feedback checkpoint stays visibly ready for that feedback when its session exits, with its existing work preserved and a clear path to continue. It must not look like failed work to start again.

## Evidence and terrain

Hello Revenue #601 reached its explicitly planned calibration pause. On rented, session `3a97f910-02ad-437f-a441-fa70ef8f22bb` ended after asking Dennis and Maria to mark four pilot ads. Its clean worktree remains at `/home/dennis/Work/hellorevenue/.claude/worktrees/card-601-test-whether-hr-can-create-ads-w`, with commits through `b7b1bbe7d`. Its final substantive response is stamped 2026-09-16T16:16:06Z; its WAITS row was written at 16:15:51Z. Board history later records Executing to Up next at 17:20:18Z: "lane ended with nothing folded". No evidence establishes a crash. The experimental results and paid-call artifacts are present. Do not restart, modify, fold or spend on that experiment.

Immediate recovery by the diagnosing session: wrote an ASK row with the existing calibration artifact link and moved #601 through the board API to Decision moment. This is a repair to the operational record, not completion of the experiment. Owners still owe calibration.

Proof of search: read `board/lane.py` `owner_decision_outstanding`, `disposition`, `asks_owner`, `exit_for`, and `api/loops.py` `_move_by_fact` / `_wait_owed`. The recovery disposition already reads current ASK/Q and unanswered RULING rows, while `exit_for` falls back to `came_from(history)` without that check. The final prose was imperative, so the question regex did not recognize it; WAITS alone is not a typed owner decision and may represent many other waits. Do not enlarge a prose regex as the principal fix. Reuse the existing owner-decision semantics and teach the supported explicit handoff where sessions read it; no second decision store or lifecycle. Check question lifecycle and stale-row handling before selecting the smallest correction.

Existing work searched: Needle #88 concerns wording of existing Decision moment reasons, not this misrouting; #136 concerns already-answered requests. Preserve those boundaries and coordinate any shared files. Needle #68 introduced recovery disposition. `docs/INTENT.md` says the board is true at every moment and all moves except entry into execution are teamwork. `domain/row.py` already distinguishes ASK/Q from WAITS. Relevant blast radius: exit/recovery policy, current-request recognition, card state/doors and session handoff instructions. No product-generation work and no automatic new spend.

## Items

### 1. Keep an outstanding owner checkpoint visible through session exit

Use the existing lifecycle and request record to route the current owner decision correctly, preserve completed/archived precedence and avoid resurrecting requests from earlier lives or decisions already answered. Assess recovery and visible card state together. A silent stop without a current request must retain its existing recovery behavior. Document the explicit checkpoint handoff in the canonical session instructions already used by launched workers.

Done means: an ended lane with an outstanding current request appears in Decision moment with what the owner needs to do; it is not relaunched or presented as lost work. Stale/answered requests do not park unrelated future work. The HR601 regression is represented in meaningful checks, including the explicit ASK recovery now recorded, without widening every WAITS row into a human question.

### 2. Review, integrate and verify the actual card

Complete independent review under HOW-WE-WORK §13, verify repairs, run the applicable suite once for integration and close the card through the supported commands. Verify the serving board is using the corrected behavior and #601 still retains its existing committed work and calibration request. If runtime activation needs a restart, protect active lanes and verify service health afterward; don't claim the running board changed merely because code landed.

Done means: the reviewed fix is integrated and live, the review and close record name evidence, and #601 truthfully waits on the two reviewers without losing or restarting the experiment.

Loop: session — After integration, read the next three ended lanes with current owner requests and their move histories. We expect all three to remain available for their owners without a new Start, because exit and recovery use the same current-decision evidence. If any returns to the start queue or hides the request, reopen with that card's lifecycle evidence; do not ask the owner to reconstruct it. Name the supported signal form at close.
