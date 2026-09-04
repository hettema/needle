# A write from another process reaches the page within a second

**Found by:** the owner, 2026-09-04: "I had to ctrl R to see '244 cards
carry a verdict you have not read'. Having to refresh the board to see
changes like these feels a bit archaic. I kinda expected everything new to
automatically appear."
**Kind:** defect
**Carried by:** docs/plans/2026-09-04-06-the-board-at-a-glance.md (item 6)

## Observation

The page holds a live stream and re-reads the board whenever the server's
version bumps. The server bumps it on its own moves and reads. But the
command-line doors — `needle row`, `needle close`, `needle verdicts --write`,
`needle add` — open the store in their own process and write straight to
SQLite; the server never learns, so nothing a session writes on a card
reaches the page until the next loop tick happens to bump, or the owner
refreshes. The cleanup lane wrote 244 verdicts this way and the attention
line stayed blank until a refresh.

## Done means

- The server notices a commit from any other process within a second and
  bumps its version: SQLite in WAL mode changes `PRAGMA data_version` on a
  connection whenever another connection commits, so one cheap check per
  second on the server's own connection is enough — no file watching, no
  second channel, no change to the writers.
- A test writes a row through a second `Store` on the same file and sees the
  server's version bump within the check interval.
- The page's stream reconnects after a server restart and re-reads once on
  the first message, so a restart never leaves a stale page (verify; if it
  already does, say so in the close-out).
