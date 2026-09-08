# Every sentence on a card says whether it is your move, in plain words

**Carries:** docs/slice-suggestions/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md
**Status:** SHIPPED 2026-09-08 — every item stanced below; the review record is `docs/reviews/2026-09-08-every-sentence-on-a-card-says-whether-it-is-your-move.md`.
**Written:** 2026-09-07, from Dennis reading #74's face: "the sub sentence 'Start waits on the plan's own word:' makes no sense to me? Is there something I need to do? The card is a surface that helps me understand intent and actions that require me, the sub sentence kinda failed on that. Same is true for held cards and cards in decision moment." And then, asking for the plan: "My intent is to understand the board at a glance and understand the cards when I open them. This needs to be true for the HR, Omarchy and needle needles."
**Effort gate:** medium — the sentences are string literals in three modules and a test can read every one of them; the judgment is the shape (one opening per meaning, and the opening agrees with the colour), settled in the Rulings here; the sweep is many small edits with a ratchet that says when it is whole.
**Sequencing:** after #74 (the vocabulary file `docs/vocabulary.md` is #74's item 1; this plan reads it and adds nothing to it). The two share that file and nothing else.
**Class:** a ratchet reads every sentence the board can build onto a face and refuses one that does not open with its meaning's words or that uses a vocabulary word; an amber face that does not open "Your move" fails the same test.

## Intent

The card is the owner's surface for two things: what this is, and whether
it needs him. Every sentence the board writes on a face — a door's reason, a
hold, a doubt, a lane's state, a signal due — leads with his part, in his
words, and then says the plain reason and what happens next without him.
The colour language (plan 27, `domain/board.py::Meaning`) already answers
"is this mine": amber is "only you can act", teal is "happening now", grey
is quiet. Today the sentence beneath the colour was written from the
machine's side ("Start waits on the plan's own word: its Sequencing names
#20; it opens by itself once every named card is in Executed or Done") and
the owner could not tell from it whether he had to do anything. The colour
and the sentence say the same thing, and both are written for him.

This holds on every project's board by construction: the sentences are the
board's own, built in `board/assemble.py`, `board/lane.py` and
`api/loops.py`, and every project on the board reads the same code.

## Items

### 1. One shape for every sentence on a face, and the shape agrees with the colour
A face sentence opens with its meaning's words — "Nothing for you" for a
quiet or live face, "Your move: <the one thing>" for an amber one,
"Happening now" for teal, "Something is wrong: <what disagrees>" for red,
"Proven" for green — then the plain reason, then what happens without him,
using no word from `docs/vocabulary.md`. The shape lives in one place in
`board/` beside `Meaning`, as a function every sentence is built through,
so the opening and the colour cannot disagree: the function takes the
meaning and the parts, never a free sentence. For #74's hold: "Nothing for
you yet. This starts by itself once #20 ships; move #20 up to have it
sooner."
Done means: `domain/board.py` or a neighbour names the openings, one per
meaning; every `_state(...)`, `_closed(...)` and `_open(...)` call and every
lane sentence in `api/loops.py` is built through the one function; a test
builds a sentence for each meaning and reads the opening; a sentence built
with a mismatched opening is refused at construction.
**Met:** `domain/meaning.py` holds `Meaning`, `OPENING` (one opening per
meaning) and `say(meaning, what, why=, then=)`, the one builder;
`CardState` refuses a detail whose opening is not its meaning's and an
amber or red face with no sentence, `Door.why`, `FaceDoor.why` and
`Lane.sentence` refuse a text with no opening (`domain/board.py`,
`domain/lane.py`); every `_state`, `_closed`, `_open` call and every lane
sentence in `board/lane.py::lane_for` goes through it (the lane sentences
live there, not in `api/loops.py` — see item 2); `tests/board/test_meaning.py`
builds a sentence per meaning, reads the opening, and shows the refusals.
The held card reads "Nothing for you: this starts by itself once #20 ships.
Move #20 up to have it sooner." — the plan's example with the opening's
colon instead of "yet", so one shape serves every meaning (commit 07c47c8).

