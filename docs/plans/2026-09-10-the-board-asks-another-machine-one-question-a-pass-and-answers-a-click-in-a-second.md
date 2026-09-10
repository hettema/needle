# The board asks another machine one question a pass, and answers a click in a second

**Carries:** docs/slice-suggestions/done/2026-09-10-the-board-asks-another-machine-one-question-a-pass-and-answers-a-click-in-a-second.md
**Status:** NEW — planned, not started; placed at the top of Up next on 2026-09-10 at the owner's word ("What do we need to fix to make the board run properly? Can you put those cards at the top of up next").
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

### 4. The measure is on the head
Every pass records four times — collection per machine, lock occupancy,
the first door's wait, the door's completed effect — and `needle beats
--last` prints them; the head shows the last pass's numbers beside the
machines line.
Done means: live, on a day with the rented machine on the board and
lanes on both, the head reads collection under ten seconds, the lock
under a second, and a click answered under a second; the loop below reads
the same.

## Acceptance criteria

- A click on any card is answered within a second while the board reads
  the rented machine, and while the rented machine is silent.
- One pass makes one wire call per other machine, whatever that machine
  holds.
- A machine that stops answering is shown with the age of its last
  reading, and its silence costs no other machine's lanes their pass.

## Rulings

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
