# Nothing a finished session started keeps running

**Carried by:** docs/plans/2026-09-09-nothing-a-finished-session-started-keeps-running.md
**Found by:** the machine session on omarchy (3e51c668), 2026-09-09 10:20, asked by the owner why the laptop was struggling with "only one agent building"
**Kind:** defect
**Fix:** now — HOW-WE-WORK §12 is the written intent (a session's work runs apart, in its own process group, so one kill takes one lane) and §11's rule that the board never lies while he is away: the board read three sessions as ended while their groups ran on for a day. The fix is one machine fact on the beat beside `api/loops.py::_keep_in_scope` and `_release_finished`, with the verbs in `runtime/machine.py`; it removes the class — every process a session leaves behind, whatever it was waiting for — not the forty found today.

## Observation

At 10:20 the laptop held 7.1 GB in swap with 1.9 GB free, and the owner
felt it. Among the causes: 38 shells and 46 `sleep` processes left by
sessions that had ended hours earlier, each shell a wait loop a session
had typed to watch a background job and then abandoned:

- 26 from Hello Revenue #456's lane, 5.5 hours old, waiting with
  `until ! pgrep -f "run_batch.py /tmp/p17/muts2.json"` — a pattern that
  matches the waiting shell's own command line, so the loop can never end
  (the trap §12's last sentence names). The batch finished at 05:05. Once
  two such shells exist they keep each other alive: `pgrep -af` for the
  pattern answered nine waiters and no batch.
- 7 from Needle #75's job e0c827b4 (33 hours old), waiting on a task
  output file the session never wrote, one started every ten minutes
  from 01:04 to 02:05.
- 5 from Needle #63's job dc575103 (21 hours), waiting with `until grep -q
  "EXIT=" suite.txt` for a line the suite never wrote.
- 2 from omarchy #45's job a8789dc7 (24 hours), the same shape.

Four different wait shapes, one class: the session's turn ended, the
board read it as ended (`needle sessions` said so), and nothing ended
what the session had started. The runtime already puts every lane's and
reading's session in a process group of its own (`needle-<lane>.scope`,
`runtime/launch.py::scope_session`), and its docstring records that
stopping the group ends everything in it (verified 2026-09-04). But no
part of the board stops the group when the session is gone:
`_release_finished` stops the *session* after a fold and close, and every
other ending is left as evidence. So `needle-card-45-….scope` and
`needle-card-63-….scope` stood `active (running)` for a day holding
nothing but waiters and sleeps.

Rehearsed by hand at 10:31: `systemctl --user stop
needle-card-63-the-strongest-model-with-room-to.scope` took 15 ms, the
unit read `inactive`, and all ten processes were gone; the same on #45's.
The live lane (#456) and the two readings were untouched. Shells went
from 53 to 11 and sleeps from 46 to 2.

## The intent it breaks

A session's work stays its own and ends when it does, so the machine's
memory is the lanes that are running and nothing else. While the defect
stands, every abandoned wait lives until the next reboot, spawning a
process every few seconds, and the board says the session ended when a
piece of it is still running.
