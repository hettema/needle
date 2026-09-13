# Review — Colleagues ask each other for help without disturbing each other's work (#137)

**Plan:** docs/plans/done/2026-09-13-colleagues-ask-each-other-for-help-without-disturbing-each-others-work.md
**Reviewer:** session 2347a739 (Claude, opus on armana), an ended reading session on card #69 with no part in this change, called warm through `needle call` as call 125; its answer is `/home/dennis/.cache/needle/notes/from-2347a739-re-137-cold-read.md`, and the note it read is `/home/dennis/.cache/needle/notes/137-cold-read.md`
**Diff range:** e007dfb..37923a9 reviewed; repaired in 3317264
**Findings:** 6 — 3 demonstrated defects (all repaired), 3 hypotheses (all ruled on, no change). Finding 6 was found by the lane's own live verification after the fold, not by the reader.
**Verification:** the four states item 3 names, run against the entry and exit readers before and after and quoted verbatim below; the full backend suite module by module on 3317264; `npx tsc --noEmit` and `npx vitest run` in `frontend/`
**Completion:** all three demonstrated findings are repaired inside the change, with a test each that fails on the old behaviour; the three hypotheses are answered with evidence and a written reason, two of them now stated in the code where the next session reads them. One promise is met narrower than the plan wrote it and says so: the note reaches a colleague on the board's own machine, and a note handed from any other machine is refused at the door by name rather than lost — the capability behind it is card #83's and is filed. Nothing else is open.

## Dispositions

1. [feature] `board/lane.py:217` (`elsewhere`, the open-call branch) — the reader
   demonstrated that reading *every* open call as an absence inverts the card's own
   promise. A call that resumed a colleague did take it away; a call that handed it a
   note took nothing away — that path resumes nothing and stops nothing, and the
   colleague reads the note inside the turn it is already having, on its own card. With
   a live session mid-turn in its own worktree and a handed note against it, the real
   `lane_for` answered `state=ended`, `session=None`, `away='… is answering a call from
   #9'`, and the face read "nothing is working on it" about a card that was being worked
   on — the lie of #135 and #82 the other way round, entering through the door this card
   built. Its own headline test (`tests/api/test_calls.py`, a note to a lane that is
   mid-turn) was green because nothing asked what that lane's card said afterwards.
   **FIXED in 3317264:** only a call with `handed_at is None` counts as taking a
   colleague away. Picked up or not, a note leaves the colleague where it is, so the
   discriminator is `handed_at`, not whether the call is open. The ratchet's call arm now
   says "a call that took it away", and a new arm,
   `tests/ratchets/…::test_a_note_handed_to_a_colleague_moves_nothing_about_the_card_it_is_working_on`,
   holds the other half: the lane's whole sentence must equal what it would say with no
   call at all. That arm fails on the reviewed revision.
