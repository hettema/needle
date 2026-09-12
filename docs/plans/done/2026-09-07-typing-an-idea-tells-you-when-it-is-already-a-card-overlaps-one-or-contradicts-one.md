# Typing an idea tells you when it is already a card, overlaps one or contradicts one

**Carries:** docs/slice-suggestions/done/2026-09-05-a-plan-or-a-defect-is-born-knowing-the-live-cards-on-its-ground.md
**Status:** DONE — shipped 2026-09-12 by the lane on card #69 (review record: docs/reviews/2026-09-12-typing-an-idea-tells-you-when-it-is-already-a-card-overlaps-one-or-contradicts-one.md).
**Written:** 2026-09-07, at the board's Idea door (conversation 206dd83f), on the owner's ruling in that conversation: "can you not write the plan? You have context so it feels like you're better positioned than the clean plan agent." The words that asked for it, twice at the same door: 2026-09-05, "I'm worried we're trying to solve the same thing in similar ways which goes against our working doctrine … cards that smell of planning drift either folded or aware of each other"; 2026-09-07, "when I enter a card to any needle board I don't have full understanding of the open cards in that project. What if I suggest a plan it has massive overlap with another plan? Is that a bad thing? I'm for example concerned about me contradicting myself." A colleague of another make (Codex 0.153.4, read-only, two rounds, 2026-09-07) read the finding cold: its corrections are in the suggestion, and its objection to a plan written at the door is ruling 1. Amended 2026-09-08 at the card's Discuss door, on the owner's words there: ruling 8, the look at the moment of filing in item 2, and who clears a counted document in item 1.
**Effort gate:** high — the code is four readers widened (the corpus read against itself, the briefs, the head's claims, the Sequencing verdict) with a fixture test each and a page change behind them; the judgment is what counts as a neighbour and what the door says about one, and a reading that gets it wrong is silent: a door that names no neighbour looks exactly like a door with none to name.
**Class:** the head counts live documents beside a neighbour they do not name, as a broken claim beside "document without card", on every board; and a reader of another make reads the first ten births after the fold for conflicts missed, invented or silently chosen (the Loop), so a wrong reading is loud within three weeks, never silent.
**Formerly:** The door tells you when your idea is already a card, overlaps one or contradicts one, and nothing is born blind to its neighbours (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)
**Challenged:** 2026-09-12, by claude (opus on gmail, session c288acc6, call 109): 9 material corrections before build

## Intent

The owner types an idea into a door that shows him nothing, on a board that
already holds forty cards he cannot hold in his head, and he should not have
to. The board is the team's memory (HOW-WE-WORK §11); finding the live cards
an idea touches and reading them against it is the colleague's work, and
choosing between two intents the record does not settle is his (§1). Today
every writer of a document is blind: the Idea door's session gets his line
and nothing else, the dial's planning session gets one defect, a review lane
files one finding, and the twelve documents of 2026-09-05 — four things
written twelve ways — and the owner's own idea brought twice to the same
door are the result. The board already reads shared ground for lanes and
shows it as a cost; it reads nothing when a document lands.

Two classes, and the second is the one the owner fears. *Shared ground* is
two documents on the same files: the fold settles it and it is never a
reason to wait (`docs/INTENT.md` lesson 4). *Contradiction* is two intents
that cannot both hold — two "done means" that cannot both be true, or a new
ask that reverses a live plan's ruling — and it lives in the words, not the
files; a reading by paths is blind to it and only a session reading the
intents can judge it. A changed intent is his to change; an incompatibility
nobody noticed is the board's defect, not his. So after this plan: every
document's neighbours are read at birth, by paths and by words; every brief
that writes a document carries them by intent; the Idea door's first reply
says of each one whether the idea is already that card, sits beside it, or
contradicts it — and a contradiction comes back to him as one question he
can answer cold, never as a refusal; and a Sequencing line the board cannot
place says so instead of silently being prose. A duplicate — the same
card under another name — folds into the card that holds it, by whoever
finds it, with the new evidence under that card's own heading and a line
saying so; only a contradiction is his (ruling 8).

What does not change: nothing refuses a birth, nothing waits on shared
ground, the board never says "contradicts" on its own (ruling 3), the one
hold stays the plan's own Sequencing word, nothing born while he is
away waits for him (ruling 8), and the owner ranks.

## Items

### 1. Every live document's neighbours are read on every corpus read, by paths and by words, and the head counts the ones nobody named
The corpus is read whole on every change (`infrastructure/corpus.py`);
lanes' ground is read by `board/collision.py::footprint` (the backticked
paths a document names that exist) and shown as a `Readiness` of `shares`
on the Start door (`board/lane.py`, `domain/lane.py`). This item adds one
pure reading in `board/`, beside `collision.py` — which reads lanes editing
now — and `sequencing.py` — which reads a plan's own word — since nothing
yet reads a document against the other documents (the search: those two,
`reconcile.py`, which reads identity, and `triage.py`, which reads a mark;
none reads neighbours). For one live document it names the live documents
that share its footprint, with the files; and for a document whose
footprint is empty — every idea typed at the door names no file — the
nearest live documents by the words of its title and intent
(`Document.title`, `Document.intent`, `Document.essence` in
`domain/document.py`), as candidates, never as a verdict. A document
*names* a neighbour when its text cites the neighbour's card (`#N`) or its
path anywhere — a `Carries:` line, a `Sequencing:` line, or prose (ruling
4). The reading lands on the card's face and open view the way `shares
ground with #N` does for a lane, and in the head as a claim in the broken
list (`Claim` in `domain/board.py`, counted and filtered like "document
without card", plan 27's pattern): live documents beside a neighbour they
do not name. The count names the
failure, so the row says who clears it: for a defect, the reading that
verifies its mark (item 2) folds it into the neighbour or cites it; for a
plan, the owner, from the row on the card, when he ranks (ruling 8).
Done means: on the fixture (`tests/fixtures/harbourmaster/docs/`), a
suggestion born naming a file a live plan's Terrain names shows that plan's
card and the files on its own card; a suggestion naming no file but a live
plan's words shows that card as a candidate, said as a candidate; a plan
that carries or cites the neighbour clears the count; the row says who
clears it — the reading for a defect, the owner for a plan; the head's count
reads on the served page and filters the board to the cards carrying it;
the types are regenerated (`needle types`), the frontend fixture rebuilt
(`tools/board_fixture.py`), `tsc` and `vitest` clean; and after the fold —
types, fixture, dist, service restart, in that order — the served Needle
board shows the count and the row on a real card, read by hand in the
review record.
Hands out: search — every live document on the four boards with the paths its text names and the words of its title and first intent sentence, to size the reading and choose the word rule; verifies three of the documents by opening them before the rule is chosen.
**Met:** `tests/board/test_neighbours.py` reads the fixture: the slip defect, which names `office/pricing.py`, sits beside the two pricing plans whose Terrain names it, with the file and their intent sentences; the waiting-list defect names no file and shows the waiting-list plan as a candidate, said as one, never counted; a document that cites the neighbour's card, carries it by a plain path or names it on its Sequencing line clears the count; the row names who clears it and by what act (the reading for a defect, a session on it for a plan). `tests/api/test_doors.py::test_a_document_born_beside_a_neighbour_it_does_not_name_is_counted_and_the_row_says_who_clears` births a defect on the fixture, reads the count on the head, the same reading on the board and the open card, the head's filter, and the count clearing when the document names every neighbour. Types regenerated, the fixture rebuilt, `tsc` and `vitest` clean; `frontend/tests/board.test.tsx` renders the line on the resting card, the list on the open one and the head's count and filter. The sizing the item handed to the search role and the lane's own measurement (`board/neighbours.py`'s docstrings carry the numbers) chose the rules: glue at 8% of the live corpus, a rarity floor that scales with the board; three documents opened before the rule (this plan, the fixture's gate-code plan and its slip defect). The served board after the fold: recorded in the review record's last section — the count on Needle's head and the row on a real card, read by hand.

### 2. Every brief that writes a document carries the neighbours, by intent
Five briefs write documents and none carries a neighbour: the dial's
planning brief (`board/brief.py::planning_brief`), the reading brief and
the lane brief through the filing rule (`board/brief.py::reading_brief`,
`board/brief.py::filing_rule`, `api/doors.py::brief_for_lane`), and the
Idea and Discuss doors (`api/doors.py::idea_brief`, `api/doors.py::discuss`)
— `neighbours_text` there lists lanes with hands on, never documents. Each
brief gains the live documents on its subject's ground or words, from item
1's reading, one line each: the card, its title, the first sentence of its
intent, its files, and its rulings where the plan has a Rulings section.
The planning brief also hands the session every live defect on the same
ground and says what a plan does with a neighbour: carry it, sequence after
it, or cite it and say in the head why the plan is whole without it — so
one plan for a class is the default and one plan per instance the
exception. The filing rule (`board/brief.py::filing_rule`) is read an
hour after the lane's brief, about a finding on ground the card never
touched, so the neighbours the brief carried are the card's and not the
finding's: the rule says look first — before it writes, the session reads
the live defects and plans on the finding's own paths and words, appends
the new evidence under the heading of a card that already holds the bug
instead of writing a second file, and cites by card or path a neighbour on
shared ground in the file it does write. The head's count from item 1 is
what proves the look happened (ruling 8). The reading that verifies a mark
(`board/brief.py::triage_brief`,
`board/triage.py`) reads the neighbours too: a `now` on a document whose
ground a live plan already covers lands as `when` on that plan's card, in
the result vocabulary plan 59 gave the reading, not as a second `now`.
Done means: the brief tests (`tests/board/test_brief.py`,
`tests/api/test_doors.py`, `tests/api/test_dial.py`) read a fixture where a
live neighbour exists and each of the five briefs names it with its card
and intent sentence; the planning brief's three dispositions are in its
text; the filing rule's text says to read the finding's own neighbours
before writing and to append to a card that already holds it, read by
`tests/board/test_brief.py` in every brief that carries the rule; and on
the fixture a triage reading of a `now` whose files a live
plan's Terrain names lands `when` on that plan's card
(`tests/api/test_triage.py`).
Hands out: execution — the backend and frontend suites after the brief change (`uv run pytest -q`, `npx vitest run --root frontend`), every failure verbatim; verifies by re-running the one failing test it reports before acting on it.
**Met:** `tests/board/test_brief.py::test_every_brief_that_writes_a_document_carries_the_neighbours_by_intent` reads the neighbour line — card, title, intent sentence, path, ground, rulings — in the reading brief, the planning brief and the mark's reading, the three dispositions in the planning brief, the look-first sentence in the filing rule (and so in every brief that carries it), and the `when` trigger's shape through the one signal parser; `tests/api/test_doors.py::test_the_discuss_door_and_the_lane_brief_carry_the_live_documents_beside_the_card` reads the lane brief and the Discuss door on the fixture; `tests/api/test_dial.py::test_a_now_on_ground_a_live_plan_covers_is_read_with_the_plan_beside_it_and_lands_when` opens the reading on a `now` defect naming `office/pricing.py`, which the fixture plan's Terrain names, reads the plan on its brief, lands `when` with a trigger on that plan's card through the triage verb, and reads the planning brief with the plan and the defect beside it. The triage test the item named `tests/api/test_triage.py` lives in `test_dial.py`, where the seat's helpers are.

### 3. The Idea door's first reply names each neighbour and what it is to the idea, before anything is written
The opening line is not a document yet, so item 1's words read runs on the
line itself in `api/doors.py::idea` — the door has the live corpus in hand
(`self.live`) — and the brief carries the neighbours it finds, with the
instruction the session's first message answers: for each neighbour, say
whether the idea is already that card under another name (with the card),
compatible work on shared ground (named, never waited on), or a
contradiction — two intents that cannot both hold — and put a contradiction
to the owner as one question with what is true today, both outcomes, what
turns on each, and a recommendation. The session judges; the board only
retrieves (ruling 3). The Discuss door's brief carries the same for its
card. The page's door stays one input (`IdeaDoor` in
`frontend/src/components/ui/index.tsx`): the comparison comes in the reply,
after he has typed, never as a condition of typing.
Done means: the Idea door test in `tests/api/test_doors.py` opens the door
with a line that shares a live fixture suggestion's words, and the brief
names that card with its intent sentence and the three-way instruction; an
empty line gets the ask and no neighbours, as today; the first live Idea
door conversation after the fold names a neighbour in its first message or
says none is on the ground, and the review record quotes it.
**Met:** `tests/api/test_doors.py::test_idea_opens_a_conversation_the_rail_lists_and_a_document_it_writes_is_born_from_it` opens the door with "the waiting list should remember who asked first for a berth" and reads the fixture's waiting-list card, its intent sentence and the three-way instruction in the brief; the empty line gets the ask and no neighbours; a line near nothing gets the ask and one clause saying so. The first live Idea door conversation after the fold is the owner's to have: the close's WATCH row reads it (a session reads the first idea conversation's first message after 2026-09-12), and the review record quotes it when it has been had.

