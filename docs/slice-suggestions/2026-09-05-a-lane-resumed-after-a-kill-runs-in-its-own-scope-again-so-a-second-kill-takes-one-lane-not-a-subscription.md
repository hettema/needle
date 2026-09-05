# A lane resumed after a kill runs in its own scope again, so a second kill takes one lane, not a subscription

**Kind:** defect
**Fix:** now — the intent is written (INTENT lesson 1, the runtime owns launching and its scopes; plan 02's scopes, one per lane, so a limit or a kill is one lane's); the fix stays inside the runtime's adopt and the lane loop's read; it removes the class — every session resumed outside the scope the runtime gave it.
**Found by:** the owner, from card #50's close-out conversation on 2026-09-05, asking what happens to a killed lane's processes and whether they resume safely.

## Observation

When `systemd-oomd` killed Hello Revenue #386's lane scope at 10:59:22 on 2026-09-05, the machine's own unit "Resume Claude sessions interrupted by a transient error" restarted the session from its transcript within a minute (journal, 11:00:17), and the board read hands on again eleven seconds after it had read the lane ended. The resumed session runs inside `claude-daemon-hrme.scope` — the subscription's daemon scope — not in `needle-card-386-….scope`, which failed with `oom-kill` and is gone (`/proc/<pid>/cgroup` of the resumed session, read 2026-09-05). If oomd has to kill again, the biggest candidate is now the daemon scope holding every session on that subscription, not one lane.

## Evidence

- `journalctl --user --since 10:59 --until 11:01`: the oom-kill of the lane scope, then "Starting Resume Claude sessions interrupted by a transient error".
- `cat /proc/1928508/cgroup` → `/user.slice/user-1001.slice/user@1001.service/app.slice/claude-daemon-hrme.scope`.
- Card #386's history: 08:59:32Z "the lane ended with nothing folded (the journal for needle-card-386… says oom-kill)", 08:59:43Z "hands on: 7951d3df on hrme" — the same session id, back in the worktree.

## What would hold it

On every read, a session with hands on a lane's worktree whose cgroup is not the lane's scope is adopted into it (`runtime/machine.py::adopt`, the call the launch already makes), and the card says so in one row. The runtime's rescue after a wall already re-adopts, so this is the same act on the machine's resume path. The scope's name is the lane's, as at Start, so `systemctl --user show` and the memory reading above keep finding it.
