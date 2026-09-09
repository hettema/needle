# Nothing a finished session started keeps running

**Carries:** docs/slice-suggestions/done/2026-09-09-nothing-a-finished-session-started-keeps-running.md
**Status:** IN PROGRESS — written and built the same morning by the machine session (omarchy 3e51c668), on the owner's word; its lane is `card-99-nothing-a-finished-session-start`.
**Written:** 2026-09-09, from Dennis, after the laptop spent the morning paging with forty abandoned wait loops from three finished sessions: "Is the defect big enough to make a card? If yes, please create it and execute it so that this gets fixed. Feels like it'll speed up my machine which is a win I want now."
**Effort gate:** medium — the verbs (list the groups the manager holds, read what each holds, stop one) sit beside `runtime/machine.py::adopt` and `scope_memory`, and the beat's move beside `api/loops.py::_keep_in_scope` and `_release_finished`; the judgment is the test for "nobody home" and its two races (a group just made at Start, a session being moved back into its group), settled in the rulings below.
**Sequencing:** none. Shares `api/loops.py` with whichever lane is on the beat; the fold settles it.

## What is true today

- Every lane's and reading's session runs in a process group of its own,
  named after the lane (`runtime/launch.py::lane_unit`,
  `scope_session`); the runtime records which group each session was
  put in (`SessionSlot.scope`), and reads a live session's group from
  `/proc` (`Session.scope`). Stopping a group ends everything in it
  (verified 2026-09-04 in `machine.adopt`'s docstring, and again by hand
  today on #45's and #63's).
- The beat already reads those groups: their memory every pass
  (`headroom_now`), and a session found outside its group is put back
  (`_keep_in_scope`). A session whose lane folded and closed is stopped
  (`_release_finished`); every other ending is left as evidence.
- Nothing stops a group once its session is gone. Three stood a day
  holding only abandoned waiters (the carried suggestion has the count
  and the four shapes). The daemon's own group (`claude-daemon-<slot>`)
  is a different thing: it outlives every lane by design.
- Today's leftovers were stopped by hand at 10:31 (#45, #63) and killed
  by pid (#75's and #456's waiters). The live groups — #456's lane and
  two readings — are untouched.

## Items

### 1. A group nobody is home in is stopped on the beat, and the card says so
On every reconcile, after sessions are put back in their groups, the
beat reads every group of ours the manager holds active (the
`needle-` prefix, `runtime/machine.py`: a list of units by prefix, the
processes each holds from its control group), and stops the ones nobody
is home in: the group holds at least one process, no live session of
ours — either make, any project — has its pid in it, and the card it
names has no live session at all — on two reads in a row, thirty
seconds apart, because one read that landed between a Start and its
registry row must never end a lane. The stop goes through the runtime
(`runtime/service.py`, one verb beside `rescope`), and the card the
group names gets one row, machine as actor, saying what was stopped and
how many processes it held; a group named for no card on any board is
stopped and logged. An empty group is left alone (Start's settle
window). A stop the manager refuses is said once on the card, not every
thirty seconds (the memo `_keep_in_scope` keeps for its adopts).
Done means: on the test floor, a lane whose session has ended and whose
group still holds a process is noted on the next reconcile and swept on
the one after — the fake manager records the stop, the card carries the
row with the count — and in the same test the live lane's group, an
empty group, and the daemon's group are not touched; a further
reconcile stops nothing again.
**Met:** `tests/api/test_nothing_a_finished_session_started_keeps_running.py::test_a_group_nobody_is_home_in_is_stopped_on_the_second_read_and_the_card_says_so` — the lane's session is killed with no door and no hook; the first reconcile notes the group, the second stops it through the runtime (the fake manager records the unit in `scope_stops`) and the card carries *Stopped what a finished session left in needle-card-253-….scope: 1 process nobody owned (sleep 300); nothing a finished session started keeps running.*; in the same machine the live lane's group, an empty group and `claude-daemon-alpha.scope` are untouched, and a third reconcile stops nothing. `test_a_group_whose_card_still_has_a_live_session_is_left_alone` holds the second guard. Ownership follows ancestry (`board/dial.py::who_is_home`, `runtime/machine.py::ancestors_of`): a process a live session started is that session's wherever its own pid sits. Read live before the lane folded: `needle scopes` on this laptop found reading #241's group nobody home, holding a `uvicorn` the reading had started and left (1.9 GB peak); stopped by hand, the way the beat now will.

### 2. `needle scopes` shows every group of ours and who is home
One list from the terminal, the shape of `needle sessions`: each group
the manager holds, whether a live session is in it, and what else it
holds by count and command head; `--stray` lists only the ones nobody is
home in and `--count` prints their number. This is the loop's reader and
the by-hand check before item 1 is trusted.
Done means: on the floor, the list names the swept group as stray before
the beat and not after; `--stray --count` prints `0` on a clean machine.
**Met:** the same test — `needle scopes` lists the lane's group with its session home and *2 processes (sleep 300)*, then *nobody home  1 process (sleep 300)* after the kill, and `--stray --count` reads `1` before the sweep and `0` after; on this laptop at 11:05 it read the three live groups and the one leftover named above.

## Acceptance criteria

- A session that ends by any road — its turn done, a limit, a kill, a
  stop from the card — leaves nothing of its own running a minute later,
  and its card says the machine stopped what was left, with the count.
- A running lane, a running reading, a group made a moment ago, and the
  daemon's group are never stopped by this.
- `needle scopes --stray --count` reads `0` on this laptop every morning.

## Rulings

- **The beat sweeps, not a door.** Rejected: stopping the group inside
  `needle stop` or the close only. A session ends without any door — a
  limit, an oom-kill, a closed lid, a turn that simply finished — and the
  one thing that knows is the beat reading the registry. Two executors
  would be the second way the doctrine refuses.
- **The class, not the pattern.** Rejected: a refusal at the Bash tool for
  a `pgrep -f` that matches its own command. That trap is real and §12
  names it, but it was one of four shapes found this morning; a wait on
  a log line the suite never wrote is the same defect and no pattern
  catches it. What ends the class is ending the group.
- **Nobody home means both, twice.** The group holds a process and no
  live session's pid is in it, *and* the card it names has no live
  session, on two reads in a row. The second guard covers the moment a
  moved session is being put back into its group and the first reading
  missed it; the empty-group guard covers Start, where the group exists
  before its process settles; the second read covers whatever neither
  foresaw, at the cost of thirty seconds nobody will notice. Groups are
  read before sessions, so a session the registry knew before its group
  existed is always home on the first read.

## Deliberately not

- The worktree a finished lane leaves on disk: the plan of 2026-09-07
  (*a finished card leaves nothing behind on the disk*) owns it.
- A ceiling on how many lanes and readings run at once: the memory
  shortage is the owner's ruling, said aloud this morning; he watches it.
- Groups under any other prefix: the daemon's, the terminal's, VS Code's
  are not the board's to stop.

## Loop

We think a sweep on the beat will keep a finished session's leftovers
off the machine, because every session of ours already runs in a group
the manager can end in one call, and the only thing missing was the
call. If a group nobody is home in is ever counted a day after its
session ended, the "nobody home" test is wrong or the beat is not
reaching it, and item 1's test is what changes; if a running lane is
ever stopped by it, the second guard is wrong and the sweep is turned
off until it is fixed.

Loop: no process group of a finished session outlives the beat — command uv --project /home/dennis/Work/needle run needle scopes --stray --count expect 0 by 2026-09-23 every 1d