### 4. A Sequencing line that means a hold is one, or the card says it is not
`board/parse.py::sequenced_cards_of` reads a Sequencing line's leading
names and `board/sequencing.py::waits_for` stops at the first it cannot
place; a plan number with no `#` ("after 11 … and after 08") or a card no
board holds is prose, and the writer's hold silently never held. A line
whose leading words name a plan the board cannot place gets a verdict on
the card in the voice of an unreadable gate — the way a plan with no gate
reads "no gate" (`StartState` in `domain/lane.py`, the pill in
`board/lane.py`) — and the head counts it with the unreadable, so the
writer or the owner fixes the line rather than discovering the lane started
early.
Done means: on the fixture a plan with `**Sequencing:** after 08 and 11`
shows the verdict line and its Start pill says so; `after #8` holds as
today and opens when #8 ships; both forms are in
`tests/board/test_sequencing.py`; the verdict's words are on the page.
**Met:** `tests/api/test_doors.py::test_a_sequencing_line_naming_a_card_in_flight_holds_start_until_it_ships` writes `after 08 and 11` on the fixture's metered plan and reads the closed Start door's sentence, the pill `hold unread` with `['08', '11']`, the face word in the broken colour and the head's count; `after #241` holds and opens when #241 ships in the same test; both forms and the loose reading are in `tests/board/test_sequencing.py::test_a_line_that_means_a_hold_the_board_cannot_place_says_which_names`; the page renders the `hold unread` case from `tools/board_fixture.py`'s language table in `frontend/tests/board.test.tsx` ("the colour language"). One tightening beyond the letter: a `#N` no board holds keeps today's self-clearing wait, and only a name after a hold word counts, so "beside #15" stays shared ground (the challenge's correction).

