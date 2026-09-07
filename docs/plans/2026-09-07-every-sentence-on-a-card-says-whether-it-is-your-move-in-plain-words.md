# Every sentence on a card says whether it is your move, in plain words

**Carries:** docs/slice-suggestions/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md
**Status:** NEW — planned, not started; the owner placed it third in Up next on 2026-09-07, after #20 and #74.
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

### 3. The open card reads the same way
When a card is opened, the state sentence replaces the essence
(`board/CardView.tsx`, `StateSentence`), so the first line he reads inside
the card is the same sentence and takes the same shape; the door buttons'
labels and their reasons (`_open` and `_closed` in `board/lane.py`) are
sentences too and are read by the same ratchet.
Done means: the ratchet of item 2 covers the door labels and reasons; on
the fixture an open held card reads "Nothing for you yet …" as its first
line and its Start door's reason in the same words.

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
