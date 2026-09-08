# Every sentence on a card says whether it is your move, in plain words

**Carried by:** docs/plans/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md — planned on 2026-09-07 at the owner's word, sequenced after #74

**Kind:** defect
**Fix:** now — the intent is written (HOW-WE-WORK: "the person can see which without reading code"; the owner's steering: "say what changed and what it means for him, not how it works"; `domain/board.py::Meaning.YOURS` already defines amber as "only you can act"), the sentences are string constants in `board/lane.py`, `board/assemble.py` and `api/loops.py` that a test can read, and the fix is a shape every face sentence takes plus a ratchet that reads them all against the vocabulary file card #74 introduces, which ends the class for every project on the board rather than rewording one hold
**Found by:** the owner, reading card #74 on 2026-09-07 after it was placed in Up next: "the sub sentence 'Start waits on the plan's own word:' makes no sense to me? Is there something I need to do? The card is a surface that helps me understand intent and actions that require me, the sub sentence kinda failed on that. Same is true for held cards and cards in decision moment."

## Observation

- `board/lane.py` line 771 closes Start on a card whose plan's Sequencing names another card with: "Start waits on the plan's own word: its Sequencing names #20 (…); it opens by itself once every named card is in Executed or Done." Every word is the board's: "the plan's own word", "Sequencing", "Executed". The one thing the owner needs — nothing for you to do; this starts by itself when #20 ships; move #20 up if you want it sooner — is not said, and the first clause reads as if the plan were withholding something.
- The same shape is everywhere the board speaks. `board/assemble.py` builds sixty-three state sentences through `_state(...)`; `board/lane.py` and `api/loops.py` build the door and lane sentences. "Start waits on the plan's own word", "the rule found nowhere to run", "no signal named", "doubted", "evidence holds", "not read yet": each is true, each names a mechanism, and none leads with whether the owner must act.
- The colour already knows. `Meaning` (plan 27) paints amber for "only you can act", teal for "happening now", grey for quiet. A held card is quiet, so its colour says "not yours" while its sentence says nothing either way; a Decision moment card is amber, and its sentence says what the machine found rather than what it needs from him. The colour and the sentence should say the same thing, and today only the colour was written for him.
- Nothing holds it. The sentences are literals with no reader but the owner, and each was written by a session that had read the steering.

## The intent it breaks

The card is his surface for two things: what this is, and whether it needs him. HOW-WE-WORK says the person can see which without reading code; the owner's steering says say what it means for him, never how it works unless he asks. A sentence he has to decode is a sentence that failed the person it was written for, the same failure #74 files for titles.

## What would fix it

1. **One shape for every sentence the board says on a face.** It leads with his part — "Nothing for you", "Your move: <the one thing>", "Happening now" — then the plain reason, then what happens next without him, in the words of the vocabulary file card #74 introduces (`docs/vocabulary.md`: the words the board defines and he does not). For the hold on #74: "Nothing for you yet. This starts by itself once #20 ships; move #20 up to have it sooner."
2. **A sweep of every sentence the board can say**, in `board/assemble.py`, `board/lane.py` and `api/loops.py`, to that shape; held cards and Decision moment cards first, since those are the faces that ask him to read.
3. **A ratchet that reads the sentences.** They are string literals, so unlike a title they can be read by a test: every face sentence the board can build begins with one of the shape's openings and contains no vocabulary word. The colour's meaning and the sentence's opening must agree — an amber face opens "Your move", a quiet one never does — held by the same test on the fixture.

Sequencing: after #74's vocabulary file, or with it; the two share that one file and nothing else.