## Terrain

The reading: `board/collision.py` (its `footprint` reused, its lane verdict
untouched), a new reader beside it in `board/` (named by the lane after the
search above), `domain/document.py`, `domain/board.py` (`Claim`), the
neighbour shape in `domain/` (the search: `Collision` and `Readiness` in
`domain/lane.py` are a lane's; a document's neighbours are a new shape,
born after that search), `board/assemble.py` (the face line and the head's
claim). The briefs: `board/brief.py`, `api/doors.py`, `api/dial.py`,
`board/triage.py`. The hold: `board/parse.py`, `board/sequencing.py`,
`board/lane.py`. The page: `frontend/src/types/*.ts` by `needle types`,
`frontend/src/board/CardView.tsx`, `frontend/src/board/OpenCard.tsx`,
`frontend/tests/fixture.json` by `tools/board_fixture.py`. The tests:
`tests/board/test_collision.py`, `tests/board/test_brief.py`,
`tests/board/test_sequencing.py`, `tests/board/test_assemble.py`,
`tests/api/test_doors.py`, `tests/api/test_dial.py`,
`tests/api/test_triage.py`, and fixture documents under
`tests/fixtures/harbourmaster/docs/plans/` and
`tests/fixtures/harbourmaster/docs/slice-suggestions/`. No doctrine file and
no grammar change: `docs/plans/README.md` is not touched (ruling 4).

