# Two processes can birth the same card number

**Found by:** card #16's lane (plan 06), 2026-09-04, reading the served board's
journal while changing `apply_effects`: at 16:29:13 the server's `/api/projects`
route died with `sqlite3.IntegrityError: UNIQUE constraint failed:
cards.project_slug, cards.number` inside `Store.apply_effects`, on the birth
of a card whose number another process had just used.
**Kind:** defect
**Fix:** now

## Observation

A birth reads `projects.next_card_number`, inserts the card with it, and
bumps the counter, all inside one `Session.begin()`. But pysqlite opens the
SQLite transaction lazily, at the first write statement: every `SELECT`
before it — the project row, the card list the sweep reconciled against, the
landing group — runs outside the transaction, in autocommit. Two processes
that sweep the same corpus at the same moment (the server on a corpus change
and a `needle add`, or a lane's `needle card`, which loads the board in its
own process) both read the same next number, and the second `INSERT` fails
on the unique key. The first read of a document then produced no card in one
of them, and the other's request answered 500. With plan 06 the write stamp
runs as the first statement of every commit, which starts the transaction a
little earlier, but the reads that chose the number are still before it.

## Done means

- A write transaction in the store begins with the write lock (`BEGIN
  IMMEDIATE`), so the reads inside it see a state no other writer changes
  under them; a read-only session keeps its lazy begin, so the server's
  constant reads never wait on a lane's write.
- A test opens two `Store`s on one file, sweeps the same new document from
  both, and finds one card, one number, and no error.
- `Session.begin()` blocks are the writes; the store tells its two kinds of
  session apart by construction rather than by convention.
