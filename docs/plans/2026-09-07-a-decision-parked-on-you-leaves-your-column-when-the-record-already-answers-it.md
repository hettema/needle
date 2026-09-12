# A decision parked on you leaves your column when the record already answers it

**Carries:** docs/slice-suggestions/done/2026-09-07-a-decision-parked-on-the-owner-is-read-twice-and-leaves-his-column-when-the-record-already-answers-it.md
**Status:** SHIPPED 2026-09-12 — every item stanced below; the review record is `docs/reviews/2026-09-12-a-decision-parked-on-you-leaves-your-column-when-the-record-already-answers-it.md`.
**Written:** 2026-09-07, from Dennis reading the boards for bottlenecks: "we need to close decisions that don't need me. If you can close the loop mechanically, let's close it." 34 cards sat in Hello Revenue's Decision moment and 12 in Needle's Executed waiting for him. A colleague of another make (Codex 0.153.4, read-only, 2026-09-07) read the proposal cold; its objection — the dangerous exit is a card closed as stale that carried a commitment — is ruling 1, and its loop is the Loop below.
**Effort gate:** high — the code widens one reading and adds one door (`api/dial.py`'s reading loop, `board/triage.py`'s results, `api/doors.py`'s act on a result); the judgment is the rule for what may leave the owner's attention, settled in the Rulings and held by a test, and a reading that gets it wrong takes a decision from him silently, which is the one failure this board exists to prevent.
**Sequencing:** after #75 (the result's words on the card face take #75's shape, and the reading's vocabulary is #74's file); #53 and #68 are not holds, but the owner placed this after them.
**Class:** a test refuses any result that lets a card leave the column while a commitment on it is unaccounted for, and the fourteen-day audit by a reader of another make is a WATCH row on this card; a wrong exit is loud within two weeks, never silent.
**Formerly:** A decision parked on the owner is read twice, and leaves his column when the record already answers it (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)
**Challenged:** 2026-09-12, by Claude Opus (the `hrclaude` slot, session 5a8331ec resumed from f53f2ba3, a reading session homed in the main checkout; call 110; the note `~/.cache/needle/notes/from-needle-82-challenge.md`, the answer beside it): ten material corrections before build, one deviation to record, one clarification, three holds. Each correction is a ruling below, marked *(challenge N)*; the two that would have taken a decision from the owner silently — a `his` line he could not answer, and a `waiting` that could defer a failed signal past his eyes for ever — are rulings 5 and 6.

## Intent

A card in the owner's column is there because the board could not tell
whether it needs him. HOW-WE-WORK §1 gives the test that tells, and says a
decision nobody has read twice belongs to nobody yet; §11 says one move is
his and the rest is the machine's, with its reason on the card. So every
card parked on him, on every board, is read a second time, cold, by a
session with none of the context that parked it, and the board acts on the
result: what the record already settles is planned as execution; what
waits for a signal gets the row that watches it and leaves his column;
what is his stays, as one line he can answer; what is over is closed. The
column becomes what its name says — his decisions, each readable in a
sentence — instead of a backlog wearing amber. Seven rules park a card
today and one unparks it; after this plan every park has a matching cold
read.

What does not change: who ranks. An `execution` result lands in Planned,
never Up next; the owner's ranking is his, and nothing here starts a lane.
The reading of plan 59 stays one reading; this plan widens its ground and
its results, never adds a second reader.

## Items

### 1. The reading's ground is every card parked on the owner, and its results say where the card goes
The reading of plan 59 (`api/dial.py`, the triage loop that picks who gets
a reading; `board/triage.py`, the typed results; the triage brief in
`board/brief.py`; `needle triage`) selects, besides a defect's mark, every
card in Decision moment on every registered board that has no reading
since it was parked, oldest first, one per beat. Its results gain two
words: `waiting <signal>` (in the WATCH grammar of `board/signals.py`) and
`stale <what ended it>`, beside `now` for execution and `his`. The brief
carries the §1 test in the owner's words, the card's whole record, the
document it cites, and the rule of item 3 as the thing the reading may not
do. The reading never moves a card; it lands a result, bound to the text
it read, and the board moves.
Done means: on the fixture, a parked card gets exactly one reading, its
result shows on the card face with its source in #75's shape, and a card
already read is not read again until it is parked again; the four results
parse and any other word is refused at `needle triage`; the reading's
brief is a fixture the tests read.
**Met:** the beat's queue (`api/dial.py::Dial._parked_unread`, appended in
`_take_next` behind the defects and the titles, `board/dial.py::Candidate`
ranking parked cards last and oldest park first) opens one reading per
card in Decision moment on every board — `board/parked.py::wants_parked_reading`
says which: read once per park, again only when the owner answers
(ruling 5), never with a live session on it, and the readings that died
are counted per park (`_readings_that_died(since=)`). The results are
`domain/triage.py::TriageResult.WAITING` and `STALE` beside `NOW` and
`HIS` (`PARKED_RESULTS`); a reading's row says what ground it read
(`Triage.ground`, migration 0024, `Store.latest_triages(ground=)` defaulting
to marks so no routing reader meets a parked reading). The brief is
`board/brief.py::decision_brief`: the §1 test verbatim (`THE_RULE`), the
whole record (every row and the card's history, oldest first), the cited
document or the fact that there is none, item 3's rule verbatim
(`COMMITMENT_RULE`) with what the board sees unaccounted for, and the four
commands; the fixture is `tests/api/briefs/a-card-parked-on-the-owner.txt`,
which `tests/api/test_parked_cards.py` compares to the brief the board
built for #139. `needle triage` on a parked card refuses `when`, `split`,
`cannot-tell`, a title verdict and a grade (`api/doors.py::Doors._decide`);
the face shows the result's words under "Your move" (`board/assemble.py::state_of`)
and the TRIAGED row carries the result, the source and the decision
identity in #75's shape (`triaged_row`). `tests/api/test_parked_cards.py`
walks the fixture's four parked cards through all of it;
`tests/board/test_parked.py` holds the rules; `tests/board/test_dial.py`
the queue's order. The reading session's name and record are a mark's
(`SessionWork.TRIAGE`), so the number, the cap and the head's count hold
for it unchanged.

### 2. The board acts on the result, once, with the reason on the card
`execution, selected by <source>` moves the card to Planned with the
source on its history; `waiting <signal>` writes the WATCH row and moves
the card to where a watched card sits (the column the close would have
put it in, `board/lane.py`), so the signal loop of plan 16 owns it from
there; `his: <one line>` leaves it and writes the line as the card's
question, which the face shows; `stale <why>` moves it to Done with the
reason. Each move is the machine's (`Actor.MACHINE`) with the reading as
its evidence, and a card the owner then moves is his: the machine never
moves it back (the rule `board/lane.py::unpark` already holds).
Done means: on the fixture, one card per result lands where this says with
the history line; an owner's move after a machine's is never undone by the
next beat; the reading session that lands a result cannot also move the
card (the door refuses a move from a reading session's actor).
**Met:** `api/doors.py::Doors._decide` acts once per result:
`board/parked.py::where_after_parked_reading` is the one map — `now` to
Planned for a live plan and to the suggestion's home column otherwise
(ruling 4: a `now` with nothing live to execute is refused), `waiting` to
Executed with the WATCH row written first and the WATCH it replaced named
on the history line, `stale` to Done, `his` nowhere with the line on the
face — every move `Actor.MACHINE` with `Evidence.RECORD_ANSWERED`, re-tested
per result on every read (`board/evidence.py` → `record_answered_missing`,
ruling 8). The owner's move after the machine's is never undone: the reading
of his re-park lands its result and the door writes the history line and
moves nothing (`owner_parked`, ruling 7), and no loop moves a card on a
reading. His `his` line is answerable: the Answer door opens on it
(`board/lane.py::doors_for`), his sentence lands as his ruling, and that
answer is what re-reads the card. `tests/api/test_parked_cards.py` shows
each landing with its history line, #139 moved by the reading, moved back
by the owner and left there by the next reading, and `needle decisions
--returned --count` counting it.
**Deviated:** "the door refuses a move from a reading session's actor" —
no door takes a move from a session as a card move: the page's move lands
the owner's actor and `needle move` moves a session. The one door a
session moves a card through is the close, and the close cannot tell a
reading session from a lane's, so `Doors.close` refuses every close while
a reading is open on the card (`_refuse_a_close_under_a_reading`), which
is the reachable form of the same rule; a lane the owner resumed on a
parked card waits the reading out, at most its ceiling. Held by
`test_a_reading_session_cannot_close_the_card_it_reads`.

### 3. A commitment never leaves the owner's attention unaccounted for
The rule from the other make's cold read, held in code and by a test: a
card may leave Decision moment only when every commitment on it is
accounted for — fulfilled with evidence on the card, withdrawn by a ruling
the owner made (an answer row of his), or transferred to a named WATCH row
that still watches it. Age, shipped code and an absent signal never
qualify, so a `stale` result on a card carrying an open commitment is
refused by the door and the card stays with a doubt on its face saying
which commitment the reading did not account for. A commitment is what the
card's document and rows promise: a DELIVERED with no signal, a WATCH not
yet read, a question in the owner's words with no answer row.
Done means: a test plants a card with a DELIVERED and no signal, lands
`stale`, and the door refuses naming the DELIVERED; the same card with a
WATCH row lands `waiting` and moves; the review record reads the first
real run's refusals by hand.
**Met:** `board/parked.py::commitments_of` is the rule, pure over the
card's rows and history and blind to age, shipped code and absent signals
by construction: a DELIVERED with no readable signal, a WATCH nobody has
read or whose last reading did not say delivered, an ASK or a Q with no
answer of his after it, a RULING with no RULED. `Doors._decide` writes the
`stale` row first and then refuses naming every commitment, the reading's
record stays open so the same reader can land `his` (ruling 10), and the
face carries the doubt from the row and the rows as they stand
(`parked_doubt`). `waiting` accounts by transfer to the WATCH row it
writes, and is itself refused when it would defer a signal already read
as not delivered or past due, or a third time on one card (ruling 6,
`waiting_refused`). The fixture's #219 (a DELIVERED and a WATCH the board
cannot read) is the planted card: `stale` refused naming "The read-out,
with the two seasons side by side.", then `waiting` moves it to Executed
(`tests/api/test_parked_cards.py`); #147's unanswered ASK refuses `stale`
until the owner's answer accounts for it, after which `stale` closes it.
`tests/board/test_parked.py` holds each clause. The first real run's
refusals are read by hand in the review record's verification section, as
far as the run has gone by the close; the rest is the WATCH row below.

### 4. The first run reads the backlog, and a reader of another make audits it
The reading runs over Hello Revenue's 34 and Needle's parked cards on the
first beat after the fold, at the dial's usual pace, one per beat; the
card carries the count of cards read, moved, kept and refused. On the
fourteenth day a reader of another make (`needle call codex`, plan 57's
channel, read-only) checks every card that left the column against the
promises on it and every `execution` result against the alternatives its
source settles, and writes its findings as a reading on this card.
Done means: after the first run every card that was in Decision moment on
2026-09-07 has a reading; the counts are on this card; the audit call is
the Loop's signal, not a session's memory.
Hands out: search — every card in Decision moment per board with its rows,
document path and the date it was parked; verifies the parked date against
the card history for three of them before the list is used.
**Met:** the list was read on 2026-09-12 from a copy of the served
board's memory, upgraded to 0024 in rehearsal (the script in the lane's
job folder; its output is in the review record): Hello Revenue 38 cards
parked (11 parked by the owner himself, 12 by the machine with the
evidence named — signal-failed, document-archived, lane-ended — 10 by the
0.1 import, the rest by a session or the machine with no evidence named),
hr3 1, Needle 0, the machine's board 0, dennishettema 0 — 39 in all, not
the 34 of 2026-09-07. Three parked dates (#147, #180, #410) were verified
against each card's history: the placement row and the history's newest
move into Decision moment agree to the second. The run itself starts on
the first beat after the fold, behind every unread defect and title on
every board at one reading a beat (ruling 12); the counts of cards read,
moved, kept and refused are what `needle decisions all` prints per parked
reading (its ground, its result and where the card went or that it
stayed), and the card carries them as a WATCH row rather than a session's
memory. The fourteen-day audit is the Loop's first line, a `session`
signal the board starts for a reader of another make.

## Acceptance criteria

- No card sits in Decision moment on any board without a reading, and
  every card there has one line that is the decision.
- A card that left the column can be traced to its result and its source
  on its history, and none carried an unaccounted commitment.
- The owner ranks what the reading planned; nothing here started a lane.
- The fourteen-day audit landed as a reading on this card, by a reader of
  another make.

## Rulings

- **The dangerous exit is `stale`, so it is the one the door refuses.**
  From the other make's read: a reader can take inactivity or shipped code
  as permission to abandon a commitment (a card asking whether to close a running
  programme), which takes the owner's decision without any external
  exposure, so the exposure test alone would miss it. Rejected: `stale` on
  the reading's word alone. Item 3 is the rule.
- **`execution` means Planned, not started.** §1 says who owns a decision;
  §11 says who ranks. Rejected: an `execution` result that lands in Up
  next, which would let a reading set his priorities.
- **One reading, wider ground.** Rejected: a second reader for the column
  beside plan 59's for the rail. Two readers of one test is two ways to do
  one thing.
- **Recovery before this, comprehension before recovery.** The owner
  placed this after #53, #74, #75 and #68. The other make argued for
  comprehension before recovery on the ground that recovering lanes before
  the owner can tell what deserves work keeps the laptop busy without
  valuable completions; the order in Up next follows that.
- **A `his` line is a line he can answer, and his answer is what re-reads
  the card** *(challenge 1)*. The Answer door on a parked card with no
  session opens on a parked reading's `his` exactly as it opens on a
  defect's, and his sentence lands as his ruling on the card's history;
  the reading opens again when a park is newer than the last reading, or
  when an answer of his is newer than it — his answer changes the record,
  and the next reading reads the record with his answer in it. Rejected:
  re-reading on any changed row (a session's WATCH would re-open a
  question he had settled) and never re-reading (his answer would sit
  unread, which is the failure the card exists to end).
- **`waiting` cannot defer a failed signal past his eyes** *(challenge 2)*.
  A WATCH is one per card and a second write replaces the first, so a
  reading could send a card whose signal failed back to Executed with a
  fresh date, and again on the next park, and he would never see it. The
  door refuses `waiting` on a card whose WATCH was already read as not
  delivered, or is past due, unless the new signal watches something
  else (its *what* differs); and refuses a third `waiting` on one card —
  two readings have sent it to wait, and the third answer is `his`. The
  WATCH a `waiting` replaces is on the card's history, and the TRIAGED
  row names what it replaced, so the transfer is traceable.
- **`now` needs something to execute** *(challenge 6)*. Ruling 2 fixes the
  column and not the precondition: a `now` on a card whose document is
  archived or absent would land in Planned wearing the wrong-column
  doubt — a card the reading moved *onto* his attention while claiming to
  take it off. So `now` needs a live document: a live plan goes to
  Planned; a live suggestion goes to its home column (Defects or Backlog
  by `board/reconcile.py::home_of`), never to a rank; with neither the
  door refuses `now` and says the result is `waiting`, `his` or `stale`.
  This applies ruling 2's reason (nothing here sets his priorities) and is
  execution, decided in the lane.
- **A card he parked himself is read, never moved** *(challenge 7)*. The
  column's promise is that each card there is readable in a sentence, so
  every park is read, his own included; but when the placement into the
  column is his own move, the door writes the result and its history line
  and moves nothing — his park is final. Rejected: skipping his parks
  (a card he parked fresh, months after an old reading, would sit
  unread for ever).
- **The evidence a reading's move rests on is re-tested per result**
  *(challenge 5)*. "A reading exists" is true the moment the row is
  written and never stops being true, so a move on it would never doubt
  itself (§11). The predicate `RECORD_ANSWERED` re-reads, per result: on
  `now`, that the source the reading named still reads as it did (the
  same fingerprint test routing makes); on `waiting`, that the WATCH row
  still names a signal and it is the reading's; on `stale`, that no
  commitment on the card is unaccounted for. A failed re-test is a doubt
  on the face, never a move.
- **Done's and Executed's definitions say what a reading may put there**
  *(challenge 4)*. Done said "the signal named on the card arrived and
  somebody read it"; Executed said "built and archived". A `stale` card
  carries no arrived signal and a `waiting` card may have no archived
  plan, so each definition gains the sentence, in the same commit as the
  move — a definition the move makes false one hover away is a lie.
- **Parked cards queue behind the defects and the titles** *(challenge 8)*,
  by a leading rank on the reading queue's key, not by their date: a park
  older than a defect's birth would otherwise jump it. And the readings
  that died are counted per park *(challenge 10)*: a card parked twice
  whose first park burned the three attempts is read on its second.
- **A refused `stale` leaves the reading open** *(challenge 12)*. The row
  is written first, so the face carries the doubt and the card is not
  re-read until parked again or answered; the reading's own record stays
  open, so the same reader can land `his` with the commitment as the
  line, and the beat ends the record when the turn is over.
- **Pacing** *(challenge 9)*. Every unread defect and title on every board
  is read before the first parked card (the served board held 120 unread
  defects and every switch off on 2026-09-12), at one reading a beat; the
  first run over Hello Revenue's parked cards lands days after the fold,
  and the card says when it can be expected to finish rather than the
  Loop's date pretending it is done.

## Deliberately not

- The seven parking rules themselves: each is right on its own and stays.
- Needle's Executed cards waiting on the owner to read a signal: the signal
  loop of plan 16 owns those, and a signal the board can read itself is
  that plan's item, not this one's.
- Anything that starts a lane.

## Loop

We think a cold reading of every parked card, with the commitment rule
held by the door, will empty the owner's column of what does not need him
without losing a commitment, because the record already settles those
questions. If the audit on day fourteen finds one commitment abandoned,
one outcome the cited source did not select, or one card closed without
its signal, the safety claim is false: the affected cards are restored and
that exit is suspended until the rule is fixed. If the column shrinks but
questions come back to the owner because results were wrong, that is
displaced work, not relief, and the reading's brief is what changes.

Loop: a reader of another make audited every card that left the owner's column against its promises — session codex by 2026-09-21
Loop: questions returned to the owner because a reading was wrong — command uv --project /home/dennis/Work/needle run needle decisions --returned --count expect 0 by 2026-09-21 every 1d
