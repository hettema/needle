# Every card title says what it is for at a glance, in plain words

**Carries:** docs/slice-suggestions/done/2026-09-07-a-cards-title-tells-the-owner-what-it-is-for-at-a-glance-in-his-words.md, docs/slice-suggestions/done/2026-09-05-plans-carry-no-sequence-number-the-card-is-the-one-identifier.md
**Status:** NEW — planned, not started; the owner placed it at the top of Up next on 2026-09-07.
**Written:** 2026-09-07, from Dennis reading his own board: "the card titles are very difficult for me to understand which makes the board difficult to read. What can we do to communicate the card's intent better?" and, asked what the title is for: "the intent of the card titles is for me to instantly understand the intent of the card. I am not technical so e.g. tech jargon in there doesn't help me." Then: "Let's make it a plan and put it at the top of up next in the needle board and do we also do a sweep of all the existing cards in all boards to rewrite the card titles?" — yes: the rule is doctrine (HOW-WE-WORK §10, `docs/plans/README.md` lines 43–51, his ruling of 2026-09-04), so the sweep and the reader cover every project on the board, not Needle alone. And, the same day, on #46 — which had waited on him since 2026-09-05: "plan numbering and card numbering seem to be out of sync … if we refer to a plan in the card it feels like it should be the same number" — the ruling: the card number is the one identifier, and a plan carries no number of its own. And the intent in one line, the same day: "My intent is to understand the board at a glance and understand the cards when I open them. This needs to be true for the HR, Omarchy and needle needles … the idea is to run a needle for any project reliably."
**Effort gate:** high — the code is small (one reading widened, one parser rule, one ratchet, one brief line), but the sweep rewrites some 230 live titles across four projects and every one of them is a judgment about what the owner would say, made in his absence and read by him afterwards; a title that mis-states the intent is a wrong card, silently.
**Sequencing:** after #20 (plan 08's item 1 makes a card's face follow its document's current title; read live on 2026-09-07, cards #74, #63 and #53 all show the title of the suggestion they were born from while their document is a plan, so without #20 the sweep renames documents and no carried card's face changes). Items 1, 3 and 4 do not wait on it; item 2 does.
**Class:** a ratchet on Needle's own corpus refuses a live title that uses a word the board defines, and the cold read at birth marks a title on any project's board that fails the owner's test; the failure that was silent nineteen times over is loud on the face.

## Intent

The owner ranks cards from their titles alone and directs on intent, never
mechanism. So every card title on every board says what will be true when
the card is done, in words he uses, and he can place it against every other
card without opening it — the bar `docs/plans/README.md` already sets and his
ruling of 2026-09-04 already states. Today the bar is a convention: on
Needle's board 19 of 28 live titles use a word the board or the code defines
and he does not (lane, make, fold, dial, ring, door, wall, pill, gate, scope,
corpus, fixture, migration, store), 12 run past twelve words, and the line
beneath a defect's title is the first sentence of its evidence — a path and a
function name. Every one of those titles was written by a session that had
read the rule. A boundary held by memory erodes (HOW-WE-WORK §5); this plan
makes it held.

What does not change: the title stays the outcome sentence, never a label or
an area — "Defects fix themselves", not "Defects". A card keeps its number and
its history through the rename (plan 08). Archived documents keep their
titles; the owner does not rank Done.

## The sweep covers every board

Four projects are on the board (`needle projects`): Hello Revenue, Needle,
Omarchy and Hello Revenue 3. Their live corpora on 2026-09-07:

| project | live plans | live suggestions |
|---|---|---|
| Hello Revenue | 23 | 166 |
| Needle | 9 | 20 |
| Omarchy | 6 | 8 |
| Hello Revenue 3 | 1 | 0 |

The rule that the sweep applies is the one text's, so the sweep is one act
over all four, one commit into each project's trunk, written by script from
the lane as card #60's lane wrote its docs commits. Nothing under another
project's `docs/` is quoted into Needle's tree: the synthetic-fixture ratchet
refuses Hello Revenue's real titles here, and this plan carries counts only.

## Items

### 1. The vocabulary is one file the writer and the reader both read
The words the owner does not use are the words the board and the code
define. They live in one place in Needle's corpus — `docs/vocabulary.md`, a
list with one line per word saying what the board means by it — and both the
planning brief's rule 1 (`board/brief.py`, the five rules a dial-written
plan holds) and the cold read of item 3 quote that file rather than carry a
copy. A ratchet under `tests/ratchets/` refuses a live plan or suggestion
title on Needle's own board that contains one of the words; it is the floor,
not the test — the test is the owner's ("could he place it without opening
it"), and item 3 is where that test is applied.
Done means: the file exists with at least the fourteen words named in the
intent; the brief quotes it by path; the ratchet fails on a fixture title
containing "lane" and passes on Needle's live corpus after item 2 lands;
`docs/plans/README.md` lines 43–51 point at the file as the list of words the
title never uses.
**Met:** `docs/vocabulary.md` carries twenty-five words, the fourteen among
them; `board/title.py` reads it; the planning brief's rule 1 and the filing
rule in `board/brief.py` name it by path, and the birth reading's brief
quotes it whole; `tests/ratchets/test_every_title_is_in_the_owners_words.py`
fails on "A lane the machine ended comes back by itself" and passed on the
live corpus once the sweep landed (commit 9bcd26e); the README's title
paragraph points at the file.