## Acceptance criteria

- On every board, a live document beside a neighbour it does not name is
  counted on the head and shown on its card with the neighbour and the
  ground — files, or words said as candidates.
- Every brief that can write a document carries the live neighbours by
  intent; a plan the dial writes carries, sequences or cites each one; a
  `now` whose ground a live plan covers routes as `when` on that plan.
- The Idea door's first reply names each neighbour as the same idea,
  compatible work, or a contradiction put to the owner as one question; the
  owner never reads the backlog first, and the door stays one input.
- A Sequencing line the board cannot place says so on the card and the head.
- Nothing refuses a birth; nothing waits on shared ground alone; the one
  hold is still the plan's own Sequencing word.

## Rulings

- **Written at the door, at the owner's word.** The other make objected that
  a plan written at the door skips the independent reading of the mark and
  that the dial's planning session derives done means from the suggestion
  and adds no scope. The owner ruled in the conversation: the session with
  the context writes it. So the done means above come from the carried
  suggestion's "What would hold it" and its three acceptance sentences and
  nothing more, and his click at the effort gate is the reading. Rejected:
  waiting for a dial that is off, with 22 unverified marks ahead of this.
- **Shown, never enforced.** A neighbour is a row and a count, never a
  refusal or a hold (`docs/INTENT.md` lesson 4; ruling 3 of the many-lanes
  plan: terrain inference is the lock under another name). Rejected: a
  Start that waits on a neighbour, and a birth the board refuses.
