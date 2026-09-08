# A card waiting on you says why it landed there

**Kind:** defect
**Fix:** now — the intent is written (card #75's plan: "his part, the plain reason, what happens without him"), the fix stays in the board's own sentences, and it removes a class: the machine's reasons for moving a card (`board/lane.py` `Exit.reason`) are written once in the owner's words and reach both the history and the face, instead of the face carrying a generic reason because the history's line is in the machine's
**Found by:** the lane on card #75 (docs/plans/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md), in the review's feature pass

## The intent it breaks

A card in Decision moment tells the owner what it needs from him and why, and today the why is generic. Every such card reads "Your move: rule on this card. It sits in Decision moment, and nothing there moves without a word from you." — true of all of them, and so it tells him nothing about this one: whether a session finished and nobody wrote it up, whether the plan was archived with no signal, or whether he parked it there himself. The reason exists, in the history line that moved the card, and the face does not say it.

## Evidence

- `board/assemble.py::state_of` builds the Decision moment sentence with `standing.words` as the reason, which is None unless the board doubts the placement; the generic clause stands in.
- `board/lane.py::exit_for` and `after_archive` write the real reason into the move's history row ("the lane ended with nothing folded", "its plan was archived (…) but no session wrote it up on the board") — in the machine's words, with vocabulary words in them, which is why the face cannot quote them as they are: `tests/ratchets/test_every_face_sentence_says_whose_move.py` reads every face sentence on the test board against `docs/vocabulary.md`.
- `claims_of` already receives the placing audit row (`placement=`); `state_of` does not.

## What would fix it

Write each `Exit.reason` in the owner's words (they are sentences he reads in the history too), hand the placing row to `state_of` as `claims_of` already gets it, and make it the Decision moment sentence's reason; the ratchet then reads those reasons on the test board like every other face sentence.
