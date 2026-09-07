# One folder the board cannot read no longer leaves it deaf for the rest of the day

**Kind:** defect
**Fix:** now — plan 03 item 10 (`docs/plans/done/2026-09-04-03-the-doors-and-the-loops.md`) says "the running board hears the store change … a write from outside bumps it through the file watcher", and HOW-WE-WORK §5 says a failure that shows up silent or late gets a mechanism; the fix is inside `api/loops.py::_watch_registries`, which today `return`s on the first exception for the life of the process — it re-enters the watch after a failure, on the floor timer's cadence, and the class removed is every unreadable entry under every registry's `jobs/` on every boot, not the one directory named below
**Found by:** #249's reading on Hello Revenue, 2026-09-07

## Observation

Read live on 2026-09-07 from `journalctl --user -u needle-serve.service`.
Every start of the board since 2026-09-05 22:42 — six starts, the latest
at 22:06 today — logs the same line four seconds after "Needle at
http://127.0.0.1:8480/":

```
the board stopped hearing the registries (PermissionError: Permission denied
(os error 13) about ["/home/dennis/.claude-accounts/armana/jobs/f8e8b10c/tmp/cases/reports-dir-unreadable"]);
the floor timer covers it
```

That directory is a test fixture another session left behind, mode
`d---------`, created 2026-09-05 22:24. `watchfiles.awatch` raises when it
meets it, the `except` in `_watch_registries` logs once and returns, and
nothing restarts the watch. From that second on, for the whole life of the
process, the board hears no registry write: a lane that starts, a session
that dies, a hook's registry change all wait for the 30-second floor
(`FLOOR_SECONDS`). The board that was meant to hear instead of ask has been
asking, on every boot, for two days — and the line that says so is written
where nobody reads it.

## What decides the fix

The watcher should treat a failure the way `_timer` already treats one: log,
wait the floor, run again. An entry it cannot read is skipped, not fatal — a
registry's `jobs/` holds other sessions' scratch, and nothing there is the
board's to trust. The sentence "the floor timer covers it" stays true only
while the floor is a fallback for seconds, never for the day.
