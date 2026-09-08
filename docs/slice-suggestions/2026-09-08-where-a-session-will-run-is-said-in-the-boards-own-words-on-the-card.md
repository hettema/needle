# Where a session will run is said in the board's own words on the card

**Kind:** defect
**Fix:** now — `docs/vocabulary.md` already lists "headroom" as a word a card never uses, and the fix is one class: the board words the placement itself in `runtime/rule.py` (which slot, which model, that it has room) instead of quoting the account tool's free text onto the face
**Found by:** the lane on card #75 (docs/plans/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md), in the review's boundaries pass

## The intent it breaks

Every sentence on a card is in the owner's words, and a word the board or the machine defines never reaches him. The Start door's reason ends with the account tool's own sentence about why it chose that account, and that sentence says "headroom" — a word the vocabulary file retired from cards on 2026-09-07 — so the one place a card explains where work will run is the one place it still speaks the machine's language.

## Evidence

- `runtime/rule.py` builds `Placement.why` from the `why` field of `claude-acct best`'s answer and falls back to `"<slot> with <model>"` only when that field is empty. The test floor answers "Fable headroom on alpha" (`tests/floor.py`), and the real tool's wording is the machine's, not Needle's.
- `board/lane.py::doors_for` wraps that text as the reason of the open Start door ("Your move: press it and a session takes this card, fable on alpha. Fable headroom on alpha."), and the collapsed face's Start door carries the same reason.
- The ratchet `tests/ratchets/test_every_face_sentence_says_whose_move.py` reads every sentence the test board builds against the vocabulary; the test board's own placement was reworded to "Fable has room on alpha" so the ratchet holds, which is exactly the kind of instance fix the rule forbids — the class is the free text crossing onto the face.

## What would fix it

`runtime/rule.py` words the placement in Needle's own sentence — "fable on alpha, which has room" — and keeps the tool's text where a session, not the owner, reads it (the `Where.reason` the launch records). The floor's answer can then say anything and the face stays in his words.
