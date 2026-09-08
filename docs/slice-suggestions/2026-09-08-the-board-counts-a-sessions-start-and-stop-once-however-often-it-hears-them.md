# The board counts a session's start and stop once, however often it hears them

**Kind:** defect
**Fix:** now — the board's own rule is that a column is a machine fact with named evidence (CLAUDE.md, "the board reads what runs"), the fix is inside the one place events are recorded, and a check at that door removes the class rather than one event.
**Found by:** the lane on card #63 (docs/plans/done/2026-09-05-the-strongest-model-with-room-to-run-drives-the-card-claude-or-codex.md), in the review's seam pass

## The intent it breaks

The board's memory of what a session did should say each thing once. It says
some of them many times: one session starting is recorded as up to eight
starts, one session stopping as five stops. Nothing the owner reads is wrong
today — the board shows the newest of them — but every count over these
records is inflated, and any future reading of "how often did a session stop
to ask" or "how long between start and stop" is reading a number that has no
meaning.

## The evidence

In the board's memory on 2026-09-08 there are 928 groups of records that
share a kind, a session and a timestamp, out of 4,742 records; the oldest is
2026-09-04, four days after the board's first read, so this has been true for
its whole life. Examples from that morning: one session's `SessionStart` at
11:02:15 recorded eight times, another's `SessionEnd` at 11:02:23 seven
times.

Sessions of both kinds are affected, so it is not about which colleague ran:
a Claude session (`ac870d6c…`, eight starts) and a Codex one
(`01a080dd…`, three starts) sit side by side. The path is
`hooks/needle_hook.py::drain` and `api/loops.py::record_hooks`: the hook
queues an event, then posts the whole queue, and clears the queue only on a
2xx; `record_hook_events` writes whatever it is given. A post whose response
is lost, or two hooks draining at once, re-posts events already recorded, and
nothing at the door says "I have this one". An event has everything needed to
know it is the same one — its kind, its session and its own timestamp — so
the door can refuse a repeat.
