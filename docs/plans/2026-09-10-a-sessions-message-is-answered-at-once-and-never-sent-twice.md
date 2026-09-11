# A session's message is answered at once and never sent twice

**Carries:** docs/slice-suggestions/done/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md
**Status:** EXECUTING — the lane on card #124 (Claude Fable 5.1, on the rented machine) since 2026-09-11; placed at the top of Up next on 2026-09-10 at the owner's word ("What do we need to fix to make the board run properly? Can you put those cards at the top of up next").
**Written:** 2026-09-10, from Dennis on the first evening a lane ran on the rented machine: "The hooks don't work because of long round trips? What does that mean and does it make the board dumb too? What do we need to fix to make the board run properly?" The finding that answered him is the carried suggestion: the hook waits two seconds for an answer the board sends after a 26-second pass, so the answer never arrives, the queue never empties, and every firing re-sends a day of events the board already holds.
**Effort gate:** medium — the mechanics are a reorder in one endpoint (record, answer, then the pass) and a uniqueness the store already has the columns for; the judgment is what "the same event" means and that the pass a post causes still runs, once, and is settled here.
**Sequencing:** none. Shares `api/loops.py` with the plan that asks another machine one question a pass; the fold settles it.
**Class:** the queue file beside the store on each machine is the trace — empty when the board answers, growing when it does not — and the loop below reads it daily.

## Intent

A session tells the board what happened through its hook, and the board
is meant to hear it within the two seconds the hook waits (plan 10, item
1). Today the board answers only after the whole pass the message causes,
which is 26 seconds with a hundred lanes and a second machine, so no hook
has heard an answer in a day: the laptop's queue holds 263 events reaching
back 21 hours, each firing re-sends them all, and the board records the
batch again while it runs another pass. The board did not lie — a post the
hook gave up on is finished by the server, and every queued event was in
the store — but it spent the evening answering echoes. After this plan a
message is recorded and answered in milliseconds, the pass it causes runs
after the answer and once, the same event is never held twice, and both
machines' queues are empty.

What does not change: the hook's two seconds. A session is never slowed by
its board, so the board gets faster rather than the hook more patient.

## Items

### 1. The board answers a message before the pass it causes
The intake (`api/app.py`, the `/api/hooks` endpoint; `api/loops.py`,
`Loops.hooks` and `reconcile`) records what was posted and answers with the
count at once; the pass runs after the answer as the loop's own work,
coalesced — however many posts arrive while a pass runs, one more pass
follows it, never one per post. A post that arrives while no pass runs
starts one.
Done means: on the fixture, a post is answered in under a second while a
pass is stalled behind the other floor not answering (`host_down`), and the
board's state shows the posted event after the next pass; three posts in a
row cause at most two passes.
**Met:** `tests/api/test_doors.py::test_a_post_is_answered_while_a_pass_is_stalled_and_the_passes_it_causes_coalesce`
— with the loops' lock held as a pass in flight holds it, three posts are
each answered in under a second, cause one pass once the stall lifts, and
the card reads "asking" after it; three fresh posts cause at most two
passes. The stall is the lock held directly, not `host_down`: on the
fixture the fake `ssh` refuses at once, so a machine that is down stalls
nothing there, and what the intake waited behind was the lock either way.

### 2. The same event is held once
The store (`infrastructure/store.py`, `record_hook_events`; a migration)
keeps one row per session, kind and moment: a re-sent batch records only
what is new, and the migration folds the day's echoes — 1,582 groups on
2026-09-10 — to one row each, keeping the first. The intake's answer counts
what was new, so a hook that re-sends sees a small number and a session
that posts fresh sees its count.
Done means: posting one batch twice records it once and the second answer
counts zero new; the migrated store has no two rows with the same session,
kind and moment, and every card's history reads as before.
Hands out: execution — the count of duplicate groups before and after the
migration on a copy of the live store, and the card whose history changed
if any did; verifies by reading two of those cards' histories on the
served board before the fold.
**Met:** `tests/infrastructure/test_store_doors.py::test_the_same_event_posted_twice_is_held_once_and_the_second_answer_counts_nothing`
and migration 0019 on a copy of the laptop's live store taken 2026-09-11
13:02Z: 1,728 duplicate groups before (49,938 rows), 0 after (2,937 rows);
no group's echoes differed in content; the distinct histories before and
after are equal; 109 of 110 cards' histories shrank, needle #109 most
(8,162 rows to 39). Read on the served board before the fold: #109's last
word (08:41:08Z, "Card 109 is closed into Executed and folded…") and
Hello Revenue #456's (07:10:44Z, "The questions are already written…")
are the copy's last Stop rows after the migration.

### 3. Both machines' queues drain, and the hook says when they do not
With item 1 the hook's drain (`hooks/needle_hook.py`, `drain`) hears its
answer and empties the queue; the loop below reads the file. A queue that
holds an event older than an hour is a finding the head can show — the
count per machine on the machines line — so the day this happened again
would be loud where the owner looks.
Done means: live, the queue file beside the store on the laptop and on the
rented machine is empty a minute after the fold; on the fixture a queue
with an old event is counted on the machines line and an empty one is not.
**Met:** `tests/runtime/test_machines.py::test_a_queue_holding_an_event_older_than_an_hour_is_counted_on_the_machines_line`
— on the two-machine floor an event two hours old beside either machine's
store counts one on that machine's line, a fresh one and an empty queue
count nothing, read through the same room read the head uses. The hook
itself is unchanged: its drain already empties the queue on a 2xx. The
live half — both queues empty a minute after the fold — is read at the
close and written in the review record.

## Acceptance criteria

- A session's hook hears an answer within its two seconds on either
  machine while the board reads a hundred lanes and a second machine.
- The store holds one row per event, and a card's history shows each
  turn once.
- Both queues are empty a minute after the fold and every day after.

## Rulings

- **The answer before the pass, never a longer wait.** Rejected: a longer
  timeout in the hook. The intent is a session never slowed by its board;
  a hook that waits thirty seconds slows every tool call thirty seconds
  the day the board is slow.
- **Kept once by the store, not by the hook.** Rejected: the hook
  remembering what it sent. A hook that dies mid-send would forget, and
  the board is the one record; the store's uniqueness holds whoever
  posts.

## Deliberately not

- The pass's own length: the plan that asks another machine one question
  a pass owns it.
- The word the hook reads back for a running lane (plan 10's `word`):
  unchanged.

## Loop

We think answering before the pass will empty both queues and keep them
empty, because every queued event was one the board had already finished
recording when the hook gave up. If the queue on either machine holds an
event older than an hour on any day, the answer is still behind something
that waits — item 1's coalescing is what changes.

Loop: the laptop's queue beside the store is empty — command sh -c 'test -s /home/dennis/.local/share/needle/hook-queue.jsonl && echo waiting || echo drained' expect drained by 2026-09-24 every 1d
