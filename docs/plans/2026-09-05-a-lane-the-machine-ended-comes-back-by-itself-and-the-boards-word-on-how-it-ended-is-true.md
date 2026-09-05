# A lane the machine ended comes back by itself once the reason has passed, and the board's word on how a lane ended is true

**Carries:** docs/slice-suggestions/2026-09-05-a-lane-the-machine-ended-is-resumed-by-the-machine-once-the-reason-has-passed.md, docs/slice-suggestions/2026-09-04-a-lane-that-folded-cleanly-is-reported-as-having-died.md, docs/slice-suggestions/2026-09-04-the-board-asks-for-a-rescue-on-work-it-recorded-as-done.md, docs/slice-suggestions/2026-09-04-nothing-moves-a-walled-lane.md
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation 6b683c8b), reading four defects about one mechanism
**Status:** PENDING
**Written:** 2026-09-05. Four suggestions, three finders, two days, one mechanism: what the lane loop remembers about how a lane ended, and what it does with the memory. #31 (2026-09-04) found that no actor moved a walled lane; the actor exists now (`api/loops.py::_rescue` moves on the handoff, and tonight's card histories read "Moved to fable on hrme"), so what is left of #31 is its second finding, a handoff file nothing consumes. #33 found the rescue asking the owner for a hand on finished work, because a wall never stops being true. #32 found the death reason written at first sight and never revised, a fold reported as a death, and two memories kept in one process's head. #68 found that after the one automatic retry nothing revives a lane the machine ended, though every cause has an end the machine can read: eight Hello Revenue cards sat ended for up to six hours through a wall reset nobody was awake for. Each was marked `now` on its own; together they are one plan, so one lane reads the loop once and fixes the class.
**Effort gate:** high — every piece is inside `api/loops.py` and `board/lane.py` with a fixture; the judgment is the rule's shape: once per cause, a park with an end, and never a guess at why a lane died.
**Sequencing:** after #53 (a resume that lands in the daemon scope rebuilds the pile that killed four lanes in one second tonight; #53's plan keeps a revived lane in its own scope and stops admitting when the machine is full, and this plan's resume goes through that gate).

## Intent

A lane that ended by the machine's hand — a wall, a kill, a process gone with no hook — comes back when the reason has passed, through the gate Start passes, once per cause; a lane that ended by its own work is left alone and the owner is asked; and every word the card says about how a lane ended is read at the end, from the evidence that held the process. HOW-WE-WORK §11: a move that follows a machine fact is the machine's, and a board the owner has to move by hand lies while he is away. Plan 03 wrote "the owner's choice is Resume or Look, never a guess" for a memory kill on 2026-09-04, before the dial existed; the intent in it — never a guess — is kept: the machine resumes only a death it can name.

What does not change: ruling 5 of the many-lanes plan — a dead lane's session is not stopped, its state is evidence, and the evidence is read and written on the card before any resume; the rescue horizon and the once-per-cause count; the Resume and Look doors for a lane that ended by its own work.

### 1. The reason a lane ended is read at the end, from the scope that held the process, and a fold is not a death
Done means: a session row that has never had a pid yields no death reason (the discriminator is a row that *had* a pid and now has none); the reason is computed when the session actually ends, never cached from first sight, so `the registry says: starting…` cannot outlive the birth it described; a lane scope's journal line older than the session's last life is not this death's cause, and a session that died with its daemon scope names that kill and its time (#435's second ending at 20:29Z on 2026-09-05 cited the lane scope's 18:37Z kill; the session had run in `claude-daemon-hrme.scope` since 18:38Z); a lane that folded is reported as finished — its sentence leads with the fold and names no cause of death, and the `died` line under the band is for a lane that died; tests for each of the four.

### 2. What the board knows about deaths and parks lives in the store
Done means: `_deaths` and `_parked` are rows every `needle` command and `needle serve` read from the store, not sets in one process's head; the park note lands once per run-out across a restart of `needle serve` and across a `needle` command that builds its own `Loops`; a test starts a fresh `Loops` over a store already holding a park and writes nothing new (card #196 carried the note seventeen times; #409 four times tonight).

### 3. A wall stops being true, and a park has an end the board reads
Done means: a handoff acted on is consumed, and one naming a finished lane expires; a walled lane's park ends at the reset time the wall carries ("resets 9:30pm (Europe/Stockholm)" — `claude-acct` already reads each limit's `resetsAt`), or sooner when the rule finds headroom on another slot; a memory park ends when the floor has held for a full beat; the card says what the park waits on and until when, as a machine fact with its evidence, never "yours" while the machine knows what it is waiting for; on the fixture, a parked wall lane's card reads the reset time and the park lifts at it.

### 4. A rescue first asks whether there is work to rescue
Done means: a card whose document is archived and whose fold, trunk level and main level are all recorded yields no rescue and no park note, however its session row and handoff file read; a Resume ask reaches the owner only when resuming would do something; a test on the fixture with a folded, synced, archived card and a live handoff.

