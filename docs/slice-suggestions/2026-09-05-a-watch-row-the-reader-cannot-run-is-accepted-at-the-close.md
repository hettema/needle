# A WATCH row the reader cannot run is accepted at the close and fails a day later

**Kind:** defect
**Fix:** now
**Found by:** the machine repo's card 16 (plan 13 there), 2026-09-05, opening
the three Executed cards on the omarchy board and reading their first readings.

## Observation

Three of three machine signals on the omarchy board failed on their first
read, and `needle close` had accepted every one of them without complaint:

- #12: `command 'machine burn --days 7'`. The grammar shows `<target>` and
  gives no way to write a multi-word command, so the lane quoted it as any
  shell user would. `parse_watch` keeps the quotes in the target and the
  reader hands the string to `bash -lc`, which looks for a program named
  `machine burn --days 7`. Reading at 22:22:24: exit 127, "command not found".
- #14: `command 'machine check'`. The same, twelve seconds after the close.
- #7: `file ~/.cache/omarchy/claude-acct/handoff.log`. The file reader joins
  the target to the project path without expanding `~`. Reading at 22:04:56:
  "does not exist in /home/dennis/Work/omarchy-machine".

Each would have read "not delivered" every 24 hours until its due date while
the card's state word still said "loop open · the board reads it 12 Sep". The
failure only surfaced because a conversation opened the cards.

## What matters for the fix

The close is the moment a reader can be proved to run: the lane is there, the
command is one it just ran by hand, and a refusal costs a sentence. A day
later the lane is gone and the reading is an error nobody reads. So:

- `needle close` (and `reading --watch`) runs a `command` or `file` reader
  once before accepting the row, and refuses the row when the reader itself
  errors (exit 127, a missing file), naming what it ran. A "not delivered"
  verdict at the close is fine and expected; "could not run" is not.
- Quotes around a `command` target are stripped, or the grammar says plainly
  that the target runs unquoted through `bash -lc`.
- A `file` target starting with `~` is expanded, or refused with the
  grammar; the reader's docstring today says "exists in the project", which
  no lane reads before writing the row.

The omarchy lane rewrote #7 and #12 as unquoted commands (bash expands the
tilde there) and closed #14 into Done as a verified mechanism; both
replacement rows were run by hand first.
