# The board keeps hearing every session when one folder under a job cannot be read

**Found by:** the machine session on omarchy (3e51c668), 2026-09-09 11:40, reading `needle-serve`'s journal after the restart that deployed Needle #99
**Kind:** defect
**Fix:** now — the intent is the board's own (`api/loops.py::_watch_registries`: "a state change is a file write, and the board hears it instead of asking"), and the fix is inside that one function: watch the `jobs/` roots without descending into what a job wrote under its own `tmp/`, or skip a path the watcher cannot read and keep watching the rest. It removes the class — any unreadable file a session leaves under its job — not this one folder.

## Observation

Every restart of the board since 2026-09-05 logs, once per start:

    the board stopped hearing the registries (PermissionError: Permission denied (os error 13) about ["/home/dennis/.claude-accounts/armana/jobs/f8e8b10c/tmp/cases/reports-dir-unreadable"]); the floor timer covers it

The folder is a test case a Hello Revenue lane (#436, job f8e8b10c, 2026-09-05 22:24) made deliberately unreadable (`d---------`) under its own job's `tmp/`. The watcher is given every slot's `jobs/` root and watches it recursively, so one folder nobody can read ends the whole watch for every slot, and the board falls back to its thirty-second timer for the rest of its life. Nothing is lost, but a session's state change reaches the board a beat late instead of at once, and the fall-back is silent on the page: only the journal says so.

## The intent it breaks

The board hears a session's state change the moment it is written, instead of asking every thirty seconds. While this stands, one leftover folder from one lane's test makes every card on every board up to half a minute stale, and nothing on the page says so.
