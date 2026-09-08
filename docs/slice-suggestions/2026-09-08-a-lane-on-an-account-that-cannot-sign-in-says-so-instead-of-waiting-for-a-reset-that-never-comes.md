# A lane on an account that cannot sign in says so, instead of waiting for a reset that never comes

**Found by:** Codex, reading #68 from its Discuss door on 2026-09-08 (round one, point 16), verified by Claude against the machine's script
**Kind:** defect
**Fix:** now — §11 is the written intent (a machine fact with named evidence, or the board lies while he is away); the fix is inside `board/lane.py`'s sentence and `runtime/reasons.py`, reading the blocking-error record the machine already writes, and removes the class — every lane on a blocked account — not one card. Filed outside #68 by its ruling 6: no captured case on the board yet.

## Observation

The machine's `claude-acct` distinguishes `authentication_failed`, an org hold and a billing block from a wall: it logs them and raises one critical popup per slot per hour naming another slot, and leaves the slot in the placement rule (`~/.local/bin/claude-acct:927–945`). Needle reads none of that. A lane whose turn failed on such an error is a stopped session with an error text on the board, or, once its process is gone, "the session finished its turn and was not resumed". #68 gives a walled lane a park with an end at the reset time; an account that cannot sign in has no reset, and a park written for it would name a time that lifts nothing.

The machine's connectivity probe accepts any HTTP answer from `https://api.anthropic.com/v1/models` as "the connection is back" (`:1314–1320`), an error answer included — so "back" does not establish that inference is served, and a recovery resumed on it can fail the same way again.

## Evidence

- `claude-acct:927–945`: the blocking-error branch, log and popup, no handoff.
- `claude-acct:1314–1320`: the reachability probe's acceptance.
- `runtime/reasons.py::why_ended`: reads a scope's journal and the registry's state; never the machine's interrupted or blocking records.
- #68's item 3 gives a park an end; an account block has none the machine can read.

## Why it matters

The owner reads the card to decide whether to act. A lane waiting on a sign-in that only he can do, shown as a park with a reset time or as a finished turn, waits until he happens to look.

## What would fix it

The board reads the machine's blocking-error record for the lane's slot and says "this account cannot sign in; waiting for you, or for another account with room" — an ASK-shaped state, his, with the slot named — and a recovery on that slot is not attempted until the record clears. A recovery after a connection loss stands on an inference answer, not on any HTTP answer. Fixture: a lane whose slot carries a blocking record; the card's sentence, and no park.