2. [feature] `api/loops.py:764` (`word_now`'s early return) — when this pass's snapshot
   held no lane for the card the directory named, the function returned before the block
   that appends the notes handed to the session, so the session's own address was dropped
   and the note was neither delivered nor stamped, while `needle call` had already
   reported it handed over. Reachable transiently after a board restart, and permanently
   for a colleague sitting in a directory that looks like a lane whose card is gone.
   The reader read the control flow and did not build a live `Loops`; I did.
   **FIXED in 3317264:** the early return carries the handed notes. `tests/api/test_calls.py::test_a_note_reaches_its_colleague_even_where_the_board_holds_no_such_lane`
   drives the served board with a colleague in `…/worktrees/card-4242-a-card-that-is-gone`
   and fails on the reviewed revision.
3. [record] `api/loops.py::notes_handed_to` and `infrastructure/store.py::pick_up_call`
   stamp the note picked-up *before* the words leave, and the hook that carries them has
   half a second and swallows every failure — so a read cut off after the stamp loses
   that note for good, and item 5's "a note picked up stops being shown as standing"
   reads as a guarantee the mechanism does not have. **NO CHANGE to the mechanism, and
   the reasoning is now written at both halves of it:** said once and possibly lost beats
   said twice, because a note reads as an instruction and a colleague that acts on the
   same question twice is worse than one that never sees it, and the caller holds the
   answer file either way and can ask again. The reader agreed the trade is defensible
   and objected to its silence, which is §4's objection and the right one.
4. [seam] `board/lane.py` — two orderings the reader asked me to rule on rather than
   guess at. (a) The away branch sat above every sentence the ENDED branch composes, so
   an away lane lost its fold and park sentences. **CHANGED in 3317264:** it now keeps
   what the work already landed ("its work landed on the shared branch and nothing is
   working on it: …") and carries the park as its `then`, because what landed is a fact
   about the card and not about where its session is sitting. (b) `exit_for`'s away
   return sits below the close-landed branch but above `if folded:`, so a folded,
   unwritten-up lane whose session is lent out is held in Executing instead of parked
   under "the work folded into origin/develop, but no session wrote it up".
   **NO CHANGE, deliberate, and the reason is now in the code:** that lane has a live
   session that is coming back to write it up, so the sentence would be true only by
   accident; the hold lifts by itself when the call ends; and a close that landed is the
   one fact above the line because it is finished work whoever is sitting where. That
   false sentence on a shipped card is exactly what #135 and #82 complained of.
5. [seam] `api/loops.py::_tended_elsewhere` collects `lane.session.session_id`, and an
   away lane has none, so a wall on a lent-out colleague is moved by `_tend_calls` as "a
   colleague that is nobody's" rather than by the lane loop. **NO CHANGE:** plan 17's
   ruling 5 asks for exactly one hop by exactly one mover, and that still holds — the
   lane loop's recovery needs `lane.session`, which an away lane does not have, so the
   two movers cannot both fire. The owner of the move changed; the number of movers did
   not. The reader reached the same reading and did not call it a defect.

6. [feature] `runtime/service.py::call` — found by this lane's own live verification of
   the shipped change, on the real board, 2026-09-13. A note handed on a machine the
   board does not serve from is recorded, waited on, and never delivered: `needle call`
   is a runtime verb and runs where it is typed, so its row lands in that machine's
   store, while the word that carries a note is served by the board from its own
   records. Demonstrated by handing a note to card #139's session from the rented
   machine minutes after the fold — `needle wait 127` reported "handed over … has not
   been picked up" correctly, the board's head stayed empty through two beats, and the
   stores said why: rented held calls 125 and 127, the board's store on the laptop held
   nothing past 93, and the address every rented session's hook uses is
   `needle-tunnel.socket` proxying to that board. Every lane on this project runs on
   rented, so this is not an edge. It violates item 4's own words: a colleague that
   cannot be reached is refused at the door, "with no row written and nothing
   half-sent". **FIXED in the same lane, to the floor the plan set:** the door now
   refuses a note it cannot carry, naming the machine the board serves from and what to
   do instead, reading the fact from the one place that already holds it
   (`runtime.machine.board_elsewhere`, which is how every board verb is routed);
   `tests/runtime/test_calls.py::test_a_note_that_no_board_here_can_carry_is_refused_at_the_door`
   holds both sides. **FILED, because the capability is not this change's:** a call that
   is one row wherever it is made belongs with card #83's item 4, which must answer the
   same question for the warm call and for the note's files —
   `docs/slice-suggestions/2026-09-13-a-note-reaches-a-colleague-whichever-machine-either-of-you-is-on.md`.
   The lane's own note to #139 is withdrawn on the watercooler, with the line it carried
   said there instead, so nobody waits on a note that cannot arrive.

Also recorded from the same read, as facts rather than findings: `started_on` written
once and never over across every fork site (checked site by site, including the Codex
resume that used to overwrite it, and migration 0025's nullable columns with no
backfill); the reordered refusals in `runtime/launch.py::call` losing none and
duplicating none; `judge` giving the wait and the loop one answer, with a gone process
still ending a standing call; `Word.card_number` optional with no downstream assumption;
and item 1's **Deviated** stance verified independently — `grep -rn
"session_slot\|SessionSlot" api/ board/ hooks/ tools/` is empty on this revision, so the
close's cold-reader check that card #115 named really is gone from today's code and that
half of the done-means has no live subject.

## Verification evidence

**The four states, item 3's hands-out, run against `should_enter_executing` and
`exit_for` on a test board built from `tests/board/test_lane.py`'s own helpers.** The
script is `four_states.py` in this session's job tmp; each state names a closed card
(#123's shape: DELIVERED written, plan archived, work folded) and one session in its
worktree.

Before the change (e007dfb):

```
1. closed card (Executed), its old colleague called away to read #80's work
    lane.state   working
    sentence     Happening now: a session is working on it, opus on gmail, for 20 min.
    enter        hands on: 8d7fb4a3 on gmail in card-123-the-board-asks-another-machine-o
    exit         None
2. closed card (Executed), restarted on its own work
    enter        hands on: 9999aaaa on gmail in card-123-the-board-asks-another-machine-o
    exit         None
3. card wrongly opened before the fix (Executing), the visitor still there
    lane.state   working
    enter        None
    exit         None
4. card genuinely under way (Executing), its own colleague working
    lane.state   working
    enter        None
    exit         None
```

State 1 is the defect, reproduced: the board tells a finished card to enter Executing
because someone asked its old session for help. State 3 shows it does not right itself —
the card stays open while the visitor sits there.

After the change and the repairs (3317264):

```
1. closed card (Executed), its old colleague called away to read #80's work
    lane.state   ended
    lane.session None
    sentence     Nothing for you: its work landed on the shared branch and nothing is
                 working on it: 8d7fb4a3 is answering a call from #80.
    away         8d7fb4a3 is answering a call from #80
    enter        None
    exit         None
2. closed card (Executed), restarted on its own work
    lane.state   working
    sentence     Happening now: a session is working on it, opus on gmail, for 5 min.
    away         None
    enter        hands on: 9999aaaa on gmail in card-123-the-board-asks-another-machine-o
    exit         None
3. card wrongly opened before the fix (Executing), the visitor still there
    lane.state   ended
    away         8d7fb4a3 is answering a call from #80
    enter        None
    exit         ('Executed', 'the close landed: the plan is archived and DELIVERED is written')
4. card genuinely under way (Executing), its own colleague working
    lane.state   working
    away         None
    enter        None
    exit         None
```

All four answers are what the plan's item 3 promised, read against the test board's own
rows: 1 stays where its close put it with nothing added; 2 enters as it always did; 3
returns to Executed — the column its close chose — with nobody touching it, and never to
Decision moment; 4 is unchanged.

**Live evidence that the defect is the one the owner meets.** Card #123's lane filed it
on 2026-09-12 after being pulled open by card #80's call. Card #82's lane hit it again on
2026-09-13 while this was being built, said so on the watercooler, and had to move the
card back by hand through the owner's own door — "left alone it would have landed in
Decision moment under 'the work folded into origin/develop, but no session wrote it up' —
false, since its close landed on 2026-09-12". State 3 above is that card, righting itself.

**The suite.** Run module by module on 3317264 from the lane's worktree (`uv run pytest
-q --no-header -p no:randomly <module>`; one process per module — a single process
holding every floor at once falls over on this machine). Every module green. The modules
this change touches most: `tests/board/test_lane.py` (37), `tests/api/test_calls.py`
(12), `tests/runtime/test_calls.py` (12), `tests/runtime/test_codex.py` (13),
`tests/infrastructure/` (61), `tests/ratchets/test_a_colleague_helping_is_still_its_own_cards.py` (4).

**The frontend.** `npx tsc --noEmit` clean; `npx vitest run` 85 passed in 2 files. Types
and the board fixture regenerated from the backend models (`api/typegen.py::write_types`,
`tools/board_fixture.py`), so the mirrors cannot drift.

**The live verification after the fold, and what it found.** The served board was
rebuilt and restarted on the laptop, migrated to 0025, and `session_slots.started_on`
is on the live table. Card #123 — the card the whole defect was filed from — reads
**Executed** on the owner's board, where its close put it. A note was then handed to
card #139's live session from this lane, and **card #139 went on reading "working" the
whole time it stood**: the repair of finding 1, on the real board, with no launch and no
stop. The same test found finding 6 above: the head never showed the note standing,
because the row was in this machine's store and the board reads its own.

**Limits, stated.** The note's delivery is verified against the served board through
`/api/word` with the hook's own query shape, not by driving a real Claude session's
PostToolUse hook; the hook's own change is one query parameter, covered by
`tests/api/test_hook_script.py`. The note reaches a colleague on the board's own
machine; from any other machine it is refused at the door, and the capability is filed
(finding 6). Migration 0025 is numbered 0025/0024 in this lane and
renumbers to 0026/0025 at the rebase over #139's fold, which claimed 0025 first; the
renumber is a head-field change to one file and the schema-vs-migration ratchet is what
proves it after. A note handed to a live colleague that never picks it up stays open
indefinitely by design — item 5's choice — and the head line is what makes it visible;
no ceiling ends it, which is the plan's promise and not an omission.
