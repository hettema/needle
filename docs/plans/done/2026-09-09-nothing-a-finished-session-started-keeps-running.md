# Nothing a finished session started keeps running

**Carries:** docs/slice-suggestions/done/2026-09-09-nothing-a-finished-session-started-keeps-running.md
**Status:** SHIPPED — written, built, reviewed (Codex's pass, three findings, all landed) and folded on 2026-09-09 by the machine session (omarchy 3e51c668), on the owner's word; review record `docs/reviews/2026-09-09-nothing-a-finished-session-started-keeps-running.md`.
**Written:** 2026-09-09, from Dennis, after the laptop spent the morning paging with forty abandoned wait loops from three finished sessions: "Is the defect big enough to make a card? If yes, please create it and execute it so that this gets fixed. Feels like it'll speed up my machine which is a win I want now."
**Effort gate:** medium — the verbs (list the groups the manager holds, read what each holds, stop one) sit beside `runtime/machine.py::adopt` and `scope_memory`, and the beat's move beside `api/loops.py::_keep_in_scope` and `_release_finished`; the judgment is the test for "nobody home" and its two races (a group just made at Start, a session being moved back into its group), settled in the rulings below.
**Sequencing:** none. Shares `api/loops.py` with whichever lane is on the beat; the fold settles it.

## Intent

A session's work ends when the session does, so the laptop's memory is the running work and nothing else. Today every wait a session abandons lives until the next reboot, spawning a process every few seconds, and the board says the session ended while a piece of it is still running; this morning that was forty shells, forty-six sleeps and a web server nobody had asked for, on a laptop three gigabytes short. After this plan a finished session's leftovers are gone within a minute of its going, its card says what was stopped, and one command shows every group of ours and who is home in it.

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
names has no live session at all — on every read for thirty seconds,
because one read that landed between a Start and its registry row must
never end a lane, and reads come as fast as the registry changes. The
stop is asked of the manager through the runtime (`runtime/service.py`,
one verb beside `rescope`) without waiting on it, and the card the
group names gets one row, machine as actor, once the group reads empty,
saying what was stopped and how many processes it held; a group named
for no card on any board is stopped and logged. An empty group is left
alone (Start's settle window). A stop the manager refuses is said once
on the card and asked again after another window; a group not empty a
window after it was asked is asked again.
Done means: on the test floor, a lane whose session has ended and whose
group still holds a process is left through reads inside the window and
asked to end on the first read past it — the fake manager records the
stop — and the card carries the row with the count on the read that
finds the group empty; a refusal is said once on the card in words that
claim no stop, and the next window's ask lands; in the same test the
live lane's group, an empty group, the daemon's group and the group of
a session whose turn is done but whose process stands are not touched.
**Met:** `tests/api/test_nothing_a_finished_session_started_keeps_running.py::test_a_group_nobody_is_home_in_is_ended_after_a_window_and_the_card_says_so_once_it_is_empty` — the lane's session is killed with no door and no hook; reads inside the window leave the group, the first read past it asks the manager (the fake records the unit in `scope_stops`), and the read that finds the group empty gives the card *Stopped what a finished session left in needle-card-253-….scope: 1 process nobody owned (sleep 300); nothing a finished session started keeps running.*; in the same machine the live lane's group, an empty group, `claude-daemon-alpha.scope` and the group of a session whose turn is done with its process standing are untouched, and a later read asks nothing twice. `test_a_refused_stop_is_said_once_in_words_that_claim_nothing_and_asked_again` holds the refusal path; `test_a_group_whose_card_still_has_a_live_session_is_left_alone` holds the second guard; `tests/board/test_dial.py::test_who_is_home_follows_ancestry_and_names_strangers` holds ownership by ancestry and the stale copy. Ownership follows ancestry (`board/dial.py::who_is_home`, `runtime/machine.py::ancestors_of`): a process a live session started is that session's wherever its own pid sits. Read live before the lane folded: `needle scopes` on this laptop found reading #241's group nobody home, holding a `uvicorn` the reading had started and left (1.9 GB peak); stopped by hand, the way the beat now will.

### 2. `needle scopes` shows every group of ours and who is home
One list from the terminal, the shape of `needle sessions`: each group
the manager holds, whether a live session is in it, and what else it
holds by count and command head; `--stray` lists only the ones nobody is
home in and `--count` prints their number. This is the loop's reader and
the by-hand check before item 1 is trusted.
Done means: on the floor, the list names the swept group as stray before
the beat and not after; `--stray --count` prints `0` on a clean machine.
**Met:** the same first test — `needle scopes` lists the lane's group with its session home and *2 processes (sleep 300)*, then *nobody home  1 process (sleep 300)* after the kill, and `--stray --count` reads `1` before the sweep and `0` after; on this laptop at 11:05 it read the three live groups and the one leftover named above.

## Acceptance criteria

- A session whose process is gone by any road — a limit, a kill, a
  closed lid, a stop from the card, a resume elsewhere — leaves nothing
  of its own running a minute later, and its card says the machine
  stopped what was left, with the count. A session whose turn is done
  but whose process still stands is not gone: it can be resumed, so what
  it started is its own until the board ends it at the fold and close
  (`_release_finished`), and the beat takes the rest on its next read.
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
- **Nobody home means both, for thirty seconds.** The group holds a
  process no live session owns — by pid, or by ancestry, since a
  session's children can sit in the group while its own pid sits
  elsewhere — *and* the card it names has no live session, on every read
  for thirty seconds. The second guard covers the moment a moved session
  is being put back into its group and the first reading missed it; the
  empty-group guard covers Start, where the group exists before its
  process settles; the window covers whatever neither foresaw, at the
  cost of thirty seconds nobody will notice. Rejected, on Codex's
  reading: two reads in a row — reads come as fast as the registry
  changes, so a count is no settling time, and a count that kept
  advancing while a guard held would stop the group the instant the
  guard cleared. Groups are read before sessions, so a session the
  registry knew before its group existed is always home on the first
  read.
- **A turn that is done is not a session that is gone.** The registry's
  `done` is a session whose turn finished with its process resident and
  resumable; the board's own ruling leaves it standing as evidence until
  its lane folds and closes. So its leftovers are its own until then —
  the sweep reads by the process, never by the state — and the
  acceptance line that said "its turn done" was wrong and is corrected
  above (Codex's reading, 2026-09-09).
- **The card is told what happened, not what was asked.** The manager is
  asked without waiting, so a stubborn process never holds the board's
  lock for the manager's stop timeout (a `uvicorn` took all of it this
  morning); the row lands when the group reads empty, and a refusal is
  said in words that claim no stop.

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