- **Words are retrieval, never judgment.** The words read names candidates;
  the session with the neighbours in front of it judges same, compatible or
  contradiction; the board never writes "contradicts". From the other
  make's read: two wordings can carry incompatible intents and one wording
  two compatible ones, so a word match that judged would be wrong both
  ways. Rejected: a similarity score on the card.
- **Naming is citing.** A document names a neighbour by citing its card or
  path anywhere in its text. Rejected: a third head field beside `Carries:`
  and `Sequencing:` for "beside, whole without it" — a third relation would
  be a third form to teach on every project, and a citation is what every
  writer already does.
- **A contradiction is a fork, never a refusal.** A changed intent is the
  owner's (§1); the failure is nobody noticing. The door asks one question
  he can answer cold. Rejected: the door declining to write until he
  resolves it.
- **One footprint, two readers.** The footprint reading is shared with the
  lane reader; the verdicts stay apart because one is about edits in
  progress and the other about documents at rest. Rejected: widening
  `Collision` to documents, which would put a document's neighbours on the
  Start door where they read as a lane's collision.
- **Shared ground with running lanes is the fold's.** #74's lane is in the
  parser and the briefs today, and #72 adds a head field the parser reads;
  this plan names no hold on them. The second to fold rebases.
- **A duplicate folds; only a contradiction is his (Discuss door,
  2026-09-08).** The owner's intent in his words: "keep the needle boards
  clean by not adding duplicate cards; when a card is being created and a
  duplicate is detected we backbrief together." Sharpened in the same
  conversation and agreed. A duplicate — the same card under another name
  — is one of three neighbours and the easy one: whoever finds it folds
  it, adding the new evidence under the existing card's own heading, and
  says it did; that applies a rule already written (one way to do each
  thing) and is execution under §1, never a decision parked for him. A
  neighbour on shared ground is named, never waited on. A contradiction —
  two intents that cannot both hold — is the one that reaches him, as one
  question. "Together" means at the door: the Idea door's first reply is
  that backbrief, before anything is written. A card born while he is away
  — a review lane filing a defect, the dial planning one — never waits for
  him: a duplicate folds, a contradiction lands on the card as a question
  for him, and the board moves on. Rejected: a birth that waits for a
  backbrief, which rebuilds the eight parked decisions §1 was shaped by.
  Also settled at the door: the look at the moment of writing is a
  convention — the brief says look first, and no verb writes a document,
  so there is no door to refuse at — while the count after landing and the
  reading before routing are the mechanisms; by HOW-WE-WORK §5 a failure
  that shows loud on the head within one read may stay a convention.

### From the challenge before build (2026-09-12, call 109)

A colleague of the same make with no share of the lane's context read the
plan and the lane's design cold and measured the reading over Needle's 63
and Hello Revenue's 224 live documents. Nine corrections, each landed
here because the plan's letter would have failed its intent:

- **Ground is what a document names, not what exists.** The lane reads
  neighbours by the paths a document names whether or not the file exists
  today: two plans naming a file one of them will create share ground, the
  reader stays pure, and the fixture project has no source tree, so the
  done-means could not be tested through `footprint`'s existence check.
  Cost named: a mistyped or long-renamed path is ground too.
- **A path or a word nearly every document shares is not ground.** The
  challenge measured 199 file-ground pairs on Needle and 671 on Hello
  Revenue, nearly all through the few core files every plan names, and a
  word rule of "two shared words" gave a median of 21 neighbours per
  document on Needle. One rule for paths and words alike: what a large
  share of the project's live documents name is glue, not ground — the
  cut is a share of the live corpus, read per project on every read, never
  a hand-kept list, so `docs/plans/README.md` drops out and a live plan
  three documents cite stays. Words are scored by rarity in the project's
  own live corpus, a candidate needs a floor the measurement set
  (`board/neighbours.py` carries the numbers), and the three shown are
  ordered by score then card number so the list never flickers between
  reads. Rejected: a blanket drop of `docs/` (loses the real citations of
  a live plan), and a hand-written stop list (the glue is the project's
  own nouns).
- **The count starts at the reader's birth.** Fifty of Needle's 63 live
  documents, and 156 of Hello Revenue's 224, would carry the claim on day
  one — documents born blind before any brief carried a neighbour, which
  is not the failure the count exists to show, and fifty rows on the
  owner's pile is the eight parked decisions §1 was shaped by, sixfold.
  So a document counts only when its card was born on or after the
  reader shipped (`board/neighbours.py::COUNTED_FROM`); older documents
  show their neighbours on the card and in every brief as a quiet fact,
  and the Loop's "expect 0" reads the count as a claim about births.
