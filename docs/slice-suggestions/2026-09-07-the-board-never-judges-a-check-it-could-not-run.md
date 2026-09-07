# The board never judges a check it could not run

**Kind:** defect
**Fix:** now — HOW-WE-WORK §11 says a column is the person's ruling or a machine fact with its evidence, and §5 asks for a default that makes the wrong thing impossible; the fix is in `runtime/signals.py::read`, where a `command` signal whose shell answers "command not found" (exit 127, or 126) is reported as a reading that could not be made — `None`, as the `url` reader already answers a failed fetch — never as "not delivered", and at the close door (`api/doors.py::close`), which refuses a `command` WATCH whose first word the reader's own login shell cannot resolve, so a card never enters Executed on a check the board cannot perform; the class is every command signal on every project, not card #1
**Found by:** the Discuss-door conversation on Needle card #1, 2026-09-07

## Observation

Read live on 2026-09-07 from the store's audit rows for Needle #1 (the
runtime, shipped and archived 2026-09-04):

```
2026-09-04 12:38:06  machine  Signal read as not delivered: — command needle sessions does not exist in /home/dennis/Work/needle
2026-09-04 12:38:20  session  WATCH rewritten: … — command needle sessions expect working by 2026-09-06
2026-09-05 12:38:43  machine  Signal read as not delivered: `needle sessions` exited 127, expecting working: /usr/bin/bash: line 1: needle: command not found
2026-09-07 08:06:46  machine  Signal read as not delivered: `needle sessions` exited 127, expecting working: /usr/bin/bash: line 1: needle: command not found
2026-09-07 08:06:46  machine  Moved Executed → Decision moment — the signal says not delivered and its due date 2026-09-06 has passed   [signal-failed]
```

The reader (`runtime/signals.py::read`) runs a `command` signal through
`bash -lc` in the project's checkout and hands `returncode == 0` to `judge`
as the verdict. The shell's own "command not found" is exit 127, so a check
the board could never perform came back as the check saying no. Three reads,
one rewrite between them, and the same cause each time; on the due date the
board moved a shipped card to the owner's desk with `signal-failed` as its
evidence. The `url` reader in the same module already tells the two apart:
a fetch that fails answers `None`, "could not be fetched", and the landing
says "could not be read".

The command itself works from the project: `uv run needle sessions` lists
every session on the machine. What the reader lacks is `needle` on its login
shell's path; the close door accepted the row without trying.

The card was re-closed the same day on a check the reader's shell does run
(the rescue ledger, which is the claim itself: 39 rows with a limit reason),
and that is the instance. The class is the row above it.

## Why it matters

The owner's one ask of the board is that he can trust it. A machine move
stands on a machine fact with its evidence; here the fact was "the check
failed" and the evidence was the board's own inability to run it. Every
card whose WATCH names a project command that is not on the service's path
takes the same route: a false failure, then his desk, then a conversation to
find out nothing was wrong. The failure is silent until the due date and
looks exactly like a real one, which is the shape §5 says gets a mechanism.

## Boundaries

- Inside: `runtime/signals.py::read` (the command branch's verdict on
  exit 126/127), `board/signals.py::where_after` (already says "could not be
  read" for `None`; unchanged unless the reader's answer changes shape), the
  close door's refusal for an unresolvable command, and the tests that hold
  both on the fixture floor.
- Not this: putting `needle` on the service's path. That fixes one command
  on one machine and leaves the class; a check the board cannot run must be
  refused when written and named as unreadable when met.
- Not this: where an unreadable signal lands at its due date. Today it is
  Decision moment with "could not be read" as the reason, which is at least
  true; whether the board's own inability to read should ever reach the
  owner is a separate question, and this defect does not decide it.
