# A card waiting on your word shows the decision, not the death

**Kind:** defect
**Fix:** now — the intent is written (docs/INTENT.md: the board is true at every moment, and Decision moment is the column where only he moves a card; card #155's plan: work waiting for his feedback is never presented as lost work) and the fix stays inside one reader, the order of the card's face in `board/assemble.py::state_of`, where the "session died" branch is tested before the Decision moment branch; a card in his column leads with the decision the column holds and keeps the death inside the card, which removes the class (every parked card whose session died) and not the instance.
**Found by:** the lane on card #155 (docs/plans/done/2026-09-16-work-waiting-for-your-feedback-stays-ready-for-your-answer.md), in the independent review

## The intent it breaks

A card that sits in Decision moment waiting for his word shows him the decision, and a session that died on it weeks ago is a fact inside the card, not the card's face. While the face says "session died" over a decision a cold reading already put to him, he reads a parked decision as broken work to resume or start again, and the question the card actually holds is one click further away than everything else on the board.

## The evidence

Found on the served board on 2026-09-16, after card #155 landed, by that plan's Loop — the first reading of every ended lane that carries an owner's request. Hello Revenue #147 ("Tell production which ad account…", imported from Needle 0.1 on 2026-09-03) sits in Decision moment. Its lane's session died on 2026-09-05 when the machine took back its account's memory (an oom-kill of the daemon's scope); the card was moved there on 2026-09-04 because its DELIVERED row was a previous life's and no close landed. On 2026-09-15 a cold reading of the parked card found the decision is his — "Correct mhall's frozen share to EUR 499.01 by one-off script, or let EUR 998.03 stand?" — and wrote it on the card (a TRIAGED row, the dial's note). The card carries an ASK row with the same question, the import's, with no writing on the history.

What the face shows: the word "session died", in red, and the sentence "Something is wrong: the session on it ended 13 d ago. The machine took back its account's memory at 2026-09-05 16:02Z (…oom-kill…). Open the card to start again." The decision the reading put to him is below, inside the card.

Why: `board/assemble.py::state_of` tests an ended lane that died (`_lane_died`: not folded, no close landed, no park, not a shipped column, not Not now) before it tests the card's column, so for a card in Decision moment the death wins the face and the column's own words — `parked_words` from the cold reading, or the column's sentence — are never reached. Card #155 changed `_lane_died` so a lane whose sentence is his move (an ended session that asked, or a card whose rows carry a decision of his written in this life of the lane) is not a death; #147's ASK has no writing before this life, so by that rule — a row from a previous life is a question already answered or overtaken — it is not read as current, and correctly so: the reader that knows the question is current is the cold reading, which is the column's word, not the lane's.

Neighbours on this ground: #82 (a cold reading of a parked card says what the decision is; `board/parked.py::parked_words` is the one place the words come from), #155 (an ended lane with a current request is his move, never a death — this is the card that found this one), #136 (a card stops asking for something he already did), #88 (the wording of Decision moment reasons). None holds this: #82 wrote the words, #155 wrote the lane's reading, and neither touched which of the two the face shows first.

## What done looks like

A card in Decision moment whose lane died shows the decision as its face — the cold reading's words when one has read it, the column's sentence when none has — in the column's own colour, with the death as a line inside the card where the lane's sentence lives. The head counts it as a card in Decision moment and not as a lane that died. A card whose lane died in any other column keeps its red face: the death is still what red is for there. The fixture gains one parked card with a dead lane and a reading, and the face test pins the word.
