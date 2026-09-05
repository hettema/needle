# A lane the machine ended is resumed by the machine once the reason it ended has passed, and only then

**Kind:** defect
**Fix:** now — the intent is written (HOW-WE-WORK §11: a move that follows a machine fact is the machine's, and a board the owner has to move by hand lies while he is away; plan 03's "one automatic retry per run-out" is the precedent, and the dial is his standing ruling that a verified defect runs without him); the owner asked for it tonight in his own words ("I don't think they revive by themselves"); the fix stays inside the lane loop's rescue and the dial's gate; it removes the class — every lane ended by the machine rather than by its own work — not the eight cards below.
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation 6b683c8b), looking at Hello Revenue's Planned column: "I see a lot of broken cards in Hello Revenue's plan lane. I think they are crashed processes. I don't think they revive by themselves."

## Observation

At 20:54Z on 2026-09-05 Hello Revenue's Planned column held eight cards
whose lane had ended with nothing folded, and Executing held a ninth the
board doubted. None was crashed by its own work. Read from the card
histories and `journalctl`:

| Card | Started | How it ended | Came back? | Ended again | Sat waiting |
| --- | --- | --- | --- | --- | --- |
| #426 | 16:45Z, hrme | oomd killed its lane scope 16:54Z | yes, 17 s later, same session | 17:59Z, with the hrme daemon scope | 3 h |
| #429 | 17:26Z, hrme | oomd killed its lane scope 17:57Z | yes, 19 s later | 17:59Z, with the hrme daemon scope | 3 h |
| #435 | 18:21Z, hrme | oomd killed its lane scope 18:37Z | yes, 15 s later | 20:29Z, cause misnamed (below) | 25 min |
| #417 | 12:49Z, armana | wall; moved twice, last to hrme 16:07Z | — | 17:59Z, with the hrme daemon scope | 3 h |
| #341 | 14:59Z, hrclaude | — | — | 16:03Z, with the hrclaude daemon scope | 5 h |
| #416 | 12:49Z, armana | wall; moved to gmail 14:03Z | — | 14:31Z, with the gmail daemon scope | 6 h |
| #409 | 11:18Z, gmail | wall; moved twice, parked 16:16Z | — | process gone; "resets 9:30pm" | 4 h |
| #419 | 15:24Z, hrme | wall; moved once, parked 16:18Z | — | 16:25Z, "the session was stopped" | 5 h |
| #427 | 17:22Z, hrme | — | — | 17:59Z, with the hrme daemon scope; card still in Executing, doubted | 3 h |

Three things in that table, each a fact the board can read and none of
which it acts on:

1. **A lane that oomd kills comes back once, into the wrong place, and its
   second death takes the neighbours.** The machine's recover unit put
   #426, #429 and #435 back within twenty seconds of the kill, inside the
   subscription's daemon scope, as card #52 found for #386 this morning.
   The daemon scope is then the biggest cgroup on the machine, and oomd
   took three of them today: `claude-daemon-gmail.scope` at 14:31Z (106
   processes), `claude-daemon-hrclaude.scope` at 16:02Z (236),
   `claude-daemon-hrme.scope` at 17:59Z (162). The 17:59Z kill ended
   #426, #429, #417 and #427 in the same second. After a daemon-scope
   death nothing comes back: `claude-acct recover` drops a record whose
   process is gone (its docstring says so), and the board's rescue
   (`api/loops.py::_rescue`) acts only on a lane in `MOVING`, which needs
   a live process with a wall. A dead process is `ENDED`, whatever killed
   it, and `ENDED` is nobody's.

2. **A wall's park never lifts.** #409 and #419 were moved once (plan 03's
   one automatic retry) and parked on the second wall within the hour with
   "so this one is yours (Resume)". The wall text names its own end:
   "resets 9:30pm (Europe/Stockholm)". 21:30 local passed at 19:30Z; at
   20:54Z both still sat parked, one and a half hours into a limit that
   no longer existed. `claude-acct` already reads each limit's
   `resetsAt`; Needle reads none of it.

