# Carrying a suggestion the way the README says parks the plan's card in Decision moment

**Carried by:** docs/plans/done/2026-09-04-11-defects-fix-themselves.md — fixed in that lane (the reconcile emits no `Archived` for a card the same read relinks to a live document; a test lands a plan with its carried suggestion archived in one read and finds the card in Planned), found independently by the dial's own path minutes after this was filed.
**Kind:** defect
**Fix:** now
**Found by:** the machine repo's Idea-door conversation (81c7301c), 2026-09-05
23:03, writing plan 14 with a `**Carries:**` line and moving the carried
suggestion to `docs/slice-suggestions/done/` in the same commit, exactly as
`docs/plans/README.md` says to.

## Observation

Card #30's history, one second apart:

- `corpus linked` — to the plan, "which carries this card's suggestion".
- `corpus moved` Backlog → Planned — "a plan appeared for it".
- `corpus archived` — "Its document was archived to
  docs/slice-suggestions/done/…the-signal-is-the-cards-thesis….md".
- `machine moved` Planned → Decision moment — "its plan was archived
  (docs/plans/done/2026-09-05-14-….md), but no session wrote it up on the
  board".

No such file exists under `docs/plans/done/`. The plan is live, `PENDING`,
and the board's own face shows `document_state: plan` with the live path.
Start is closed ("this card is in Decision moment").

The path through the code, read rather than guessed:

- `board/reconcile.py`: the per-card loop looks the card's link up as it
  was before this read — the suggestion — finds it in `done/`, and emits
  `Archived` for the card. The same read emits `Relinked` to the plan.
- `infrastructure/store.py`: `relinked` is applied first (link → the plan,
  `link_archived = relinked.archived`, false), then `archived` sets
  `link_archived = True` on the card whose link is now the plan.
- `board/lane.py` `after_archive`: runs from `api/loops.py` on every pass,
  for every card in Backlog, Planned, Up next or Executing; sees a link that
  says archived and no DELIVERED row, and moves the card to Decision moment,
  printing the link's path with `done/` inserted.

Because the flag is set in the store and nothing resets it, a hand move back
to Planned is undone on the next pass. The only corpus write that clears it
is a rename (`renamed` sets `link_archived = False`), which is what this
conversation did: the plan's stem changed, the title did not, and the card
followed with the flag cleared. That is a workaround, not a fix, and it
leaves the file's stem and title out of step.

Plan 11 (#34) carries two suggestions and never hit this, because its two
suggestions were left live in `docs/slice-suggestions/` rather than moved to
`done/` in the same commit. So the README's instruction has been followed
once, and that once broke.

## What would hold it

- The reconcile emits no `Archived` for a card the same read relinks to a
  live document; or the store sets `link_archived` only when the archived
  document is the card's link at the moment the effect is applied. Either
  makes the read order irrelevant.
- A test writes a plan with a `Carries:` line and moves the carried
  suggestion to `done/` in one read, and finds the card in Planned with a
  live link and no Decision-moment move.
- `after_archive`'s reason names the path that actually exists on disk, so
  the next reader of a history row is not sent to a file that was never
  there.
