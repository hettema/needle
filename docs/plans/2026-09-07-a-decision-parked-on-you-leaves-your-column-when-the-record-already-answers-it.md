# A decision parked on you leaves your column when the record already answers it

**Carries:** docs/slice-suggestions/done/2026-09-07-a-decision-parked-on-the-owner-is-read-twice-and-leaves-his-column-when-the-record-already-answers-it.md
**Status:** NEW — planned, not started; placed in Up next by the owner on 2026-09-07, after admission, comprehension and recovery.
**Written:** 2026-09-07, from Dennis reading the boards for bottlenecks: "we need to close decisions that don't need me. If you can close the loop mechanically, let's close it." 34 cards sat in Hello Revenue's Decision moment and 12 in Needle's Executed waiting for him. A colleague of another make (Codex 0.153.4, read-only, 2026-09-07) read the proposal cold; its objection — the dangerous exit is a card closed as stale that carried a commitment — is ruling 1, and its loop is the Loop below.
**Effort gate:** high — the code widens one reading and adds one door (`api/dial.py`'s reading loop, `board/triage.py`'s results, `api/doors.py`'s act on a result); the judgment is the rule for what may leave the owner's attention, settled in the Rulings and held by a test, and a reading that gets it wrong takes a decision from him silently, which is the one failure this board exists to prevent.
**Sequencing:** after #75 (the result's words on the card face take #75's shape, and the reading's vocabulary is #74's file); #53 and #68 are not holds, but the owner placed this after them.
**Class:** a test refuses any result that lets a card leave the column while a commitment on it is unaccounted for, and the fourteen-day audit by a reader of another make is a WATCH row on this card; a wrong exit is loud within two weeks, never silent.
**Formerly:** A decision parked on the owner is read twice, and leaves his column when the record already answers it (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)

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
