# A clone record is never written for a machine the board forgot in the same instant

**Kind:** defect
**Fix:** now — the intent is written (card #83's plan, item 3: a machine's stale clone is said on that machine's own line and never outlives what it records; the record's finding 57); the fix stays inside `infrastructure/store.py::record_clones` and removes the class — the existence check and the write become one statement (an insert guarded by the machine's row, `ON CONFLICT` updating), so no removal can fall between them — rather than the instance a test could pin.
**Found by:** Codex's twelfth reading of card #83 (docs/reviews/2026-09-09-the-work-runs-where-the-horsepower-is.md, finding 57's last half), filed by the lane under the rule that three passes finding one shape end the loop with a question about the representation, not a repair read by nobody

## The intent it breaks

The head's machine line says which of a machine's clones is not level with the trunk, from a record the board writes on its trunk beat outside its lock. `record_clones` refuses a machine the board no longer knows, but the refusal is a read followed by a write: a `needle machine rm` landing between them leaves clone rows for a machine that is gone, and a machine registered again under that name shows the old warning as its own.

## Evidence

- `infrastructure/store.py::record_clones`: `session.get(MachineRow, machine)` then the inserts, under pysqlite's lazy `BEGIN` — Codex's probe in the twelfth pass interleaved `remove_machine` between the two on an in-memory store and read `['p: 1 behind']` back with no machine row.
- The window is a levelling in flight on the rented machine (a fetch, up to a minute) against a removal typed at the same moment; on a one-machine board nothing writes the table.

## What done looks like

`record_clones` writes each row with one statement that inserts only where the machine's row exists, and a test drives a removal from a second connection between the machine check and the write (an engine event before the insert) and reads no row back.