### 2. Every live title on every board is rewritten to the bar, and the card keeps its number
Every live plan and suggestion on the four projects is retitled: the
outcome, in the owner's words, no word from the vocabulary, short enough to
place at a glance (the archive's twelve-word titles read at a glance; the
twenty-five-word ones do not). The file stem follows the title. Where the old
sentence carried something the new title does not — the mechanism, the seam,
the second half of a compound outcome — that sentence moves into the
document's intent or observation, so the record loses nothing. A plan's
sequence number ("08 — ", "14 — ") leaves the title and the stem in the same
rename (item 5 is why); the card's number is the one the owner sees. Plan 08's
reconcile keeps the card through a rename that changes stem and title; the
lane proves it on the fixture before touching a real board. One commit per
project into its trunk, by script, each body naming this plan. A document
whose card has hands on it — a lane running, on any board — is not renamed
by the sweep: its lane owns its plan until the fold (card 50's lesson: a
plan moved on the trunk under a running lane costs the lane a rebase over
a rename), and the sweep lists what it skipped on this card so the reader
of the loop knows which titles are still old and why.
Done means: after the board's next read, no live card on any of the four
boards carries a vocabulary word in its title, and every card number that
was live before the sweep is live after it with its history intact (the
lane records the card list before and after, per project, in the review);
the owner reads the new titles on each board, and any he renames within the
week is a finding for the loop below.
Hands out: search — the list of live plan and suggestion paths with their
first line, per project; verifies the count against `ls` of each folder
before rewriting anything.
**Met:** the search role listed 193 + 35 + 17 + 1 live documents, each count
checked against `ls`; the lane retitled 149 on Hello Revenue (commit
23de0e2c1 on its trunk), 27 on Needle (9bcd26e in this lane, the three
numbered plans losing their number), 6 on the machine (1bfaf74, four numbered
stems and three titles) and none on Hello Revenue 3, each old title kept on a
`**Formerly:**` line under the head and every citation of a renamed path
elsewhere in each tree following the rename — the method for "the record
loses nothing", chosen over moving the old sentence into the intent because
it is uniform and lossless for 182 documents. Skipped, their lanes' own: Hello
Revenue #452, #459, #461, #462, the machine's #22, and this plan. Read back
from the served board after the sweep: no card born, none archived on any of
the four boards, `tools/renames_kept.py --since 2026-09-07` answers 0, and the
card numbers per project are listed in the review record; the rehearsal is
`tests/api/test_title.py`'s rename test. The owner's read of the new titles
is the loop below.

### 3. A title is read cold at its birth, and a title that fails is marked on the face
The reading that verifies a suggestion's `Fix:` mark from outside the
finder's context (plan 11; `api/dial.py::_triage`, the triage brief in
`board/brief.py`, the result through `needle triage`) reads the title too,
against the README's test and the vocabulary file, and lands the outcome as
part of its one typed result. A plan gets the same read when it is carded,
through the same reading session, since a plan's title becomes the card's
the moment it lands. The read covers the title and the essence line beneath
it (the first sentence he reads on the face, and the first line inside the
open card), since he opens a card to understand it and the title alone is
not the whole face. A title that fails puts a machine fact on the card's
face — the reader's words for what he could not place, with the words that
failed — and closes the Start door until a title passes: Start is the one
door every project's card goes through, so the refusal holds for Hello
Revenue, Omarchy and Hello Revenue 3 by the same mechanism as for Needle,
with nothing to copy into a project. The fact and the hold clear on the next
read of a title that passes. The reading is the same session as the mark's
reading, never a second one, and it never rewrites the title: the writer
does, and the reader reads again.
Done means: on the fixture, a suggestion born with "lane" in its title
shows the mark on its face after one reading, a suggestion retitled to the
bar shows none after the next, and a plan carded with a vocabulary word in
its title shows the same mark; a marked card's Start door is closed with
the mark as its reason and opens on the read that clears it, on the
fixture and on a second fixture project, so the hold is proven to be the
board's and not one project's; the mark's evidence names the reading's
session and the words; `board/triage.py::routing_of` is untouched — the
title reading changes no routing, only what the face says.

