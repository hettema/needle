# A finished card that never shipped does not take the whole board down

**Kind:** defect
**Fix:** now — INTENT says the board reads what runs and shows it; card #75's rule that a face's detail opens with its meaning's word is written and its validator states the bar; the fix is inside the one seam that broke it (the lane's ended sentence and the face's broken word disagreeing) and removes the class: a face that refuses is one card's face, never the project's board.
**Found by:** the lane on card #41 (docs/plans/done/2026-09-05-a-card-that-finishes-or-needs-you-stays-on-screen-until-you-dismiss-it.md), in the review's done-means pass — the owner reported Hello Revenue's board answering 500 on 2026-09-09 at 13:16Z, after card #68's fold and restart

## The intent it breaks

The board is the team's memory and the owner watches the team's moves on it; on 2026-09-09 Hello Revenue's board answered nothing at all — a 500 on every read — because one card's face could not be built, and every other card on that board went dark with it. He loses the whole project's board for as long as one card's two sentences disagree.

## The evidence

- `journalctl --user -u needle-serve`, 13:16:01Z: `ValidationError: 1 validation error for CardState — a broken state's detail must open with 'Something is wrong'; got 'Nothing for you: its close landed and the session on it ended 5 d ago.'` on `GET /api/projects/hellorevenue/board`.
- `board/lane.py:446` (card #68): an ended lane whose `close_landed(card)` holds gets a quiet sentence, *its close landed and the session on it ended…*, whatever column the card is in.
- `board/assemble.py:588`: the face still says *session died* in red for an ended lane with nothing folded on a card outside Executed, Done and Not now (`_lane_died`), and `CardState`'s validator (card #75) refuses a red word over a quiet detail. A card whose close landed but which never folded — Hello Revenue holds one — is exactly that pair.
- A validator raising inside assemble takes the project's whole board down, not the one card: the same class card #75's build recorded on 2026-09-08 ("a validator raising inside reconcile silences a project on the served board").

Two fixes, both this class: the lane's ended sentence and `_lane_died` read the same facts, so one of them decides (a close that landed with nothing folded is broken, or it is quiet, but the same on both sides); and the board's assembly builds every other card when one refuses, showing the refusing card as broken with the validator's words as its detail.
