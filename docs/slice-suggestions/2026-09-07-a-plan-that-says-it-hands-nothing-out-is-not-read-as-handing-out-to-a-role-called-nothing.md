# A plan that says it hands nothing out is not read as handing out to a role called nothing

**Kind:** defect
**Fix:** now — `docs/plans/README.md` says an item that is judgment hands nothing out and that silence means Fable, so a `Hands out:` sentence whose object is nothing (or none) states that same intent in words and names no role; the fix is inside `board/parse.py::handouts_of` and its `_handout` reader and removes the class: every plan that writes the sentence out reads as naming no handout, so no card carries a false undefined-role notice and no close writes a false named-and-never-dispatched cell
**Found by:** #36's reading, 2026-09-07

## Observation

Plan 50's item 3 (`docs/plans/done/2026-09-05-as-many-lanes-as-the-machine-can-hold-run-side-by-side-and-the-fold-settles-what-they-share.md`,
line 32) ends: *Hands out: nothing; the constant is a judgment.* The board
read the word after the colon as a role. On the served board on 2026-09-07,
`GET /api/projects/needle/cards/50` lists a named handout with role
`nothing`, what `; the constant is a judgment` and no verification; its
`handouts.unknown` is `["nothing"]` and its verdict reads *This plan hands
out to "nothing", which this machine has not defined; its roles are top,
downgrade, execution, search.* The close of #50 then wrote the HANDED OUT
row `execution ×0 (named 2), search ×0 (named 1), nothing ×0 (named 1) —
execution, search, nothing named and never dispatched`, and `needle card
needle 50` shows *hands: 3. The dial's number is headroom the machine reads —
nothing: ; the constant is a judgment; verifies nothing named*.

Three false things on one card: a role notice the plan did not earn, a
handout cell for a role nobody named, and an item read as handing work out
when its author said in the grammar's own word that it does not.

## What is true when this is fixed

A `Hands out:` sentence whose object is *nothing* or *none* reads as no
handout, the same as silence: it appears on no card's handout list, adds no
role to the undefined-role check, and contributes no cell to the HANDED OUT
row. A parser test holds it.

## Not this suggestion's business

The signal that found it (#36's WATCH) reads on its own card: whether lanes
whose plans name a handout dispatch one. #50 and #59 named execution and
search and dispatched neither; that is what the row is for, and the reading
says so there.
