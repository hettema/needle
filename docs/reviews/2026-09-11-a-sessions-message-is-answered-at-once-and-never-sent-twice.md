# Review — a session's message is answered at once and never sent twice

**Plan:** docs/plans/done/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md
**Reviewer:** the build session (Claude Fable 5.1, then Claude Opus 5 after a usage-limit handoff on the same lane) for its own passes; Codex in a fresh read-only thread through `needle call codex --fresh` for the cold reads of another make
**Diff range:** d32e24f (`origin/develop` at the lane's rebase) .. the close commit that carries this record (the build f3664e1, pass 1's repairs d36792d and fb7a5ba)
**Findings:** 6 over pass 1
**Stop signal:** open — pass 1 found live behaviour inside the change (findings 1.1 and 1.3), so a clean pass is owed after its round is read cold.

## What was checked

- **The live stores.** A copy of the laptop's store (the board serves from the laptop; `needle.db`, 84 MB, alembic 0018) taken 2026-09-11 13:02Z: 49,938 hook events, 1,728 groups sharing a session, kind and second, 47,001 rows beyond each group's first. The rented machine's store is not the served one and was not copied.
- **The migration on that copy**, by opening it with this lane's `Store` (0019): 2,937 rows, 0 duplicate groups; no group's echoes differed in cwd, card, message, reason or error; the distinct histories before and after are equal row for row in first-seen order; 109 of 110 cards' event histories shrank (needle #109 from 8,162 to 39, #83 from 7,752 to 125, #110 from 5,729 to 48, Hello Revenue #456 from 4,129 to 118).
- **Two cards on the served board** (`/api/projects/needle/cards/109`, `/api/projects/hellorevenue/cards/456`, read 2026-09-11 before the fold): #109's lane said at 08:41:08Z "Card 109 is closed into Executed and folded…", #456's at 07:10:44Z "The questions are already written…"; each is the last Stop row the migrated copy holds for that card.
- **The queues**, read 2026-09-11: the laptop's `hook-queue.jsonl` held 285 events from 2026-09-09 21:38Z to 11:02Z; the rented machine's held 88 from 2026-09-10 15:59Z to 2026-09-11 11:00Z.
- **Tests**: the stall test (three posts answered under a second with the loops' lock held, one pass after the stall, the card "asking" after it, three fresh posts at most two passes, a re-sent batch answering zero new, the page woken from the loop's thread); the store test (a batch twice records once, answers zero, a later second counts one); the machines test (an event two hours old counted on either machine's line through the room read, a fresh one and an empty queue not); the head test (the count said on the machine's line and the line painted broken). Frontend 81 of 81, `tsc` clean.

## The passes

1. **The author's cold re-read of f3664e1, the three lenses in one pass.** Against the "done means": item 1's stall is the loops' lock held directly, since on the floor the fake `ssh` refuses a machine that is down at once and stalls nothing; the Met line says so. The seams: the store's read-then-insert left a race between two posts carrying one event to the unique index, whose refusal rolled back the whole batch and answered 500, so that hook kept its whole queue (finding 1.1, live); the head counted a queue the board never answered but painted the machines line broken only for a machine that did not answer (finding 1.2); moving the store write to a worker thread moved the page's wake and the directory-to-card lookup with it — the wake resolves futures that belong to the server's loop, and the lookup reads the projects the loop's own sync mutates (finding 1.3, live); the pass's own wakes already come from worker threads in the word read, the signal landing and the trunk levelling (finding 1.4, outside the change); a re-sent batch that recorded nothing still asked for a pass, which is the evening of echoes the plan exists to end (finding 1.5). The record: item 1's words name `host_down` for the stall (finding 1.6).

## Dispositions

### Pass 1's findings

1. [seam] Two posts carrying the same event at once raced the store's read to the unique index, and its refusal rolled back the whole batch, answering 500 — FIXED in d36792d; reaches every caller of `Store.record_hook_events` (only `Loops.hooks`), the other events in the same batch, and the migration's index, which is the one arbiter; assumes SQLite savepoints nest inside the session's `begin()` and a refused savepoint leaves the outer transaction usable, and that no writer other than this function inserts into `hook_events`.
2. [feature] The machines line counted a queue the board never answered but painted broken only for a machine that did not answer — FIXED in d36792d; reaches the head's machines line in `Board.tsx` and its test, and `describe_room` on the terminal, which says the count without a meaning; assumes the line is shown only when the board knows more than one machine, so a one-machine board shows no count (stated under *Not done*).
3. [seam] The store write's move to a worker thread moved `Live.bump` and the directory-to-card lookup with it — FIXED in fb7a5ba; reaches the page stream's waiters in `Live.wait_for_change`, `Live.sync_projects`' mutation of the projects map, and the stall test that now holds the wake's thread; assumes the server's loop thread is the only writer of `live.projects` and the only thread that resolves the waiters on this path.
4. [seam] The pass's own wakes in the word read, the signal landing and the trunk levelling come from worker threads — filed as docs/slice-suggestions/2026-09-11-the-boards-page-shows-each-change-as-it-happens-whichever-part-of-the-board-noticed-it.md
5. [feature] A re-sent batch that recorded nothing new still asked for a pass — FIXED in fb7a5ba; reaches the stall test's three pass counts, the timers and the registry watcher, which still run passes on their own beats; assumes every event the store holds had a pass asked when it was first recorded, which holds because the ask follows every write that recorded something.
6. [record] Item 1's words name `host_down` for the stall where the test holds the lock — NO CHANGE: the Met line states the method and why the lock is what the intake waited behind either way.

## What the build learned the plan got wrong

- The plan counted 1,582 duplicate groups on 2026-09-10; on 2026-09-11 13:02Z the laptop's store held 1,728 over eight days, the most on 2026-09-10 (279 groups, 33,603 rows beyond the first).
- Item 1's `host_down` does not stall a pass on the floor: the fake `ssh` exits at once.

## Not done, stated

- A one-machine board shows no machines line, so its queue count is not on the head; the board today knows two machines. Adding the line for one machine would change the face #83 promised not to change on a one-machine board.
- "The same event" is a session, a kind and the second the hook stamped: two events of one kind from one session inside one second are held as one. A turn takes longer than a second, so two Stops cannot; two SessionStarts inside a second would.
