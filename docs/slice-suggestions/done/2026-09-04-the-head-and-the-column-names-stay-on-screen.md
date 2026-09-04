# The head and the column names stay on screen when the board scrolls

**Found by:** the owner, 2026-09-04: "when I scroll down I don't see the
lane names or the header anymore. So when I come back to a board that's
scrolled down I have to scroll up to orient myself."
**Kind:** idea

## Observation

The head (project, counts, attention rail) and the column headings scroll
away with the cards. A board left scrolled down is a wall of cards with no
name on any column and no attention line; the first gesture on returning is
always to scroll up.

## Done means

- The head, the attention rail and each column's heading stay pinned while
  the columns scroll; each column scrolls on its own so a long Backlog does
  not move Executing.
- An open card stays in view while its column scrolls, as slice 01 already
  promised ("expanding a card never scrolls the board away from it").
- On a laptop the pinned head folds to one line after the first scroll, so
  the columns keep their height; the attention rail's counts stay visible in
  that line.
- Built on the design system and re-signed on the comp in the plan's
  Rulings; a page test scrolls a column and asserts the heading and the rail
  are still in the viewport.
