# A session that ran out of room to think comes back with its state, and the board says that is why

**Found by:** Codex, reading #68 from its Discuss door on 2026-09-08 (round one, point 8), verified by Claude against `runtime/launch.py`
**Kind:** defect
**Fix:** now — §6 is the written intent (a partial result reported as whole is bad information) and §11's (a machine fact with named evidence); the fix is one captured context-exhaustion ending on the fixture and its classification in `runtime/reasons.py`, then the resume in `runtime/launch.py::move` carrying the work's state, and it removes the class — every session that ends on its context — not one card. Filed outside #68 by its ruling 6: no captured payload exists on this machine to classify from.

## Observation

Nothing on the board names a session that ended because its context ran out or its compaction failed. Its Stop hook reads like any other turn boundary, so the card says "the session finished its turn and was not resumed" or "stopped", and the owner cannot tell it from a session that chose to stop. The runtime's 8 MB branch (`runtime/launch.py:54–62, 651–660`) starts a fresh session with the brief when a transcript is too large to resume; it is a transcript-loading workaround applied once a move is already happening, not a detector of exhaustion, and #68's plan does not claim otherwise (its ruling 6 names this as deferred).

## Evidence

- `runtime/launch.py:54–62`: `RESUME_SIZE_LIMIT` and the fresh-brief path; `:651–660` where it applies.
- `domain/hook.py:30–39`: the hook shape records a SessionStart `source` (including compact) and a failure's `error` and `transcript_path` — the material a classifier would read.
- The machine's hook leaves an unrecognised failure logged and alone (`~/.local/bin/claude-acct:973–980`).
- No captured context-exhaustion payload on this machine as of 2026-09-08; a classification written without one is a guess (§8).

## Why it matters

A session that ran out of room mid-close leaves a lane with work in it and a card that says nothing is wrong. A resume without its state repeats the work or contradicts it.

## What would fix it

Capture one real exhaustion and one failed compaction on the fixture (a bg session driven past its window), classify each from the hook's own fields, and give the resumed session the work's state and the true reason it was restarted. Successful compaction continues untouched. Where a case cannot be classified the card says "the turn ended; the cause is not established", never a guess.
