# You name what matters now, a colleague finds what holds it back, and the board sorts every card by whether it moves that

**Status:** NEW — planned, not started; waits for the owner's rank.
**Written:** 2026-09-07, from the owner's idea in the interactive Needle session d03a7b55, discussed in three rounds with a colleague of the other make (Codex 0.153.4, read-only, reasoning effort high); the whole exchange, every Codex line verbatim, is `docs/design/2026-09-07-the-focus-of-a-project-discussed-between-two-makes.md`. His words: "One of the challenging thing for humans is to understand what the most impactful next step is in all the work that's on the board. I am a huge believer in the theory of constraints and Alex Hormozi has a great framework he uses which is 'why can't we do More?' … what if we have a 'sort on intent' or something function on the board. … My intent is for the work we do to be the most impactful work." Then: "my intent is for this to work for any project that uses needle to organise." Then, on the design: "How about moving the constraint into the needle board itself as an input? … nailing the key priority is something that will require some back briefing I guess? Maybe it breaks off into a session to then land on whatever is jointly decided? … There are two languages here: constraints and priorities and they feed into each other. Choosing the wrong priority never fixes the constraint but fixing a constraint in something that doesn't move the prioritised thing is also a failure." And: "what happens when cards are missing that should be there? … it would be awesome if you guys find I'm just not seeing the highest leverage thing because I didn't think of it … I believe hormozi goes through each M, finds a solution in one, then asks something like 'what else can we do that costs x and takes y time that has a higher likelihood of impact'." He ruled to plan it on 2026-09-07: "I think we should turn it into a plan." After a hand simulation the same evening he ruled the sort crosses columns: "Did you move anything from planned into up next? I mean, in my mind the sort reorganises the board. Moves things out of up next, pulls plans or suggestions/bugs forward etc." and "yeah I think it should go across all lanes and reorder based on intent … Can I then still go back to the old state if I want to? Kinda like the age and gate buttons?"
**Effort gate:** high — the code is one document reader, one door with a typed purpose, two typed readings in the shape plan 59 already has, one lens and one strip; the judgment is the seam both makes named as the hard part: a diagnosis, a verification, a ruling, a per-card judgment and an outcome reading all bind to versions of things that change under them, and a page that shows yesterday's judgment in today's voice is the one lie this board exists to refuse. A wrong sort costs him a glance; a stale sort shown as current costs him the decision it was built to inform.
**Sequencing:** none holds this. Beside `docs/plans/2026-09-05-16-every-loop-a-plan-names-is-watched-until-it-closes.md` (this plan's `Loop:` lines are read as prose until that one folds, and become WATCH rows at the close after it) and `docs/plans/done/2026-09-07-every-sentence-on-a-card-says-whether-it-is-your-move-in-plain-words.md` (the leverage words on a card face take whatever shape that plan settles for a reading's words; if it lands first, this plan uses its shape, if not, this plan's words are one more sentence for it to fold).
**Class:** a ratchet refuses any import of the leverage result under `api/dial.py` or `board/dial.py`, and a test refuses a chosen focus whose document fingerprint differs from the ruling's; a wrong order is a lens away from his rank and never a lane.

## Intent

The owner ranks by position and gates what enters execution (`docs/INTENT.md`,
"The owner's side"); what the board cannot tell him today is which of the
cards on the plate moves the thing that limits the project right now. The
theory of constraints says one thing binds at a time and work on anything
else is a mirage; his own prioritisation brain says it
(`/home/dennis/Work/dennis-os/references/constraints.md`, adopted 2026-06-07),
and the first Hello Revenue board ranked by it — "distance to one named
constraint at a time, a written sentence the owner ratifies" (card #138,
`/home/dennis/Work/hellorevenue/docs/board/done/README.md:560-583`, ratified
2026-08-31). That rule lived in the old board's README and died with the old
board on 2026-09-04; nothing on Needle holds it.

