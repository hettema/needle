# The board asks another machine one question a pass, and answers a click in a second

**Carries:** docs/slice-suggestions/done/2026-09-10-the-board-asks-another-machine-one-question-a-pass-and-answers-a-click-in-a-second.md
**Status:** SHIPPED — built, reviewed once by Codex (call 105; seven findings, all fixed and each verified by a test), verified by the full suite (767 passed) on the rebased tree, and folded on 2026-09-11 by the lane on card #123 (Claude Fable 5.1, then Claude Opus 5 after a usage-limit handoff); review record `docs/reviews/2026-09-11-the-board-asks-another-machine-one-question-a-pass.md`. Started 2026-09-11; placed at the top of Up next on 2026-09-10 at the owner's word ("What do we need to fix to make the board run properly? Can you put those cards at the top of up next"). The board's home changed the morning this started (card #83's plan, Rulings, 2026-09-11 morning: the board goes to the rented machine for good after this card).
**Written:** 2026-09-10, from Dennis after three hours with the board on the rented machine: "The intent is for the needle board's UX to be just like it used to when it was only on my laptop", and that evening, "lets go with your rec" — the board back on the laptop, the rented machine the horsepower, and this the next slice. The shape is Codex's reading of the representation (card #83's review record, fourteenth pass), adopted the same evening.
**Effort gate:** high — the mechanics are one new verb on the machine side and one collector on the board's, beside the per-verb reads that exist (`runtime/remote.py`); the judgment is what runs under the loop's lock and what never does, which decides whether a click can be answered while a machine is silent, and is settled in the rulings below.
**Sequencing:** none. Shares `api/loops.py` with the plan that answers a session's message at once; the fold settles it.
**Class:** the head shows, per pass, how long collection took, how long the lock was held and how long the first click waited; a pass that holds the lock for seconds is loud where the owner looks, and the loop below reads the numbers daily.

## Intent

The board reads a machine that is not its own by asking that machine's
own `needle` — one question per lane per pass, each a second over the
wire, all under the one lock every click on a card takes. With the board
on the rented machine and a hundred lanes on the laptop a pass took a
minute per project and the owner's Watch on a card waited minutes behind
it; with the board back on the laptop and one lane on the rented machine
a pass takes 26 seconds and every click waits for it. The wire's cost is
the number of lanes on the other machine, and the lock's cost is every
door. After this plan the board asks each other machine one question a
pass, outside the lock, keeps the last answer warm, applies it under the
lock in a moment, and a click on any card is answered within a second
whether or not a machine is silent.

What does not change: the two rulings of card #83. Another machine is
asked through its own `needle` over ssh, and the board's store is the one
record. And the board stays where the owner ruled it: on the laptop.

## Items