### 5. A lane the machine ended is resumed by the machine, once per cause, through the Start gate
Done means: a wall, oomd's kill of the lane scope or of the daemon scope holding it, or a process gone with no Stop hook and no fold, is resumed by the lane loop through the runtime's resume (`runtime/service.py::resume`, the Resume door's act) with a placement with headroom and the memory floor satisfied on a fresh read; once per cause within the rescue horizon, and a second death of one cause within it parks with the reason; the dial's "took it once already; it is the owner's from here" (`board/dial.py::why_left`) counts a lane the machine ended as not yet run, and keeps its reason for a lane that ended by its own work — turn finished, said nothing, stopped by the owner, folded; the card's row names the cause and the count each time.

### 6. A test per cause, and the live read
Done means: fixture lanes for a lane-scope oom-kill with the floor satisfied (resumed on the next pass) and not (parked with the floor's numbers), a daemon-scope kill, a parked wall at its reset time (resumed), twice the same cause within the horizon (parked, the card saying what lifts it), and a turn that finished (left alone); live, every Hello Revenue card that sat ended on the evening of 2026-09-05 (#426, #429, #435, #417, #341, #416, #409, #419, #427) is either resumed by the board or parked with a reason and an end, and the close-out says which and when.

## Terrain
- `api/loops.py` — `_rescue`, `_parked`, `_deaths`, `_release_finished`, `RESCUE_HORIZON_SECONDS`, `_machine_moves`; the sets at `:163`–`:167` and the death write at `:340`.
- `board/lane.py` — the state derivation (`MOVING` needs a live process with a wall; `ENDED` is every dead process), the sentence at `:301`; `domain/lane.py` — one `ENDED`.
- `runtime/reasons.py:55` (the only producer of `the registry says:`), `runtime/registry.py:113` (`pid is None` for newborn and dead alike), `runtime/service.py::resume`, `runtime/launch.py::move` (whose docstring already names "a resume after a death").
- `board/dial.py::why_left` — "a lane exists for it (ended)" and "took it once already".
- The machine's `claude-acct`: `cmd_recover` drops a record whose process is gone, so an oom-killed lane is never recover's to revive; `resets` per limit at its `status` reading.
- The four carried suggestions hold the evidence: card #196's seventeen notes and reopened close; the birth epitaph's 127 ms window; four lanes moved by hand on 2026-09-04; the table of eight on 2026-09-05.
- Proof of search: one rescue (`_rescue`), one resume path (`launch.move`), one death-reason producer (`reasons.py`); this plan changes when each is called and what it remembers, and adds no second of any.

## Acceptance criteria
1. A newborn row yields no death reason; a fold reads as finished; a daemon-scope death names the daemon kill; a stale lane-scope line is never the cause.
2. The park note lands once across processes; a fresh `Loops` over a parked store writes nothing.
3. A parked wall lane is resumed at its reset time; a handoff is consumed; a finished lane yields no rescue.
4. A machine-ended lane is resumed once per cause under the gate; a second death parks with the reason and its end; a lane that ended by its own work is left to the owner.
5. The nine live cards are resumed or parked with a reason and an end, in the close-out; the suite, the ratchets and `tsc` are green.

## Loop
We think resuming machine-ended lanes under the gate will change the count of Hello Revenue lanes sitting ended with nothing folded at the morning read from eight toward zero, because every one of tonight's endings was the machine's and every cause has an end the machine can read. Loop: the morning count of lanes ended with nothing folded on Hello Revenue's Planned column — session read the board's broken count and the card histories at the first morning after the fold, then daily for a week, by 2026-09-13. If lanes are resumed and die again of the same cause within the horizon more than twice in a night, the gate is wrong and #53's card is the fix, not more retries. If cards still sit ended with a cause the board did not name, item 1 is the gap.

## Rulings
Recorded before the build, from the conversations; each overturnable by the owner on the card.
1. **The machine resumes only a death it can name.** Plan 03's "never a guess" is kept; its "the owner's choice is Resume or Look" for a memory kill was written before the dial existed, and the owner asked tonight for the opposite ("I don't think they revive by themselves"). Rejected: resuming without the gate — a revived lane on a full machine is the next kill, and tonight the retry into the daemon scope made each kill take more than one lane; the owner's Resume click as the way — eight cards sat up to six hours through a wall reset nobody was awake for; unbounded retries — the horizon stays, what changes is that a park has an end.
2. **One plan for four suggestions.** All four are what one loop remembers and does; four lanes would each fix an instance and re-read the same functions. Rejected: four fix lanes, in the order the dial happened to take them.
3. **A park is a machine fact with an end, never a verdict on the owner.** "Yours (Resume)" was the honest word when nothing could lift a park; now the board knows what it waits on and says so. Rejected: keeping "yours" and adding a reminder.

## Close-out
Written by the lane: a stance per item; the fixture cases by name; the nine cards' outcomes with times; the first park that lifted by itself, with what lifted it.
