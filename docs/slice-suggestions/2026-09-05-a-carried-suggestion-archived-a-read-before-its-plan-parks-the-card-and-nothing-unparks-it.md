# A carried suggestion archived a read before its plan lands parks the card, and nothing unparks it

**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation a2d30083), watching the dial's first night on Hello Revenue: #384's plan landed at 02:41 and the dial could not open Start on it, because the board had parked the card in Decision moment ten seconds earlier.
**Kind:** defect
**Fix:** now — the intent is plan 11's ("the board plans and starts a marked defect" with no hand on it) and INTENT's lesson 2 (true without anyone remembering); the fix is inside `board/reconcile.py` and `board/lane.py::after_archive`, the seam plan 11 already fixed once; it removes the class — every plan whose commit archives the suggestion it carries, read on a checkout the runtime levels — not the one card.

## Observation

Hello Revenue #384, on the board's own record, 2026-09-05:

- 02:40:35 `archived` — its suggestion moved to `docs/slice-suggestions/done/`.
- 02:40:38 `moved` — Backlog · Defects → Decision moment, "its suggestion was archived … but no session wrote it up on the board".
- 02:40:48 `linked` — to `docs/plans/2026-09-05-five-landing-pages-load-again-…md`, "which carries this card's suggestion".
- 02:41:18 `dial` — "Start waits: Start is offered in Up next and Planned; this card is in Decision moment."

The plan and the archive are one commit on Hello Revenue's trunk (`2105e24b9`, 113 lines of plan, one rename). Plan 11's lane fixed this seam for the case where the board reads both in one pass (`docs/slice-suggestions/done/2026-09-05-carrying-a-suggestion-the-way-the-readme-says-parks-the-plans-card.md`). On a checkout the runtime levels by fast-forward, the watcher read the rename in one pass and the new plan file in the next, ten seconds apart, and the one-pass fix did not apply. The store now holds the card with a live plan link and `link_archived = 0`, in a column no machine move leaves: `after_archive` runs on every pass but only parks; nothing reads "the reason I parked this is gone" and moves it back. The dial counts the card against its number while it waits, and only the owner's drag frees it.

## Evidence

- The audit rows above (`needle card hellorevenue 384`; the store's `audit` table).
- Hello Revenue `git show --stat 2105e24b9`: the plan and the suggestion's rename in one commit.
- Cards #361, #379 and #383, planned the same night by the same path, were not parked: their planning sessions left the suggestion live. The README's instruction to archive the carried suggestion is what trips it, so following the corpus rule is what breaks the board.

## What would hold it

- The machine undoes its own move when the evidence for it is gone: on every pass, a card in Decision moment whose last move was the machine's *archived* move and whose link is now a live document goes back to Planned, with the row saying why. The park stays for a card whose link is still archived.
- Or the park waits: an archived suggestion cited by no live plan is parked only after one settle window, so a rename read a pass before its plan never moves anything.
- The fixture case: the plan file and the rename applied in two reads, in either order, and the card ends in Planned with Start offered. The one-read test from plan 11 stays.
