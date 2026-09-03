# Needle — the founding intent

**Written:** 2026-09-03, by the owner and the coordinating session, the evening
the first board (Needle 0.1, inside the Hello Revenue repository) needed its
ninth fix of the day. This document is the fixed point of the project. Plans
are our best thinking about how to serve it; code is the current attempt.

## The fact this project is built on

Hello Revenue, the first project on the board, is developed by writing plans
and executing them: 508 plans, 1.56 million words of them, and 2.5 million
words of written record in five months. The developers are AI sessions, each
arriving with no memory of the last. The plans are excellent. The bottleneck
was the owner: every plan, its status, its dependencies and what could run
beside it lived as a map in one person's head. The first board was born to
take that map out of his head. It worked well enough to prove the idea and
badly enough, as a runtime, to be rebuilt from scratch.

**Needle is the map over a corpus of plans.** A plan is the substance of a
card. A card is a view onto a plan, plus the three things a plan cannot hold:
its position among everything else, what is happening to it right now, and
the owner's rulings on it. Any project that writes plans this way can be on
the board. Hello Revenue is the proving ground, not the owner.

## The intent, in the owner's words

**The board is the shared memory of a team that has none.** The team is the
owner plus a rotating set of skilled developer sessions. The board is the one
thing every member reads and writes, so it has to be true at every moment.
That sentence is the test for every mechanism the project will ever grow: it
stays if it keeps the board true.

**The owner's side.** He manages priorities, not tasks. The board is where he
runs an agile team at the best possible scale.
- Everything on the plate, at once, ranked. Position is priority, column is
  status, and both are true.
- Any card opens to its intent, its essence, its core points and its record,
  without reading code.
- He can clarify a card, discuss it, answer its question, or step into its
  running work at any point. A card can message him; he can step into its
  terminal and give feedback there, and leave without ending anything.
- He sees the flow of work: what is blocking what, where the bottlenecks are,
  what can run concurrently and what cannot, so he never starts work that
  makes other work harder.
- The strongest model does the work, across every subscription he holds,
  with no management on his part.

**One move is his; every other move is teamwork.** He decides what enters
execution. Everything else — into Executing when hands are on it, out of it to
where the work says, on to Done when the signal arrives — belongs to the team,
machine or session, and he watches it happen. A board he has to move by hand
is a board that lies while he is away.

**Done is a closed loop, not a claim.** Built work waits for the signal that
says it delivered. The owner cannot always close that loop himself, so a card
enters the waiting column with its signal named, and the board or a session
reads the signal and moves it on. Nowhere on the board is a place where cards
go to be forgotten.

**The developers' side.** A session reads its card as the brief and writes its
outcome back, so the next session and the owner see the same true state. A
session never reconstructs what happened from git or from memory.

**The coordinator's side.** Keep the board true, keep lanes from colliding,
keep work on the strongest model, and say what the board cannot show.

## What 0.1 taught

Nine fixes in one day, every one of them in the half of 0.1 that ran things
rather than the half that showed things. The lessons, carried as principles:

1. **The board reads what runs. It never is the thing that runs.** 0.1 spawned
   lanes from its own process, so every restart of the board killed every
   lane; it opened windows by waiting on the terminal and killed them when the
   wait timed out; it kept one session registry per subscription and lost
   sight of lanes it had moved. Launching, choosing the model across
   subscriptions, listing every session as one list, opening a window into
   any of them: that is a runtime service. The board talks to it; the owner's
   own terminals can use it too.
2. **True without anyone remembering.** Executing is a machine fact, observed
   from real sessions and real worktrees. Shipped means archived. A ruling is
   durable the instant it is made. Nothing on the board is set by hand except
   the owner's own priorities and his gate on entering execution.
3. **Sessions push; the board never polls a session.** A hook at session
   start, stop and end writes to the board. A poll that "opens terminals and
   raises toasts" as a side effect of a read was 0.1's deepest trap.
4. **Concurrency is visible before Start.** A plan declares what it touches; the
   board shows which cards can run beside which, and refuses a collision
   unless the owner overrides it with the reason in front of him.
5. **A door either opens and proves it, or says why not.** Every door the
   board offers verifies its effect by positive evidence and fails loudly.
   Silence was how 0.1 ate the owner's typed idea while toasting success.
6. **The model rule is one function.** Strongest model wherever it runs; the
   next model down only when the top one is exhausted on every subscription.
   Two choosers in 0.1 gave two answers and the owner could not tell which
   one Start obeyed.
7. **Its own tests are the specification.** 0.1's 8,800 lines of tests are the
   record of every trap it fell into. They carry over as scenarios; no code
   does.

## What Needle is not

- Not a task tracker. If a card has no plan or written suggestion behind it,
  it is a note, and the board says so.
- Not the runtime. See lesson 1.
- Not a team tool for humans. One owner, many sessions. Multi-user is not a
  goal and must not shape the design.
- Not enterprise software. Clean, typed, ratcheted, and small enough that a
  session arriving cold extends it the way the last one did.

## How the project is built

Needle is built the way Hello Revenue is built, because that method is what
the board exists to serve: intent first, a written plan per slice with an
effort gate, execution in an isolated lane, a review before anything is called
done, ratchets for every boundary that matters, one way to do each thing. The
project's `CLAUDE.md` carries the working rules; `docs/plans/` carries the
slices, with the folder as the status.

## Sequence

1. **The map** — the kanban over a project's plans, with the owner's moves,
   card detail, and the first project (Hello Revenue) on it read-only from
   its written record. `docs/plans/2026-09-03-01-the-map.md`.
2. **The runtime** — sessions as one list across subscriptions, the model
   rule, launching a lane in its own scope, a window into any session that
   the owner can close without ending it.
3. **The doors and the loops** — Start, Discuss, Answer, Watch; the machine
   moves; the done signal read and acted on.

Needle replaces 0.1 for Hello Revenue when the third slice lands. Until then
0.1 keeps running and every lesson it teaches is added above.
