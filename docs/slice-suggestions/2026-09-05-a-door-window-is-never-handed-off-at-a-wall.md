# A door window is never handed off at a wall; the owner gets a popup instead

**Kind:** defect
**Fix:** now
**Found by:** the owner, from a session on gmail (2026-09-05 03:30), after the
Idea-door conversation a2d30083 on Needle hit hrclaude's session limit and
stopped dead with a popup saying "not launched via claude-acct".

## Observation

`claude-acct handoff` (the `StopFailure` hook) moves a terminal session to the
slot with headroom only when the session's parent process is a `claude-acct
use` supervisor: it files the handoff for that pid, stops the session, and the
supervisor resumes the same conversation on the new slot. Without a supervisor
there is nobody to act, so the hook logs "unsupervised, left in place" and
notifies the owner with the relaunch line.

Every window Needle opens is unsupervised. `runtime/windows.py` builds
`discuss_command` (the Idea and Discuss doors) and `look_command` (Look) as

    CLAUDE_CONFIG_DIR=… CLAUDE_ACCOUNT=… exec claude --model … --session-id …

so foot is the parent of `claude` and `CLAUDE_ACCT_SUPERVISOR` is never set.
Read from `/proc` on the live window at 03:25: pid 717078, parent 717053
(foot), no supervisor variable; the handoff log line for a2d30083 says
`unsupervised, left in place`. The runtime plan (docs/plans/done/…-02-the-
runtime.md) withdrew Needle's own `needle claude` wrapper on the ground that
"`claude-acct use/auto` already is that wrapper for terminals", and the window
commands never went through it.

The cost tonight: the owner opened an Idea conversation to watch the HR board's
auto-fix overnight, went to sleep, and the watcher sat at a wall until 04:40
with nobody to read the popup.

## What would hold it

`discuss_command` and `look_command` exec `claude-acct use <slot> …` instead of
`claude` with the config dir set by hand; the supervisor sets the config dir,
the account and its own pid, and keeps resuming the conversation wherever the
handoffs lead. `attach_command` is different — it attaches to a `--bg` daemon
session, whose wall is filed under `handoff/bg/` for the runtime — and stays as
it is.

Done means: a fixture window opened by the Idea door has a `claude-acct` python
process as the parent of `claude` with `CLAUDE_ACCT_SUPERVISOR` equal to that
parent's pid; the existing window tests pass with the new command text.

## Note for whoever builds it

`claude-acct use` reads a `--model` anywhere in its arguments as a hand-picked
model (tier `manual`), and a manual session is never moved back up to Fable
by the turn-ended hook. Needle always passes `--model`, so the naive change
would make every door window manual. Either pass `--model` only for the
downgrade rung and let the supervisor add Fable's id itself (it does, from
`roles.json`), or give `claude-acct use` an explicit `--tier`; the second is
cleaner and is the machine repo's half — say so in the discussion directory
before building either side.
