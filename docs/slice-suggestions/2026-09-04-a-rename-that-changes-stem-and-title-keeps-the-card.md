# A rename that changes stem and title still keeps the card

**Found by:** the coordinating session, 2026-09-04 16:20, renaming a
suggestion from "the closed card…" to "the collapsed card…" on the owner's
word: the board birthed a new card (#18) and left the old one (#11) with its
document gone, instead of following the document.
**Kind:** defect

## Observation

Plan 01 promised "a card keeps its number when its document is renamed or
archived, so identity follows the document, not the path". The reconcile
matches a moved file by stem and by title; a rename that changes both — the
common case when a word in the title was wrong, since the filename carries
the title — matches nothing, so the old card loses its document and a new
card is born with none of the old one's history or rows.

## Done means

- A document that disappears in the same read as one appears is a rename
  when git says so (`git diff --name-status -M` on the corpus, or the
  watcher's paired delete-and-create) or when the bodies match closely
  enough (the Found-by line and the first paragraph identical is enough);
  the card keeps its number, its history gains "renamed from <old path>",
  and no new card is born.
- A test renames a suggestion changing both stem and title, and finds one
  card with the new document and the old history.
- Cards #11 and #18 on Needle's own board are the incident: when this
  lands, the lane merges #11's history into #18 (or the reverse) and retires
  the other, saying so on both.