- **Naming is every form a writer already uses.** A `Carries:` line is
  written without backticks four times in six on Needle, and a
  Sequencing name is read by its own parser; so a document names a
  neighbour when its text cites the neighbour's card (`#N`), its
  Sequencing line names it, or the neighbour's document path appears
  anywhere in the text, backticked or plain.
- **The row names an act the board can see.** "The owner clears it when he
  ranks" asked for an act that edits nothing: ranking moves a card and
  the claim lifts only when the document names the neighbour. The row says
  what clears it — cite it, carry it, or fold this card into it — and for
  a plan, that Discuss puts a session on it that can; for a defect, the
  reading that verifies its mark.
- **A word candidate never counts on the head.** Every document shares
  words with something, so a count that included candidates could never
  reach the Loop's zero; only file ground counts, and a candidate shows on
  the card and in the briefs said as a candidate (ruling 3).
- **`after #999` is not unplaced.** A `#N` no board holds yet holds today,
  loudly and self-clearingly ("starts by itself once #999 (not on the
  board) ships"), which is the shape of a card not yet born; item 4 reads
  as unplaced only the names the grammar genuinely loses — a bare number,
  `plan N`, and `<Words> #N` whose words are no project's — and carries
  the tail the strict reading dropped after the first such name, since
  "after HR #409 and #123" silently held nothing.
- **The block goes into the briefs that write, not into `render`.**
  `render` is read by `needle card`, the Plan door per carried card and
  the Execute door; the neighbours block is its own function composed into
  the five briefs item 2 names and the Idea door, and the Plan door gets
  it once.
- **The trigger a reading writes costs no session.** A `now` on ground a
  live plan covers lands as `when` with a `command` trigger that reads the
  plan's card column through `needle card`, never a `session` row that
  opens a windowless reading every two days per routed defect.
- Also settled: the Idea door's three-way instruction replaces its existing
  "say when it is already in the corpus under another name" sentence
  rather than sitting beside it; `#N` is read by the parser's one card
  reference; the rulings a brief carries are the bold leads under a plan's
  `## Rulings` heading, which is Needle's shape — a board whose plans keep
  rulings in a bold numbered list carries none, as the item's "where the
  plan has a Rulings section" already allows.

## Deliberately not

- The open cards listed beside the Idea door for the owner to read first:
  that makes the door a reading task and hands him the retrieval.
- Neighbours across boards: the reading is per project. A document that
  names another board's card does so in the Sequencing grammar the board
  already reads (`Needle #20`), and cross-board knowledge is #21 — the
  `his` idea on cross-repo sharing — not this plan's.
- The dial, the triage seat and the 22 unverified marks on Needle's rail:
  a fact for the owner, not this plan's.
- Rewriting the twelve documents of 2026-09-05: they fold or name each
  other already (the commit that filed this class did that), and item 1
  counts any that still do not.
- Any change to what a plan must contain: no grammar, no README, no
  doctrine.
- A filing verb that shows the neighbours before it writes, the one hard
  door at the moment of writing: a new primitive, its own card (ruling 8).

## Loop

We think reading every document's neighbours at birth and carrying them by
intent into every writing brief will end documents born beside a neighbour
they do not name, and will catch a contradiction at the door rather than
after a lane started, because every one of the twelve of 2026-09-05 was
written by a session that would have read a row had one existed, the dial's
planning session writes what its brief carries, and the door conversation of
2026-09-07 caught its own card only by a hand search its brief could have
spared it. If the head's count is not at zero two weeks after the fold, the
brief is not being read and the hold moves to the mark's reading (item 2's
`when`). Naming alone is not success: a reader of another make reads the
first ten documents born after the fold across the boards, and every Idea
door conversation in that window, for three things — conflicts missed,
conflicts invented, and choices between intents made silently for the owner
— and one occurrence of any fails the thesis: the retrieval or the judgment
that produced it is corrected and the next ten births are read. If the ten
births show no real conflict at all, the live effect is unproven and this
stays a belief, reported as one. If a door birth shows no neighbour and the
reader finds one by hand, the words read is too narrow and widens.

Loop: live documents beside a neighbour they do not name, on every board — session read the head's count on Needle, Hello Revenue and the machine expect 0 by 2026-09-28 every 2d
Loop: the first ten documents born after the fold and every Idea door conversation in the window, read for conflicts missed, invented or silently chosen — session codex by 2026-09-28
