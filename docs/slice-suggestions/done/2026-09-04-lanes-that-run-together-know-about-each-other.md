# Lanes that run together know about each other, before they start and before they fold

**Found by:** the owner, 2026-09-04: "how reliable is it that when I start
things concurrently they will actually not collide? And if they do collide I
am assuming that the sessions will work things out amongst themselves
efficiently? Maybe with the watercooler thing or a similar mechanism which is
board specific?"
**Kind:** idea

## Observation

What holds today (slice 03, `board/collision.py`): at Start, a card's plan
footprint — the files its plan names — is compared with every live lane's
declared footprint and its actual edits, and Start refuses a collision with
the files named; "Start anyway" overrides with the reason carried into the
brief. What does not hold: nothing re-checks while two lanes run (a lane
whose plan named nothing can drift into another's files); two lanes that
change the same behaviour in different files collide only at the fold, where
git's rebase either merges silently or refuses; and the sessions never talk —
the only channel that exists is the machine-level discussion folder, which is
not a board thing and which a lane reads only if its brief says so.

So: a collision on named files is reliably refused before Start; a collision
on unnamed files or on meaning is caught late or not at all, and the lanes do
not work it out among themselves, because they do not know about each other.

## Done means

- **Before start:** the brief of every lane lists the other live lanes on the
  project — card, footprint, what they are doing in one line — and the rule:
  leave those files alone unless your plan names them; if you must touch one,
  say so in the project's watercooler first.
- **While running:** the board re-computes footprints from each live
  worktree's actual diff on every read (already read for the verdict pill)
  and marks two lanes that have drifted into each other's files as
  **colliding** on both cards and the attention rail, before the fold.
- **The watercooler:** one file per project, `docs/watercooler.md` or the
  board's own store — the plan decides — that every lane reads at start and
  before its fold, and appends to when it touches a file outside its
  footprint or changes a seam another lane depends on; the board shows the
  last line of it on each live card. A lane that folds re-reads it first.
- **At the fold:** a rebase that touched a file another live lane also
  changed is reported on the card as "folded over #N's edits in <file>", so a
  silent merge is never silent.
- A test: two lanes on a fixture project with overlapping actual edits are
  marked colliding on the next read; one lane's watercooler line appears on
  the other's card.