After this plan every project on the board can carry a **focus**: two
sentences, *what matters now* and *what is holding it back*. The first is his
outcome with a number; the second is a colleague's diagnosis with its
evidence, the rival it rejected and the test that would show it wrong. He
types the first as a line on the board; a conversation sharpens it and finds
the second; a reader of the other make checks the diagnosis cold; he chooses
it with one click. Then an independent reading lands, per open card, whether
the card helps remove the limit, protects progress, does not address it, or
needs evidence, and how likely it is to work; a **Leverage** lens orders every
column by that, cheapest likely relief first, his rank unchanged underneath.
The strip at the head says which focus the board is sorted on, how many cards
are read, and whether anything queued removes the limit at all; when nothing
does, the conversation can propose moves, each written as a suggestion he
sees as a card. Two numbers, the outcome's and the bottleneck's, are watched
on the diagnosis's own cadence, so a focus that stops being true says so on
the page before anyone sorts by it.

What does not change: who ranks, who starts. The lens never writes rank, the
dial never reads it, no session here starts a lane or changes his sentence,
and a project with no chosen focus shows his rank and says why.

## What was searched before naming anything new

The concept searched: "the thing a project is optimising right now", "a
judgment per card against it", "a typed line from the owner that becomes a
session". Found and reused: the lens switch (`frontend/src/board/dnd.ts`
`throughLens`, plan 01, a lens is never a write); typed independent readings
per card with a source fingerprint (`domain/verdict.py`, `domain/triage.py`,
`board/triage.py`, plan 59) and the reading loop that dispatches them one per
beat (`api/dial.py`); the Idea door, a typed line that opens a conversation
whose only way out is a document in the corpus (`api/doors.py::idea_brief`);
the WATCH grammar and its readers (`board/signals.py`); the warm call to a
colleague of either make (`needle call`, `needle wait`, plan 57 and card #73);
the DOUBTED word for a machine fact that outlived its evidence
(`domain/board.py`). Found and not reused: `Project.entrance` reads doctrine
delivery, not a project's focus; a plan's `intent` section is per document,
not per project; dennis-os's `loops.md` and `context/priorities.md` hold the
owner's ventures' constraints and envelope outside any project's corpus and
stay the source they are. Nothing on Needle carries a project-level focus,
a leverage class, or a diagnosis document; those three are new and named
below. Rejected in the discussion, with the reason in the record: sorting
against the intent document (every card ties); a `Constraint:` head line in
the constitution (the entrance links that file across makes and a monthly
sentence does not belong in it); a numeric impact score (the evidence
supports classes and a likelihood word, not precision); a session that
invents cards unasked (the shiny-object guard's worst enemy; proposals are
made in the conversation and written on his word).

## Items

### 1. A project's focus is one document the board reads, and choosing it is one ruling the board stores
The document is `docs/FOCUS.md` in the project's repository, read by the
corpus reader (`board/parse.py`, the head-field reader plans use) with a
head the board needs and nothing it does not: `**What matters now:**` the
outcome in his words with its measure in the WATCH grammar of
`board/signals.py`; `**What holds it back:**` the diagnosis in one sentence
with its own measure the same way; `**Evidence:**`, `**Rival:**` (the
explanation rejected and the observation that separates them),
`**Recheck:**` (a WATCH line, when the diagnosis is due to be read again);
`**Proposed:**` who and when. The M it lands on is prose in the body, never
a field, so a project that is not a business can carry a focus. The store
holds one ruling per project (`infrastructure/store.py`, beside the dial's
row): the document's fingerprint (`board/triage.py::fingerprint`) and when
he chose it, audited like a dial turn. A focus is *chosen* only while the
document on disk has the ruling's fingerprint; any other document is
*proposed*, and an edit after the click is a new proposal, never an
inherited ruling. The typed line he opened with is the door's audit row,
not a ruling. `needle focus <project>` prints the state in the strip's
words (item 5) and `--json` the typed shape, so a session and the page read
one function. Done means: on the fixture project, a `docs/FOCUS.md` with
every field reads into the typed shape and one with a missing measure or
an unreadable recheck reads as proposed-with-a-doubt naming the field; a
ruling bound to fingerprint A over a document now at B shows proposed; the
verb and the API return the same object; the ratchet under `tests/ratchets/`
refuses a chosen focus whose fingerprint differs from the ruling's.

### 2. He types what needs to change, and a conversation finds what holds it back and lands the document
A Focus door in the head of the project page, the Idea door's twin
(`api/doors.py::idea`, `runtime.discuss`, `WindowKind`): an input "What
needs to change?" and a button "Talk it through". It opens a conversation in
the project's checkout with a brief of its own purpose, beside `idea_brief`
in `api/doors.py`: his exact words; the project's intent and current focus
if any; the instruction to sharpen the outcome into a sentence with a
number first, then find what limits it — the six Ms where they fit, the
project's own evidence (its plans, its signals, its record on the board),
a rival explanation, and the cheapest observation that tells them apart;
missing evidence is a named unknown, never an invented bottleneck; the
backbrief is two or three plain sentences; on his yes the session writes
`docs/FOCUS.md`, commits and pushes, and writes nothing else. The same
conversation, when he asks or when the strip's coverage line says nothing
queued removes the limit, proposes moves the way Hormozi's walk does after
the M is found — what else could be done, at what cost, in what time, with
what likelihood — and writes each he names as a suggestion (`**Kind:**
idea`, `**Found by:** the owner, from the board's Focus door on <date>
(conversation <id>)`, its cost and likelihood in its head) so it is a card
by the next read and is judged under the lens like any other. A conversation
that ends without a document leaves the strip saying so. Done means: on the
fixture, the door opens a conversation whose brief is a fixture the tests
read; the record shows the discussion the way the Idea door's does; a
`docs/FOCUS.md` landing moves the strip to proposed; a suggestion written
from the conversation carries the Found-by line and cards on the next read;
the door refuses when a focus conversation is already alive for the project
and says which.

### 3. A reader of the other make checks the diagnosis before the ruling is offered
When a proposed focus lands, the reading loop (`api/dial.py`, the loop that
dispatches plan 59's readings) calls a colleague of the other make through
`needle call`, in a fresh thread of its own and never the slot's warm one
(the ruling of 2026-09-09 below), with the document, the sources it cites
and the project's intent, and waits on `needle wait`; the answer lands as one typed result on
the focus — stands, does not stand, cannot tell — with one line, bound to the
document's fingerprint, in `domain/triage.py`'s neighbourhood with its own
type and never a second reader of defects. The strip shows the reading beside
the proposal; "Use this focus" is offered with the reading, and without one
only when the call ended without an answer, saying so in the runtime's words
(a door either proves or says why not). Disagreement shows as disagreement
and never blocks his click. Done means: on the fixture with the fake Codex
worker, a proposed focus gets exactly one reading, its words show on the
strip, a re-edited document is read again, and a call that ends without an
answer leaves the strip offering the ruling with the reason shown; the
ratchet that holds one reader per kind still passes.

### 4. Every open card is read against the chosen focus, and the reading says how likely it is to work
The reading loop selects, besides a defect's mark, every open card on a
project with a chosen focus that has no reading since the focus was chosen
or the card's document changed, oldest first, one per beat, hands it to
the make that did not write the diagnosis through the call channel of
item 3 and never through the checkout seat (the ruling of 2026-09-09
below), and lands one typed result: the class — helps remove this limit, protects progress, does
not address this limit, needs evidence — one sentence of why that cites the
card's document and the diagnosis, and for the first class a likelihood in
one word (high, medium, low) with its reason, bound to both fingerprints.
The brief (`board/brief.py`) carries the focus document whole, the card's
document, and the rule that the reading judges what the plan would move and
never its aspiration; a plan whose intent does not say what it moves lands
"needs evidence", which is a finding on the plan. A reading goes stale when
either fingerprint changes and is redone; a card blocked by a Sequencing hold
keeps its class and shows the hold beside it, since impact and readiness are
two facts. Nothing under `api/dial.py` or `board/dial.py` reads the class
to choose work: a ratchet refuses the import. Done means: on the fixture with the fake Codex worker, a
chosen focus gets every open card read once, each in a thread of its own; an edited card is read again
and only it; a renamed focus stales all; the four classes and three words
parse and any other word is refused at the verb that lands them; a reading
session's actor cannot move a card or write a rank (the door refuses it);
the ratchet holds.

### 5. The Leverage lens shows the board as the focus would arrange it, one click makes it so, and one click puts it back
A fifth lens, `Leverage`, in `frontend/src/board/dnd.ts::throughLens` and
`Board.tsx`'s `LENSES`, that is a view like Age and Gate and stores
nothing: it shows the whole board as the focus would arrange it, across
every column and not only within one. The arrangement is one pure function
over the cards, their classes and the columns' grammar (`domain/column.py`),
so the page, the verb and the tests read one answer: a planned card that
helps remove the limit is shown in Up next, ordered by likelihood then by
effort gate ascending (the gate is the cost and time a plan already
declares); a card in Up next that does not address the limit is shown in
Not now with a wake trigger in the WATCH grammar written from the focus's
recheck; a Backlog defect that helps remove the limit is shown with the
plan door open, never in Up next, because the corpus is the status and a
suggestion cannot enter execution without a plan; protects-progress cards
keep their column and order after the helps-remove ones; needs-evidence,
unread and stale cards keep their place and are marked as such; a card
with a Sequencing hold shows the hold beside its class; a card that would
move is marked as moving, with where from. Every column is ordered under
the lens, and only Backlog, Planned, Up next and Not now have cards moved
between them: Executed, Done and Decision moment are never rearranged — the
first two are machine facts, the third is his by name — but Decision moment
is ordered by what each ruling unblocks, the one that frees the most
helps-remove work first, and Executed with the signals only he can read
first and the rest by their read date (his question of 2026-09-08: "each
column, not just up next, will be sorted in order of importance/execution?").
Flipping back to Rank shows his real board untouched; a drop under the lens
is not a rank (plan 01). Under the lens the head offers one
act, "Accept this order", with a count of the moves and each unticked at
will: the board applies every accepted move through the one move door
(`api/doors.py`, the same write a drag makes), with the owner as the mover
and the focus's fingerprint and the card's class as the reason on the
card's history, and writes the whole batch as one audit entry
(`domain/audit.py`) carrying every card's place before the move. Until he
ranks or moves a card by hand again, the head offers "Put it back", which
restores every card in that batch to its recorded place through the same
door, with his name and the batch as the reason; a hand move after the
acceptance retires the put-back, since there is no old state any more.
A move he unticked is not proposed again until the focus, the card's
document or its class changes. Accepting never starts a lane, never turns
the dial and never changes a gate: Up next remains his gate and Start his
click. The strip under the project head, above the columns, visible under
every lens, in these words and states: "No focus chosen" with the door;
"What matters now: … · What holds it back is not settled"; "Working out
what holds this back" with the open conversation; "A focus is ready for
your decision" with both sentences, the other make's reading, "Use this
focus" and "Keep discussing"; "Focus chosen · N of M cards assessed · K
moves proposed", with unread, needs-evidence and stale counts, and the
coverage line "K queued cards help remove this limit" or "Nothing queued is
evidenced to remove this limit" with "Propose moves" opening the
conversation of item 2; "Order accepted <when> · Put it back"; "Time to
check this focus again", "The evidence for this diagnosis expired on
<date>. Leverage order is paused while it is checked", and "The results
challenge this diagnosis". With no chosen and current focus the lens shows
"Leverage order unavailable: <why>" and the columns stay in his rank. The
card face under the lens shows the class in the four plain phrases and its
sentence, in the shape the plain-words plan settles or one sentence if it
has not. The strip expands in place to the document's evidence, measures
and history. The colours are the board's four meanings (`domain/board.py`);
a chosen focus is never painted proven.
Done means: a comp under `docs/design/` shows every state, the proposed
board with its marked moves, the accept count and the put-back, with
Harbourmaster data, and is signed before the build (`docs/design/README.md`);
the arrangement function has a test per rule above (a helps-remove plan
into Up next, a does-not-address card out of it with a readable wake
trigger, a Backlog defect never into Up next, Executed and Decision moment
ordered but never moved, ties keep his rank); `vitest` covers the view storing nothing,
the unavailable state and the drop-is-not-a-rank rule; on the door fixture,
an acceptance moves exactly the ticked cards through the move door with the
owner as mover and one batch entry, a put-back restores every one of them,
a hand move after the acceptance retires the put-back, an unticked move is
not re-proposed until its ground changes, and no acceptance starts a lane or
turns the dial; the Start click's audit row carries the lens in use and the
started card's class, so the loop below reads a trace and not his memory;
`tsc` passes with the mirrored types.

### 6. The two measures are watched, and the board says which link broke
At the ruling, the board writes two WATCH rows on the project's focus from
the document's own lines, the outcome's measure and the bottleneck's, read
by the signal loop of plan 16 on the recheck's cadence, with the baseline
each read first. A scheduled reading of the other make, on the recheck's
date, reads both against the diagnosis's prediction and lands one of three
words on the focus, in these sentences on the strip: "The bottleneck
measure improved, but <outcome> did not. We are checking the diagnosis";
"The work shipped, but <bottleneck measure> has not improved. We are
checking whether the work changed the limiting cause" (every card in the
first class that shipped since the ruling is re-read); "The evidence for
this diagnosis expired on <date>". Expiry, a changed outcome sentence and a
failed recheck pause the leverage order by themselves and doubt the focus
on the page; replacing the focus is his ruling through the door, and the
board never turns a missed target into "choose another priority".
Done means: on the fixture, a ruling writes two readable WATCH rows and
refuses a document whose measures it cannot read, naming the line; each of
the three outcomes shows its sentence and pauses the order; a paused order
never orders; the reading of this item is one call with a fixture answer;
the review record reads the first real focus's rows by hand.

Hands out: search — every open card on Needle's board with its document
path, gate and column, for the first run's count and the comp's data;
verifies three of them against the served board before the list is used.

Hands out: execution — the backend suite, `tsc`, `vitest` and the ratchets
after each item, every failure verbatim; verifies by re-running the one
failing test it reports before acting on it.

## Acceptance criteria

- Needle's own board carries a chosen focus by the close, reached through
  the door, the conversation, the other make's reading and his click, with
  the record of each on the strip's history.
- Under the Leverage lens that board is shown as the focus would arrange
  it across every column, the moves marked, with nothing stored; Rank shows
  his board untouched.
- One acceptance on Needle's board moved the ticked cards with his name and
  one batch on the history, and a put-back restored them, both read from
  the card histories.
- The strip says what the board is sorted on in the words of item 5, and
  says "unavailable" with a reason on every project without a chosen focus.
- No lane started, no gate changed and no card moved by anything this plan
  adds except through his acceptance; the two ratchets and the door
  refusals hold.
- The two WATCH rows exist on Needle's focus and the first recheck date is
  on the strip.

## Rulings

- **Within one project, never across.** The board is one project at a
  time; the envelope across ventures is his, held in dennis-os, and not a
  lens. Both makes, round one.
- **Two sentences, one document, one ruling.** The outcome and the diagnosis
  are one document a colleague writes and he chooses with a click bound to
  its version; the store holds the ruling and never the reasoning. "Use
  this diagnosis", never "this is proven". Codex, round three; Claude moved
  from a head line in the constitution to the document in round two.
- **Colleagues propose, he ratifies.** He is given no file to maintain; the
  conversation writes it and the strip asks for his ruling. Codex, round
  two, from dennis-os's "Dennis never maintains it".
- **The machine never turns a missed target into a change of priority.**
  It checks the causal link and says which link broke; replacing the focus
  is his. Codex, round three, correcting Claude's wording.
- **Gaps are proposals he sees, never a backlog he did not ask for.** The
  coverage line is a count; moves are proposed in the conversation with
  their cost, time and likelihood, and each becomes a suggestion on his
  word. His request of 2026-09-07 ("find I'm just not seeing the highest
  leverage thing") is served by the proposal, and the shiny-object guard by
  the word.
- **The lens proposes across every column; one click of his makes it the
  board; one click puts it back.** His ruling of 2026-09-07 after the
  simulation: the sort reorganises the board, not one column. It stays his
  move because the proposal is a view that stores nothing, the acceptance
  writes his name on every move, and the put-back is a second act rather
  than a toggle, since a board that flips between two orders is true in
  neither (INTENT: position is priority and both are true). Rejected: a
  standing ruling that lets the focus keep Up next in order unasked — the
  loop below decides whether to offer it, on evidence, later.
- **Leverage orders within the top class by likelihood then cost, never by
  a score.** The effort gate is the cost a plan already declares; likelihood
  is one word with a reason. Numeric impact scores were rejected in round
  one: the evidence supports classes, not precision.
- **Blocked is a fact beside the class, not a class.** A card can remove
  the limit and still wait on a Sequencing hold. Codex, round two.
- **The card reader is the make that did not write the diagnosis, and
  every reading starts a fresh thread.** The owner, 2026-09-09, from the
  Discuss door (conversation c9686e9c): "multiple views from different
  models should strengthen the outcome", and the wait and the cost of
  the other make reading every open card are his to spend. The makes
  meet in a relay, never in one room: the focus conversation of item 2 is
  one make with him, the check of item 3 is the other make reading cold,
  the per-card readings of item 4 are the make that did not write the
  diagnosis, through the call channel items 3 and 6 already use and never
  through the checkout seat (`runtime/launch.py::windowless`), which is
  the diagnosis author's. A call today resumes the slot's most recent
  thread (`runtime/launch.py::call_codex`, `runtime/codex.py::resume_argv`,
  read 2026-09-09), so a reading that is cold needs a fresh thread per
  call: one fix inside this lane, serving items 3, 4 and 6. Rejected: a
  joint conversation between the makes for the diagnosis — two models in
  one room converge on the first plausible story and the check becomes a
  formality; the second view's worth is its independence. Also rejected:
  naming Codex in the rule — the rule is the seat's independence from
  the author, and which make earns which seat is what #58 measures.
- **Needle is the proving ground.** Its board has evidence for "why can't
  Needle do more" today and it is not a business, which tests "any project"
  before Hello Revenue's focus is chosen.

## Loop

We think a chosen focus and a leverage order beside his rank will change
which cards he starts, because the focus is what his rank was approximating
from memory. If most starts fall outside the first two classes and the
focus was not renamed, the readings are wrong or the focus is, and five
evidence sentences read by hand say which. If he accepts nearly every proposed move and puts none back for two weeks, the board may offer a standing ruling to keep the order unasked — his to give, never a default. Adoption alone proves no impact; the second loop does.
Loop: the cards started on Needle in the fortnight after its first focus was chosen, by the lens in use and the class shown at each Start click, the share of proposed moves he accepted and put back, and whether the focus was renamed in that time — session read the Start audit rows, the acceptance batches and the focus history by 2026-10-05

We think the cards the lens put first will move the bottleneck's measure and
that moving it will move the outcome's, because the diagnosis predicts both.
If the bottleneck moved and the outcome did not, the diagnosis is re-read
and the owner is asked; if the cards shipped and the bottleneck did not
move, the card readings are re-read; either way the sentence is on the
strip before anyone sorts by it again.
Loop: Needle's first focus's two measures, read together against the diagnosis's prediction and the cards shipped in its first class — session codex by 2026-10-19

Loop: a focus shown as chosen with no ruling bound to its fingerprint — command uv --project /home/dennis/Work/needle run needle focus --unbound --count expect 0 by 2026-10-05 every 1d