3. **The dial will not touch a card whose lane exists, and will not take a
   card twice.** `board/dial.py::why_left` returns "a lane exists for it
   (ended)" and then "the dial took it once already; it is the owner's
   from here". So a fix lane the dial itself started, killed by the
   machine the dial admitted it to, is the owner's from that second on —
   which is the "his by default" the doctrine's §1 was rewritten to end.

The board also misnamed one death. #435's second ending at 20:29Z carries
"the journal for needle-card-435….scope says: Failed with result
'oom-kill'" — the lane scope's line from 18:37Z. The session had been
running in the daemon scope since 18:38Z; whatever ended it at 20:29Z is
not in that scope's journal, and the card states the earlier kill as if it
were the cause. A retry keyed on the cause needs the cause to be current.

Plan 03's done means for this case reads: "a lane that dies for any other
reason (memory kill, exit, the machine restarting) carries the machine's
reason in one line … and the owner's choice is Resume or Look, never a
guess." That was written on 2026-09-04, before the dial existed and before
the doctrine said a board he moves by hand lies while he is away. The
intent in it — never a guess — is kept below: the machine resumes only a
death it can name.

## What would hold it

1. **One rule for every ending the lane did not choose.** A wall (the
   handoff, today's rule), oomd's kill of the lane scope or of the daemon
   scope holding it, a process gone with no Stop hook and no fold. The
   lane loop resumes it through the runtime's resume — the Resume door's
   act, `runtime/service.py::resume` — under the same gate Start passes:
   a placement with headroom and the memory floor satisfied on a fresh
   read. Once per cause per lane within the rescue horizon; a second death
   of the same cause within it parks with the reason, as the wall does
   today. The card's row names the cause and the count.

2. **A park lifts when its cause lifts.** A wall's park lifts at the reset
   time the wall carries, or sooner when the rule finds headroom on another
   slot; a memory park lifts when the floor has held for a full beat. The
   card says what it waits on and until when, as a machine fact with its
   evidence — never "yours" while the machine knows what it is waiting for.

3. **The cause is read from the scope that held the process.** A session
   resumed into a daemon scope dies with the daemon scope, and the card
   names that kill with its time; a lane-scope line older than the
   session's last life is not this death's cause.

4. **The dial's "took it once already" counts lanes the machine ended as
   not yet run.** Its reason stays for a lane that ended by its own work:
   turn finished, said nothing, stopped by the owner, folded. Ruling 5 of
   the many-lanes plan — a dead lane's session is not stopped, its state is
   evidence — is about stopping and stays true; the evidence is read and
   written on the card before the resume, which is what the move note
   already does.

5. **A test per cause.** A fixture lane whose scope journal says oom-kill is
   resumed on the next pass with the floor satisfied, and parked with the
   floor's numbers when it is not; a parked wall lane is resumed once its
   reset time passes; a lane that died twice of one cause within the
   horizon is parked and its card says what lifts the park; a lane whose
   turn finished is left alone.

## Depends on

Card #52. Without the resumed session running in the lane's own scope,
every resume this card adds rebuilds the daemon-scope pile that killed four
lanes in one second at 17:59Z, and the fix would make tonight worse, not
better. Land #52 first, or in the same lane.

## Rejected

- **Resuming without the gate.** A revived lane on a full machine is the
  next kill, and today the retry into the daemon scope made each kill take
  more than one lane. The floor and the placement rule already exist; the
  resume goes through them.
- **The owner's Resume click as the way.** Eight cards sat between 25
  minutes and six hours tonight, through a wall reset nobody was awake
  for. The door stays for a lane that ended by its own work; it is not the
  path for one the machine ended.
- **Unbounded retries.** The horizon and the once-per-cause count stay;
  what changes is that a park has an end the board reads.

## Loop

We think resuming machine-ended lanes under the gate will change the count
of Hello Revenue lanes sitting ended with nothing folded at the morning
read from eight toward zero, because every one of tonight's endings was
the machine's and every cause has an end the machine can read. Read at the
first morning after it lands, from the board's broken count and the card
histories. If lanes are resumed and die again of the same cause within the
horizon more than twice in a night, the gate is wrong and the memory-floor
card is the fix, not more retries. If cards still sit ended with a cause
the board did not name, item 3 is the gap.
