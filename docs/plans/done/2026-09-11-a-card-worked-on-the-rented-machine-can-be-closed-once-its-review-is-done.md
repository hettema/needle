# A card worked on the rented machine can be closed once its review is done

**Carries:** docs/slice-suggestions/done/2026-09-11-a-card-worked-on-the-rented-machine-can-be-closed-once-its-review-is-done.md
**Status:** CLOSED — outcome delivered by #131 on 2026-09-11; the original mechanism below was superseded by the owner.
**Written:** 2026-09-11, by the lane on card #124 after its close was refused. The owner's words when it was found: "I think Claude:5d3090d5 is bumping into the same thing", then "I will go with whatever you guys rec". The recommendation he took: fix this first, then close #124 with its record unchanged, rather than re-run its reads from the laptop.
**Effort gate:** medium — the change is one read routed to the machine the work ran on, through a verb and the remote client whose shape already exists for a lane's documents; the judgment is which store a record's call number belongs to when both machines number calls independently, and that a machine which does not answer is refused in its own words and never read as a missing call — both settled in the rulings below.
**Sequencing:** none. Shares `api/doors.py`, `api/runtime_cli.py`, `runtime/remote.py` and `runtime/service.py` with #123, which is in flight; the fold settles it.

## Subsequent owner ruling — 2026-09-11

Needle #131 supersedes the implementation below: the owner removed mandatory per-repair cold reviews, so closing no longer depends on their call rows on either machine. The original plan and evidence are preserved below; no remote verdict-storage mechanism is being built. The intended outcome — finished remote work can close without repeating its reviews — is carried by `docs/plans/done/2026-09-11-work-finishes-after-review-and-verified-fixes.md`.

## Intent

A card is closed the same way wherever its work ran: once a colleague of the
other kind has read its review and the record says so, the close records what
the owner now has and the signal that will prove it. Since the rented machine
became a place cards are worked (#83), a colleague asked from there is
recorded only in that machine's store, and the close on the laptop's board
looks only in its own. So a card worked on the rented machine cannot close at
all, however complete its review: #124 (Needle) and #504 (Hello Revenue) are
both finished and stuck on 2026-09-11, and #123 will be next. After this plan
the close finds each reader where the work asked it, and those cards close
with their records exactly as written.

What does not change: the close's bar. A record still names a real call of a
colleague of the other kind whose answer landed; only where the board looks
for that call changes.

## Items

### 1. The close finds a reader on the machine the work ran on
The close (`api/doors.py`, `_refuse_a_record_that_skipped_the_read`, which
hands `board/review_rules.py::verdict_faults` a `call_of` over the board's own
store, `calls.landed`, and a `words_of` that reads the answer file) reads each
verdict's call — its row, whether its answer landed, and the answer's words —
on the machine that holds the lane's worktree. The shape to follow is the
lane's documents: `runtime/service.py::lane_docs` asks `lane_machine`, reads
here when that machine is this one, and otherwise asks `runtime/remote.py`
through a `needle` verb with `--json` (`api/runtime_cli.py`, the `lane-docs`
verb). The answer file is on the lane's machine too (`runtime/calls.py::answer_landed`
stats a local path), so "landed" and the words are judged there, not here.
A lane on the board's own machine reads the board's store as today.
Done means: on the two-machine floor (`tests/floor.py::Floor.lay_host`), a
lane on the second machine whose record names a call held only in that
machine's store closes; a record naming a call neither machine holds is still
refused with the "no row" words; with the second machine down, the close is
refused saying that machine did not answer, never that the call has no row;
and a call number present in both stores with different rows is judged
against the lane machine's row.

**Deviated:** `docs/plans/done/2026-09-11-work-finishes-after-review-and-verified-fixes.md` removes the mandatory call-row requirement altogether under the owner's later ruling; no remote verdict-routing mechanism was built.

### 2. The cards stuck on this close
With item 1 folded and the laptop's board restarted on it, the cards finished
on the rented machine close through `needle close` with their review records
unchanged.
Done means: #124 (Needle) closes into Executed with
`docs/reviews/2026-09-11-a-sessions-message-is-answered-at-once-and-never-sent-twice.md`
as written, its calls 91 to 99 read from the rented machine's store; #504
(Hello Revenue) closes the same way, its calls 100 to 104 read there; the
card of this plan records which of them closed and when, and a card still
refused says its words.

**Met:** After #131 was activated, Needle #124 and Hello Revenue #504 both closed into Executed using their existing DELIVERED/WATCH text and original review records. Their reviews were not repeated or rewritten and no call rows were copied.

## Acceptance criteria

- A card worked on the rented machine closes once its review is read and
  recorded, with no row copied by hand and no read asked twice.
- A record that names a call nobody made is still refused.
- A machine that does not answer at close time is named as not answering.

## Rulings

- **Read where the work ran, never record twice.** Rejected: `needle call`
  writing its row into the board's store as well. The two stores number
  calls independently (the board's stopped at 83 while the rented machine's
  reached 104 on 2026-09-11), so one number would name two rows, and the
  calls already made for #124 and #504 would stay unreadable.
- **The reader runs beside the work.** Rejected: sending `needle call` to the
  board's machine. A colleague reading a lane must read that lane's worktree,
  on the machine that holds it.
- **No hand copies, no second reads.** Rejected: copying the rented machine's
  call rows into the board's store, or asking the five colleagues again from
  the laptop — the owner's ruling on #124 (2026-09-11), since either would
  make a record cite reads that did not happen where and when it says.
- **A call number is the lane's machine's.** A record's `call <n>` is read in
  the store of the machine holding the lane, because the lane asked from its
  own worktree; a lane on the board's machine is the one case where that is
  the board's store.

## Deliberately not

- The board's loop tending calls made on another machine (`api/loops.py`,
  `_tend_calls`): a lane's own `needle wait` stores the landed words on its
  row, which is what the close reads.
- `needle wait` run from a machine other than the call's.
- Where a call is recorded: unchanged.

## Loop

We think reading a record's calls on the machine the work ran on lets every
card worked there close, because every call row and answer those cards
depend on exists on that machine today. If #124 or #504 is still refused for
a call the board has no row for after the fold and the restart, the close is
not reaching the lane's machine for that lane — the routing in item 1 is
what changes.

Loop: card #124 is closed into Executed — command uv --project /home/dennis/Work/needle run needle card needle 124 expect column: Executed by 2026-09-18
