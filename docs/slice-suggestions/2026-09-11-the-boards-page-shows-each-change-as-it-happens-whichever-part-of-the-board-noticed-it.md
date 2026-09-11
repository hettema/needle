# The board's page shows each change as it happens, whichever part of the board noticed it

**Kind:** defect
**Fix:** now — the page's live stream promises in `Live.wait_for_change` to return the version after the one a page holds as soon as it changes, and a wake set from a worker thread leaves the page waiting for its keepalive instead; making the one wake hand itself to the server's loop removes the delay for every part of the board that changes something, not for one caller.
**Found by:** the lane on card #124 (docs/plans/done/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md), in the review's seams pass

## The intent it breaks

The open board is meant to show what just happened without a reload: a
session's question, a card's move, a finished read. When the part of the
board that noticed the change runs in the background, the page may not hear
of it until the next quiet tick of its connection, so the owner can look at
a board that is behind by that tick while the board already knows better.

## Evidence

- `infrastructure/live.py::Live.bump` resolves the `asyncio` futures that
  `wait_for_change` parked on the server's event loop; `asyncio.Future` is
  not thread-safe (Python's `asyncio` documentation, "Futures": the loop is
  woken only by `call_soon_threadsafe`), so a future resolved from another
  thread wakes its waiter only when the loop next wakes for another reason,
  at worst the stream's `keepalive` in `api/app.py::board_events`.
- Callers that run under `asyncio.to_thread`, read 2026-09-11 on
  `origin/develop` at d32e24f plus card #124's lane: `api/loops.py` —
  `word_now` (the word read, bumps after moving the heard-mark),
  `read_signals_now` → `_land` (a signal landing), and the two bumps in the
  trunk levelling (`level_trunks_now` / `level_project`).
- Card #124 moved the hook intake's store write onto a worker thread and
  kept its bump on the loop for this reason (its commit 8b74152, held by
  `tests/api/test_doors.py::test_a_post_is_answered_while_a_pass_is_stalled_and_the_passes_it_causes_coalesce`);
  the callers above predate that card and were left as they were, since
  changing `Live` is outside that card's change.
- Not observed on the served page: the delay is inferred from the
  documentation and the code path, not measured.