### 2. Every sentence the board can say is rewritten to the shape, held cards and Decision moment cards first
The sixty-three state sentences in `board/assemble.py`, the door sentences
in `board/lane.py` (the hold at line 771 among them), and the lane and
rescue sentences in `api/loops.py`, each rewritten: his part, the plain
reason, what happens next. The Decision moment column's own note and the
dial's "held" tooltip in `frontend/src/components/ui/index.tsx` take the
same shape, since they are sentences he reads on the board.
Done means: a ratchet under `tests/ratchets/` reads every sentence literal
the three modules can build and refuses a vocabulary word or an opening not
in the set; it passes; on the fixture, a held card's face, a Decision
moment card's face and a running card's face each read in the shape, and a
live check of the served board shows #74's hold sentence in its new words.
Hands out: search — every sentence literal the three modules build, with
file and line; verifies the count against the ratchet's own read before the
sweep and after it.
**Deviated:** the search read forty `_state` calls in `board/assemble.py`
(the suggestion's sixty-three was a miscount, verified by `grep -c`),
thirty-eight door builders in `board/lane.py`, and none in `api/loops.py`:
that module builds history rows and machine readings that never reach a
face, so the third module of the sweep is `board/collision.py` (whose
sentence every face wraps as its reason), with `board/evidence.py`'s doubt
words beside it. Every one is rewritten (commits 07c47c8, 9746c4b); the
Decision moment note (`domain/column.py`) and the head's held tooltip take
the shape, the openings reaching the page through `needle types`.
`tests/ratchets/test_every_face_sentence_says_whose_move.py` reads every
literal handed to a builder in the three modules and every sentence the
test board builds (states, doors, lanes, the language cases, the column
notes, the tooltip) against `docs/vocabulary.md` and the openings, and
holds that an amber face opens "Your move" and no other does. The live
check of the served board is in the review record's last pass; #74's own
hold no longer exists because #74 shipped on 2026-09-07, so the check reads
a held card and a Decision moment card as the served board has them.

### 3. The open card reads the same way
When a card is opened, the state sentence replaces the essence
(`board/CardView.tsx`, `StateSentence`), so the first line he reads inside
the card is the same sentence and takes the same shape; the door buttons'
labels and their reasons (`_open` and `_closed` in `board/lane.py`) are
sentences too and are read by the same ratchet.
Done means: the ratchet of item 2 covers the door labels and reasons; on
the fixture an open held card reads "Nothing for you yet …" as its first
line and its Start door's reason in the same words.
**Met:** the ratchet reads every door's `why` on the test board and the
language cases' face doors; `frontend/tests/board.test.tsx` ("says on the
open card why a plan waits on the cards its Sequencing names") opens a held
card and reads "Nothing for you: this starts by itself once #139 …" as the
state sentence under the title and again as the Start note, the "Start is
closed:" prefix gone (`frontend/src/board/OpenCard.tsx`, commit 9746c4b).

## Acceptance criteria

- The owner reads a held card, a Decision moment card and a running card
  on each of the four boards and can say, from the sentence alone, whether
  it needs him and what happens if he does nothing.
- No sentence the board builds for a face contains a vocabulary word, and
  the ratchet holds it.
- An amber face always opens with "Your move"; no other face does.

## Rulings

- **The opening is bound to the meaning in code, not by convention.**
  Rejected: a written rule for sentence writers plus the ratchet alone. The
  colour and the sentence disagreeing is a silent failure, so the mechanism
  makes the disagreement impossible to construct (HOW-WE-WORK §5), and the
  ratchet catches the vocabulary, which construction cannot.
- **Its own card, after #74.** Rejected: folding into #74. #74 rewrites
  the corpus and widens a reading; this rewrites the board's code. One lane
  doing both would carry a high gate for the sweep and a medium one for
  this and delay the titles; they share the vocabulary file only.

## Deliberately not

- The vocabulary file is #74's; this plan adds no word to it. A word this
  sweep finds missing is a finding filed on #74's loop, not added here.
- The colour language itself (plan 27) does not change; five meanings, five
  openings.

## Loop

We think a sentence that opens with his part will let the owner tell from
the face whether a card needs him, because the colour already carried that
answer and only the words did not. We look one week after this lands: if he
asks "is there something I need to do?" about any card, or opens a card to
find out, that sentence is the finding, and the opening or the vocabulary
is changed, not the shape. If neither happens, the shape stays and the
ratchet is the record.
