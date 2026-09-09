# Nothing a finished session started keeps running

**Carries:** docs/slice-suggestions/done/2026-09-09-nothing-a-finished-session-started-keeps-running.md
**Status:** NEW — written and started the same morning by the machine session, on the owner's word.
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
names has no live session at all. The stop goes through the runtime
(`runtime/service.py`, one verb beside `rescope`), and the card the
group names gets one row, machine as actor, saying what was stopped and
how many processes it held; a group named for no card on any board is
stopped and logged. An empty group is left alone (Start's settle
window). A stop the manager refuses is said once on the card, not every
thirty seconds (the memo `_keep_in_scope` keeps for its adopts).
Done means: on the test floor, a lane whose session has ended and whose
group still holds a process is swept on the next reconcile — the fake
manager records the stop, the card carries the row with the count — and
in the same test the live lane's group, an empty group, and the daemon's
group are not touched; a second reconcile stops nothing again.

### 2. `needle scopes` shows every group of ours and who is home
One list from the terminal, the shape of `needle sessions`: each group
the manager holds, whether a live session is in it, and what else it
holds by count and command head; `--stray` lists only the ones nobody is
home in and `--count` prints their number. This is the loop's reader and
the by-hand check before item 1 is trusted.
Done means: on the floor, the list names the swept group as stray before
the beat and not after; `--stray --count` prints `0` on a clean machine.

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
- **Nobody home means both.** The group holds a process and no live
  session's pid is in it, *and* the card it names has no live session.
  The second guard covers the moment a moved session is being put back
  into its group and the first reading missed it; the empty-group guard
  covers Start, where the group exists before its process settles.

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