### 4. The line under a defect's title names the intent it breaks, never where the code is
`board/parse.py::essence_of` takes the first sentence of a plan's intent
and, for a suggestion, the first sentence of its body — for a defect, the
evidence. The essence of a suggestion becomes the first sentence of its
"The intent it breaks" section when it has one, and the first sentence of
the body otherwise; and no path, function name or backticked term reaches
the face of a closed card: a sentence that contains one is not the essence,
and the next sentence is tried. The suggestion grammar in `board/brief.py`
and `docs/plans/README.md` names the section so writers put it there.
Done means: on the fixture, a defect with the section shows that sentence
on its face and a defect without it shows its first path-free sentence; a
live check of the served page reads a defect card's face with no backtick
in it; the parser tests cover both.

### 5. The card number is the one identifier, and a plan carries no number of its own
Needle's and the machine's plans carry a sequence number in the stem and the
title, and cite each other by it in prose; the board numbers cards at birth,
per project, so the two sequences drift for good the first time a suggestion
is carded (plan 08 is #20, plan 12 is #36, plan 16 is #42; the machine's
plan 15 is omarchy #17). Two identifiers for one thing, born in two places,
is the registry drift the doctrine refuses, and the owner clicks cards, not
filenames. So: a plan takes a dated stem with no sequence number, both
`docs/plans/README.md` files (Needle's and the machine's) say so and why, and
prose written from here on cites a card (`#20`) or a stem, never "plan 08".
Existing citations in the archive and in code comments stay: a rename of a
`done/` plan costs every citation, and the archive is not ranked. The
ratchet of item 1 also refuses a live plan on Needle's own board whose title
or stem begins with a sequence number.
Done means: no live plan on Needle's or the machine's board carries a number
in its stem or title; both READMEs state the rule with its reason; the
ratchet fails on a fixture plan stem `2026-09-07-17-…` and passes on the live
corpus; the planning brief in `board/brief.py` names the card number as the
way to cite a plan.
**Met:** Needle's three numbered plans and the machine's four are renamed
(9bcd26e here, 1bfaf74 there); both READMEs carry the rule with the ruling's
reason and the machine's plan-write skill names it in one line; the ratchet's
own test fails `2026-09-07-17-x` and the live corpus passes; the planning
brief's rule 1 says a plan is cited by its card number.

## Acceptance criteria

- No live plan carries a sequence number, and a reader citing one cites the
  card.

- The owner opens each of the four boards and places every live card from
  its title, without opening any; a card he has to open is the loop's
  finding.
- No live title on any board contains a vocabulary word, and the ratchet
  holds it on Needle's own corpus.
- A new suggestion or plan with a jargon title is marked on its face by the
  next reading, and the mark clears when the title is fixed.
- No defect's face shows a path or a function name beneath its title.
- Every card that was live before the sweep is live after it, same number,
  same history.

## Rulings

- **The title stays a sentence, not a label.** Rejected: short area labels
  ("Titles", "Codex skills") with the outcome moved to the line beneath.
  The README's test is placing the card against every other card; an area
  label cannot be placed, and the owner's ruling asks for the intent, which
  is an outcome.
- **A word list is the floor, a cold read is the test.** Rejected: a word
  list alone. A title can avoid every listed word and still say nothing he
  can place; and a check that pins a list freezes today's vocabulary
  (HOW-WE-WORK §5: mechanise the intent, never the method). The list catches
  the cheap failure loudly; the reader applies his test.
- **The sweep covers every project, once, from this lane.** Rejected: one
  sweep per project, each on its own card. The rule is the one text's, the
  vocabulary is one file, and four lanes would learn the register four
  times; one lane learns it once and the owner corrects it once.
- **The board is the check for every project; nothing is copied into a
  project.** Rejected: a ratchet each project carries in its own test
  suite. The owner's intent is that a Needle runs for any project
  reliably, and a check a project has to adopt is a convention with extra
  steps — Hello Revenue 3 has no test suite for it to live in. Needle's own
  ratchet (item 1) is Needle's floor for its own corpus, because its tests
  can read its docs; the mechanism for all four boards is the cold read
  and the closed Start door of item 3, one code path, read by every
  project's card. A project may add its own floor and say why in its own
  instructions; none has to.
- **The reader marks, never rewrites.** Rejected: a reading that retitles a
  failing document itself. The title is the owner's intent in a session's
  words; a second session overwriting the first's guess is two guesses, and
  the writer who holds the evidence is the one to rewrite.

## Deliberately not

- Archived plans and suggestions under `done/` keep their titles, their
  stems and their numbers; "plan 08" in an archived document or a code
  comment is not rewritten.
- The doctrine text is not edited; the rule already exists there.
- Card numbers are never reassigned; a card that would be reborn is a defect
  in plan 08's reconcile, filed, not worked around.

## Loop

We think a title written to the bar and held by a cold read will let the
owner place every card without opening it, because the rule was right and
only unheld. We look one week after the sweep lands on each board: if he has
opened a card to learn what it is about, or renamed one, that title is the
finding — the vocabulary or the bar is wrong, and the reader is changed, not
the rule. If no card was opened for that reason and none renamed, the method
stays and the ratchet is the record.
