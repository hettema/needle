# Work waiting for your feedback stays ready for your answer

**Status:** PLANNED
**Written:** 2026-09-16, prompted by Dennis: "It looks like something corrupted 601 on the needle. Can you carefully find the root cause and resolve it?"
**Effort gate:** high — a bounded lifecycle correction across recorded human decisions, session endings and recovery; preserve existing close precedence and distinguish stale requests from current ones.
**Challenged:** 2026-09-16, by codex (call 240): 4 material corrections before build

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

Where to look, decided at planning after reading the terrain: the exit rule
in `board/lane.py` (`exit_for`) sends an ended lane with nothing folded back
to where it came from without asking whether the owner's decision stands,
while the recovery rule beside it (`disposition`, `owner_decision_outstanding`)
already reads that from the card's ASK, Q and unanswered RULING rows written
in this life of the lane. The exit asks the same reader, at the one point
where it would otherwise send the card back to the start queue, and nothing
above that point — a landed close, a lane lent out, a fold nobody wrote up, a
stale DELIVERED — changes order. The lane's own face (`lane_for`'s ended
branch, which today reads only the session's last words) reads the same
standing decision, so a card waiting on him never says "session died, start
again"; the facts the face reads gain that one reading, made where the loop
already reads each lane's record (`api/loops.py::_facts`). The brief every
launched worker opens with (`api/doors.py`, the paragraph on asking the owner)
says how to hand a checkpoint over when the session will not stay: an ASK row
through `needle row`, with what he needs to do, and that WAITS asks him
nothing. No new row kind, column, store or state; no change to the question
regexes.

What the challenge round corrected in that reader before it is promoted (call
240, four demonstrated with reproductions against the fixtures): it selected
the first ASK row on the card, so an old checkpoint's words stood for a
current one — it reads the newest row of its kind; it never read the owner's
answer, so an ASK he answered through the card, whose session then ran on and
ended quietly, would park the card on him again — the one reader of "an
answer landed after this row" that `board/parked.py` already has moves to
`board/lane.py` and both read it; any RULED in this life silenced every
RULING, so a RULING written after the last RULED read as ruled on — a RULED
counts only after the RULING it follows; and the face's facts covered only
cards with a lane record while the exit also serves a lane without one — the
facts are read for every card whose lane the loop judges, with the same
fallback to when the card entered Executing, through one reader of a lane's
life that the two loops inline today. The brief names ASK in its list of
rows, and says the exceptions plainly: a landed close, a fold, a session
whose last words asked, keep their own exits.

Hands out: execution — run the board and api suites module by module and
report every failure verbatim; the judgment of what each result means stays
here.

Done means: an ended lane with an outstanding current request appears in Decision moment with what the owner needs to do, its face reads as his move and Resume is offered on it, so the same work continues without a new Start; it is not relaunched or presented as lost work. Stale/answered requests do not park unrelated future work: an ASK from a previous life, an ASK he answered, a RULED that follows its RULING, and a WAITS row alone each leave the exit as it was, and an old ASK beside a current one shows the current words. The HR601 regression is represented in meaningful checks, including the explicit ASK recovery now recorded and an ended lane with no record of its own, without widening every WAITS row into a human question.

**Met:** `tests/api/test_doors.py::test_a_lane_that_ends_at_a_checkpoint_it_handed_over_waits_for_the_owner` — a started lane writes WAITS and ASK, its session is stopped, and the card is in Decision moment with the face word "asked you", the sentence "Your move: decide what it asked and bring it back … the card carries a ASK row: Mark the four pilot ads…", Resume offered, one launch in the log, the machine's move naming the row; the same standing decision is read for the card with no lane record through the fallback to its entry into Executing; the brief carries the ASK handoff and "WAITS says what the work waits on and asks him nothing". `tests/board/test_lane.py::test_an_ended_lane_with_a_current_ask_waits_for_the_owner_instead_of_starting_again` — WAITS alone, an ASK from a previous life and an answered ASK each go back where the card came from as before, and a fold nobody wrote up keeps its own exit; `…whose_last_words_put_a_decision_to_him_waits_for_him` for the prose case; `…the_standing_decision_reads_the_newest_row_his_answer_and_the_ruled_it_follows` for the three shapes the challenge round reproduced and a RULED from a previous life; `…with_a_standing_decision_reads_as_his_move_not_a_death` for the face against the exit. The regexes in `board/lane.py` are untouched.

### 2. Review, integrate and verify the actual card

Complete independent review under HOW-WE-WORK §13, verify repairs, run the applicable suite once for integration and close the card through the supported commands. Verify the serving board is using the corrected behavior and #601 still retains its existing committed work and calibration request. If runtime activation needs a restart, protect active lanes and verify service health afterward; don't claim the running board changed merely because code landed.

Done means: the reviewed fix is integrated and live, the review and close record name evidence, and #601 truthfully waits on the two reviewers without losing or restarting the experiment.

Loop: WATCH: no lane that ended carrying an ask he had not answered went back to the start queue — command `uv --project /home/dennis/Work/needle run python -c 'import sqlite3,os,datetime;db=sqlite3.connect(os.path.expanduser("~/.local/share/needle/needle.db"));c=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=1)).isoformat();print("lanes sent back to the start queue with an ask standing over the last day:",db.execute("select count(*) from audit m where m.kind=? and m.actor=? and m.detail like ? and m.at>=? and exists (select 1 from audit r where r.project_slug=m.project_slug and r.card_number=m.card_number and r.kind=? and r.detail like ? and r.at<=m.at and r.at>=strftime(?, m.at, ?) and not exists (select 1 from audit a where a.project_slug=r.project_slug and a.card_number=r.card_number and a.kind=? and a.at>=r.at and a.at<=m.at))",("moved","machine","%the lane ended with nothing folded%",c,"row","ASK %","%Y-%m-%dT%H:%M:%S","-1 day","answered")).fetchone()[0])'` expect "lanes sent back to the start queue with an ask standing over the last day: 0" by 2026-10-16 every 1d

We think reading the owner's standing decision at the exit will keep every lane that ends at a checkpoint waiting for him, because the exit and the recovery now read the same rows against the same life of the lane. The count above is the trace: a machine move out of Executing with "nothing folded" on a card whose ASK, written in the day before and not answered since, still stood. If it is ever above zero, the card it names carries the lifecycle evidence to reopen with; nobody asks the owner to reconstruct it. Read on the laptop, where the board's store is. The first three ended lanes with a current request after the fold are read by hand at the close and named in the review record.
