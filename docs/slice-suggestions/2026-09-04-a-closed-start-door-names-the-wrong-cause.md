# A closed Start door names the wrong cause

**Kind:** defect
**Fix:** now
**Found by:** work-0c on the Omarchy board (2026-09-04), when Dennis could not
start card #7 and the card's own sentence sent us both to look at its column,
which was not the problem.

## Observation

`board/lane.py:673` closes Start on a card whose plan names no effort gate
with: *"This card names no effort gate; only a planned card is startable."*

The second clause is false whenever the first is true. The gate branch is
tested before the column branch, so a card reaching it may sit in any column —
card #7 was in **Up next**, which `STARTABLE_COLUMNS` includes. The reader is
told the cause is placement, moves the card, and the door stays shut. The
column branch four lines below already has the accurate sentence for its own
case ("Start is offered in Up next and Planned; this card is in …").

The cost is not the click. It is that the door is the only place the missing
gate is reported — nothing on the board, in `needle card`, or at session start
said a plan lacked a gate — so the one sentence that could name the cause names
something else instead. Six live Hello Revenue plans have carried the same hole
since June without anyone seeing it (now reported by `machine check`, which is
the machine's own patch over this).

## What would hold it

The gate branch says what is missing and where it goes: the `**Effort gate:**`
head field, the four levels, and `docs/plans/README.md` as the shape — with
the plan's path, since the card knows it. No claim about the column.

A test that the closed-Start sentences are mutually exclusive in what they
assert: a card in a startable column must never be told its column is why.
`tests/board/test_lane.py:495` asserts only the substring "names no effort
gate", so the false clause rides along untested.