### 1. One question a pass: a machine answers everything the board asks in one batch
A machine-side verb (`api/runtime_cli.py`; the reading is one typed
observation in `domain/machine.py`) answers, for the projects and lanes
the board names, what the per-verb reads answer today — lean sessions,
the boots, the room with its hold, and per lane its tip, its edits, its
plan and review documents, its dispatches and its transcript size — in
one reply. `runtime/remote.py` asks it once per pass and reads the reply
into the same types the per-verb reads return, so nothing downstream of
the reads changes; the per-verb reads stay for the doors that need one
answer now (a push, a level, a window).
Done means: on the fixture with three lanes on the other floor, one pass
makes one ssh call for the reads (the fake's `ssh_calls`, counted), and
the board's state for those lanes equals what the per-verb reads gave
before; a machine whose `needle` is older than the verb is read the old
way and the machines line says it is behind.
Hands out: search — every wire read a pass makes today, with the file and
line that calls it and the type it returns; verifies against
`runtime/remote.py` and the fixture's `ssh_calls` on one pass before the
verb's shape is fixed.
The search (2026-09-11, read in the lane and proven on the fixture: one
pass with three lanes on the other floor, ten ssh calls, 12.8 s on the
floor where each call is a `needle` start-up): `sessions --lean`
(`runtime/service.py::sessions`, `list[Session]`), `boots`
(`Runtime.boots`, `list[Boot]`), `where` (`Runtime._where_on` for the
placement, `Where`, once per project), `worktrees <repo>`
(`Runtime.worktrees`, `Checkouts`, once per project), `tip <repo>
<branch>` (`Runtime.branch_tip`, `LaneTip`, once per lane),
`scopes --held` (`Runtime._scopes`, `list[ScopeHeld]`), `sessions --lean`
again (`Loops._tend_calls`), `room --hold` (`Runtime.rooms`, `Headroom`),
and per lane with hands on `edits <checkout>` (`Runtime.edits`, `Edited`)
and `lane-docs <checkout> --plan …` (`Runtime.lane_docs`, `LaneDocs`, and
once more with `--reviews` once every item is met). Every one is a method
of `runtime/remote.py::Remote`. Not a pass's read: `dispatches` (the Start
door's brief, `api/doors.py::handouts_row`) and `transcript-size` (a
terminal verb), so those two stay per-verb and the observation does not
carry them. Also found: the desktop's compositor is asked (`hyprctl
clients` over ssh, `runtime/windows.py::reconcile`) inside every
`sessions()` read when the screen is on another machine — three more
wire calls a pass once the board is on the rented machine — so the
observation carries the desktop's open window addresses too.
**Met:** `tests/runtime/test_one_question_a_pass.py::test_one_pass_asks_the_other_machine_once_and_reads_what_the_verbs_read` — three lanes on the other floor, the third pass makes one ssh call (`observe --ask -`), and each lane's state, machine, path, session, edits and tip, the rented machine's sessions, its boots and a slot's limits equal what the same board read one verb at a time gives; `tests/runtime/test_one_question_a_pass.py::test_a_machine_whose_needle_predates_the_question_is_read_the_old_way_and_said_behind` — a `needle` that refuses `observe` (exit 2) is read verb by verb and the machines line says its needle is behind, on the head and in `needle machines`. `dispatches` and `transcript-size` stay per-verb: neither is a pass's read.

### 2. Collection runs outside the lock, per machine, and the last answer stays warm
The loop (`api/loops.py`, `reconcile` and `level_trunks`) collects each
machine's observation outside its lock, one machine never waiting on
another, and applies the newest accepted observation under the lock in
one step. A machine that does not answer leaves its last observation
standing, with its age on the machines line and on each of its lanes'
cards, and the board's own machine is read as it is today.
Done means: on the fixture with the other floor down (`host_down`), a
pass on the board's own lanes completes in the time it took with one
machine, the other machine's lanes show their last reading with its age,
and no door on any card waits on the wire; when the floor answers again
the next pass reads it.
**Met:** `tests/runtime/test_one_question_a_pass.py::test_a_silent_machine_keeps_its_last_reading_with_its_age_and_nothing_waits_under_the_lock` — the other floor down: its last observation stands, it reads unread, its room carries its age on the head and in `needle machines`, each of its lanes says "As rented last answered, N ago" and stays hands on, the apply asks no machine, and the floor back up is read fresh on the next pass; `tests/runtime/test_one_question_a_pass.py::test_the_boards_own_lanes_are_applied_while_another_machine_is_slow` — with the other floor answering in six seconds, the pass returns once the board's own machine is applied, under five seconds, without the rented machine's answer. Measured as not waiting on the other machine, not against a one-machine timing.

### 3. Nothing that waits on another process runs under the door lock
Every wait the lock covers today — ssh, git fetch and levelling, registry
and transcript walks — runs outside it, and the lock holds only the
board's own bookkeeping. A door records the request, acts on the one
session it already knows outside the lock, and records its proof; what
must not race — the dial's count, a lane coming back, a stop — is
serialised per card, not board-wide.
Done means: on the fixture the lock is held under a second per pass with
two machines and thirty lanes (measured by the pass itself, item 4); a
Watch on a card of the board's own machine is answered while the other
floor is stalled for 45 seconds.
**Met:** `tests/runtime/test_one_question_a_pass.py::test_the_lock_is_held_under_a_second_a_pass_with_thirty_lanes_on_two_machines` (the beat's own lock time, fifteen lanes a floor); `tests/runtime/test_one_question_a_pass.py::test_the_apply_starts_no_process_and_asks_no_machine`; `tests/runtime/test_one_question_a_pass.py::test_a_stop_on_either_machine_is_on_the_card_and_its_ending_is_named_outside_the_lock`; `tests/api/test_a_click_waits_on_no_machine.py` — a Watch on a card of the board's own machine answers, its wait for the lock under a second, while the other floor is stalled (eight seconds on the fixture; the mechanism does not depend on the length). **Deviated:** the per-card serialisation is not built and acts stay under the one lock — Rulings, "Doors keep the board's one lock" and "The fold proofs and the stable branch are proved outside the lock".

### 4. The measure is on the head
Every pass records four times — collection per machine, lock occupancy,
the first door's wait, the door's completed effect — and `needle beats
--last` prints them; the head shows the last pass's numbers beside the
machines line.
Done means: live, on a day with the rented machine on the board and
lanes on both, the head reads collection under ten seconds, the lock
under a second, and a click answered under a second; the loop below reads
the same.
**Met** in the lane for the measure: every pass records collection per machine, the lock, and the first door's wait and effect (the beats table, migration 0019), `needle beats --last` prints the newest pass and the last click's verdict (`tests/runtime/test_one_question_a_pass.py::test_the_last_pass_says_whether_its_click_was_answered`), and the head shows the last pass beside the machines line. **Deviated:** the live numbers on a day with lanes on both machines cannot be read inside the lane; they are the Loop below and the card's WATCH row after the fold.

## Acceptance criteria

- A click on any card is answered within a second while the board reads
  the rented machine, and while the rented machine is silent.
- One pass makes one wire call per other machine, whatever that machine
  holds.
- A machine that stops answering is shown with the age of its last
  reading, and its silence costs no other machine's lanes their pass.

## Rulings

- **The board's own machine is observed by the same function the verb
  runs, outside the lock, and every read the pass makes answers from the
  standing observations** (the lane's ruling, 2026-09-11, on item 3's
  "registry and transcript walks"). Rejected: observing only the other
  machines and reading this one live under the lock — the registry walk
  and the codex rollouts on a laptop with a hundred lanes are seconds,
  and they would be the lock's. A door's re-read after its act refreshes
  this machine's observation locally and applies; another machine's
  session the door just started is put into that machine's standing
  observation by the runtime at the launch, so the door sees it at once
  and the next pass's answer replaces it.
- **The question names what the board knew when it asked; a lane first
  seen on a pass is asked about from the next** (the lane's ruling,
  2026-09-11). The pass asks before it applies, so a worktree that
  appears between passes has no tip, edits or documents asked for on the
  pass that finds it, and its group is read by name one pass later; on
  the board's own machine its tip and edits are read locally that once.
  Rejected: reading the newcomer under the lock — that is a process under
  the lock item 3 removes — and asking every worktree on disk by name,
  which on the laptop is a hundred groups a pass to catch a lane in its
  first thirty seconds, when a group nobody has put the lane in yet holds
  nothing. The room the pass shows is likewise the one read before its
  moves, so a memory a stop in the pass gave back is on the head from the
  next pass. The ask travels on standard input, since it names every
  lane on the machine and one argument stops at 128 KB (card #83's first
  live move).
- **A machine that never answered is an empty observation marked unread,
  never a fall-through to the wire** (the lane's ruling, 2026-09-11).
  Rejected: reading the old way when no observation stands — that is the
  wire under the lock on the first pass a machine is down, which is the
  minute this plan removes.
- **A pass applies once; what the timer, the registries, a hook and a
  corpus change wait for is the board's own machine, and a machine the
  pass does not wait for is applied when its answer lands** (the lane's
  ruling, 2026-09-11). Rejected, first: a pass that asks every machine and
  applies once all have answered — a stalled machine then holds the
  board's own lanes for its whole deadline, forty-five seconds, which is
  item 2's done-means broken with the doors free. Rejected, second: a pass
  that applies every answer as it lands, re-applies after re-asking a
  machine and again after naming an ending — the suite showed what counts
  "once a pass" breaking: a card moved before its ending was named, a
  group's note said on the pass that asked, a handoff's expiry said twice.
  A machine is never asked twice at once; an answer to a question that
  went out before the pass began is taken without an apply and the machine
  is asked again; an answer to an older question never replaces a newer
  one; and the endings the apply will name are asked outside the lock
  before it. The first read and the tests wait for every machine.
- **A door applies what stands with its own act in it, and a pass
  follows** (the lane's ruling, 2026-09-11, on the lock probe below).
  Every act the runtime makes — a launch, a stop, a move, a resume, a
  session put back in its group — is written into that machine's standing
  observation as it lands, so the door's apply shows it without reading
  any machine, and a pass reads every machine right after without the
  door waiting. Rejected: the door re-reading its own machine under the
  lock, which is the registry walk and a git read per lane — the wait
  item 3 removes. A terminal verb, with no loop, still asks every machine
  and waits.
- **The fold proofs and the stable branch are proved outside the lock**
  (the lane's ruling, 2026-09-11). The probe on the fixture (thirty lanes
  on two floors): the apply held the lock 0.49 s and started thirty
  processes, every one `git rev-parse` for a lane's fold proof; the rest
  was the store's own writes, which is the bookkeeping the lock is for.
  The pass now proves each recorded tip before it takes the lock and the
  apply looks the proof up; a tip the apply records first is proved on
  the next pass. The trunk loop proves the stable branch with its fetch.
  A terminal verb proves as it reads, so a close right after a fold
  still sees it. The same holds for why a session ended — the journal and
  the transcript of the machine it ran on, over the wire for another —
  which the apply queues and the next pass asks before the lock, so an
  ending is named a pass after it is found; and a parked lane's limits
  come from each machine's answer, which carries every subscription's
  last reading. What stays under the lock is an act the pass itself
  makes — a launch, a stop, a move, a notice, a group ended — which is
  rare, and the beat's numbers say when one was slow.
- **Doors keep the board's one lock; the per-card serialisation of a
  door's act is not built here** (the lane's ruling, 2026-09-11, on the
  third ruling below). With every read outside the lock, what a door
  waits on is another door's act — a Start's launch window, fifteen
  seconds — never a pass; the beat's door numbers (item 4) say how often
  that happens, and the loop below decides whether it is worth its own
  slice. Rejected for now: a lock per card taken by the doors and the
  pass's per-card acts alike — every act in `api/loops.py` and
  `api/doors.py` would take one, forty places, on no evidence yet that a
  door waits on a door.

- **Pull, one question, from the board.** Rejected: each machine pushing
  its observation to the board on its own clock. The board's beat is the
  one clock the dial and the rescues read, and a machine that pushes
  needs the board's address and its timing, which the tunnel end already
  costs one machine a sudo line; a pull keeps the machine answering its
  own `needle` as the ruling says.
- **The last answer stands, with its age.** Rejected: a machine that does
  not answer reads as empty. Empty is what the board showed for a lane
  whose machine was slow this evening, and empty moves cards; an old
  reading with its age moves nothing and says why.
- **Per-card serialisation, not the board-wide lock.** Rejected: keeping
  the one lock and making the reads faster. Reads over a wire will be
  slow again on the day a machine is far or full, and every door behind
  one lock pays for it; the lock's job is the board's own bookkeeping.

## Deliberately not

- The session's message and its answer (the plan that answers it at
  once): that intake changes there.
- Windows and focus over the wire: proven on card #83 and unchanged.

## Loop

We think one question a pass outside the lock will answer every click
within a second on a two-machine board, because the wire's cost was the
number of questions and the lock's cost was carrying the wire. If the
head shows the lock held over a second, or a click waiting longer, on
any day with both machines on the board, the wait is a process under the
lock item 3 missed — and it is named by the pass's own numbers.

Loop: the last pass answered its first click within a second — command uv --project /home/dennis/Work/needle run needle beats --last expect answered by 2026-09-24 every 1d
