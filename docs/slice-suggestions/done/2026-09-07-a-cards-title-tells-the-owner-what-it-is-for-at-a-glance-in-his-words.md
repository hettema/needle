# A card's title tells the owner what it is for at a glance, in his words

**Carried by:** docs/plans/2026-09-07-every-card-title-says-what-it-is-for-at-a-glance-in-plain-words.md — planned on 2026-09-07 at the owner's word, the same day it was filed

**Kind:** defect
**Fix:** now — the intent is written: `docs/plans/README.md` lines 43–51 hold the owner's ruling of 2026-09-04 ("I need to be able to derive from the card title what the intent of the card is"), and 19 of the 28 live titles on Needle's own board break it with a term from the board or the code; nothing holds the rule but a README paragraph and one line of the planning brief, so the fix is a sweep of the live titles plus a cold read at every title's birth, which ends the class for every project on the board rather than renaming one card
**Found by:** the owner, reading his own board on 2026-09-07 ("the card titles are very difficult for me to understand, which makes the board difficult to read"; "I am not technical, so tech jargon in there doesn't help me"), and the session that read the 28 live titles with him

## Observation

The owner ranks cards from their titles alone, and the README says the title is therefore "the outcome, never the mechanism, the area or a term from the code", in his words. Read on 2026-09-07, the live corpus does not meet that bar:

- 28 live titles (9 plans, 19 suggestions); 19 use a word the board or the code defines and the owner does not — lane, make, fold, dial, ring, door, wall, pill, gate, scope, corpus, fixture, migration, store; 12 run past twelve words, the longest 25.
- "A gate the board cannot read is a quiet pill, not a count", "A fix lane that files its own third ring is counted as undone", "The strongest model with headroom drives the card, whatever its make": each is a true outcome sentence, and each needs the doctrine and the code to be placed. The test the README sets — could he place it against every other card without opening it — fails for the person it was written for.
- The line under the title does not rescue it. `board/parse.py::essence_of` takes the first sentence of the intent for a plan and the first sentence of the body for a suggestion; for a defect that sentence is the evidence, so the face reads `board/lane.py:673 closes Start on a card whose plan…` or `api/dial.py::fixes decides defect_filed_against by…` — a path and a function name, under a title he already could not read.
- Nothing holds the rule. `tests/ratchets/` constrains titles only for leakage of a real project's titles into the tree; the README paragraph and `board/brief.py` rule 1 are conventions, and every title above was written by a session that had read both. A boundary that depends on a session remembering it erodes (HOW-WE-WORK §5), and this one failed silently 19 times.

## The intent it breaks

HOW-WE-WORK §10 and `docs/plans/README.md` lines 43–51: the title is his to rank by, in his words. The owner's steering: he directs on intent and outcome, not mechanism. A title that names the mechanism hands him the colleague's half of the picture and withholds his own.

## What removes the class

Three pieces, one lane; the last two are what stop it coming back.

1. **The sweep.** Every live plan and suggestion title on Needle's board is rewritten to the README's bar: the outcome, in words the owner uses, no term the board or the code defines, short enough to place at a glance. The file stem follows the title; the card keeps its number and its history through the rename (plan 08). The old sentence, where it carried something the new title does not, moves into the document's intent, so nothing the record held is lost. The owner reads the new titles on the board and renames any that still miss.
2. **A cold read at birth.** The reading that already verifies a suggestion's `Fix:` mark from outside the finder's context (plan 11) reads the title too, against the README's test and a vocabulary the board derives from the doctrine and its own code — the words it defines are the words he does not use. A title that fails lands a typed result on the card, and the face says so as a machine fact with the words that failed; the planning brief's rule 1 carries the same vocabulary so the writer sees it before the reader does. The intent is mechanised, not the method: the check is "can he place it", never a word count.
3. **The face's second line says what he would notice, never where the code is.** For a defect, the essence is the sentence that names the intent it breaks, not the first sentence of the evidence; a path or a function name never reaches the face of a closed card.

## Loop

We think a title written to the bar, held by a cold read, will let the owner place every card without opening it, because the rule was right and only unheld. If, a week after the sweep, he opens a card to learn what it is about, or renames one, that title is the finding: the vocabulary or the bar is wrong, and the reader is changed, not the rule.
