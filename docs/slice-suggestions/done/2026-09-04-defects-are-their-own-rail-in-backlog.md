# Defects are their own rail in Backlog

**Found by:** the owner, 2026-09-04, after the review-rings ruling: "we
should have a separate backlog lane for bug reports. Backlog should be for
ideas in my mind, easier to scan that way."
**Kind:** idea
**Carried by:** docs/plans/2026-09-04-06-the-board-at-a-glance.md

## Observation

Backlog holds two different things under one heading: ideas (what we might
build) and defects (what we built and got wrong, filed by review passes under
the rings rule). Scanning for either means reading both. The rings rule now
files every adjacent and outside finding as a suggestion, so the defect share
of Backlog only grows.

## Done means

- A suggestion document declares its kind on one line, `**Kind:** defect` or
  `**Kind:** idea`, and a document with no kind line reads as an idea. A
  review's filing writes `defect` — the rings rule in `CLAUDE.md` and Hello
  Revenue's review skill say so.
- Backlog shows defects as one pinned rail at its top with its own count,
  above the idea groups; the attention rail counts unplanned defects
  separately from unplanned ideas.
- A defect flows through the same columns as an idea; nothing else about its
  life is different. **Ruling proposed:** a rail, not a column — a column
  splits the one flow and costs width the laptop does not have; if the rail
  is used and the owner still wants a column, it is one definition.
- The 0.1-era suggestions get their kind read from their text where the lane
  can tell (a "Found by … review" line, a defect-shaped title), and `idea`
  otherwise; the lane's table of the guesses goes in its close-out.
