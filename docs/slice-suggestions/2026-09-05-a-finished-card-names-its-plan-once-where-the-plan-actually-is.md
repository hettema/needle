# A finished card names its plan once, where the plan actually is

**Found by:** the lane on card #57 (docs/plans/done/2026-09-05-a-colleague-of-any-make-can-be-called-warm-and-seen-at-work.md), in the review's seams pass
**Kind:** defect
**Fix:** now

## Observation

Every closed card shows its plan twice: once at the path the plan is at, and once at the path it used to be at.

```
#57   open: docs/plans/done/2026-09-05-a-colleague-of-any-make-…md (archived)
      also: docs/plans/2026-09-05-a-colleague-of-any-make-…md
#54   open: docs/plans/done/2026-09-05-18-a-new-project-…md (archived)
      also: docs/plans/2026-09-05-18-a-new-project-…md
#51   open: docs/plans/done/2026-09-05-17-asking-a-colleague-…md (archived)
      also: docs/plans/2026-09-05-17-asking-a-colleague-…md
#50   open: docs/plans/done/2026-09-05-as-many-lanes-…md (archived)
      also: docs/plans/2026-09-05-as-many-lanes-…md
```

The second path is not a file. Nothing in the corpus is at it, and nothing in the corpus cites it — `grep -rln` over `docs/` finds no occurrence at all. It is the card's own citation list, written when the card was made and the plan was live, kept verbatim after the close moved the plan into `done/`. `board/assemble.py:1004` builds `other_citations` as "every citation of this card that is not the document's current path", so the moment a plan is archived its old path stops matching and starts showing as a second, other thing the card is about. Four of four archived cards checked on 2026-09-05 show it; #50 shows a real second citation (a suggestion it carried) above the phantom one, so the true and the false sit in the same list under the same word.

## Why it matters

The board's one job is to say what is true, and the review's own seams lens is "the truth of what the board shows". A path that names no file is not a citation; it is the memory of one. It costs a reader a lookup that ends in nothing, and it is worst exactly where it is least checked — on a card that is Done, which nobody will open again to find out that half of what it says is stale. It also hides the real case: a card that genuinely cites two documents (a plan and a suggestion it carried, as #50 does) is indistinguishable from a card carrying one phantom, so the reader learns to skip the line, which is how a board stops being read.

The fix is a class, not an instance: a citation is shown only when the corpus holds it. Whatever the close does to the plan — archive, rename, `git mv` — the card follows the file rather than remembering the string, so the next mechanism that moves a document does not have to remember this one too.
