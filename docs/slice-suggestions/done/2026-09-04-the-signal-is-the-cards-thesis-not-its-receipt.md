# The signal is the card's thesis, not its receipt

**Carried by:** docs/plans/2026-09-05-14-the-board-never-asks-about-what-does-not-matter.md

**Kind:** idea
**Fix:** his
**Found by:** the owner, in conversation with the coordinating session on
2026-09-04, watching the first reading round land: *"in my mind, the needle
board would be my watchdog for the intent. So if we push a feature that is
going to change some user behavior or decrease error rates or decrease costs
for production, then the card checks Hello Revenue every once in a while based
on the cadence and then is able to either falsify the result — it didn't
happen — and send it back to a decision moment, or if it did happen, it sends
it to done. I guess that's not happening right now?"*

## Observation

Slice 09 built the reader and it works: a session reads the signal on the
cadence with the project's read-only tools, and the board moves the card —
delivered to Done, not delivered to Decision moment, cannot tell into the
owner's batch with the evidence. The machinery is indifferent to what the row
asks it to read, and that is where the intent leaks out.

Most rows ask for the mechanism, not the outcome. Hello Revenue's #124 reads
*the two total-summary labels are in the page's own language*; #119 reads *a
rejection lands in the ledger with its stage named*; #103 reads *the rehearsal
verdict sits beside Deploy*. Each is a receipt: **did the code do what the code
says it does.** A handful already name the outcome — #238 reads retry share
under ten percent of build spend, #246 reads under two dollars a page against
the plan's own query, #117 reads cost per message and latency against the week
before the ship — and those cards are watched the way the owner means.

The split is not the reader's doing. It is what the closing sessions wrote, and
slice 09 translated them faithfully rather than inventing measures nobody had
agreed. The grammar takes any `what`, and `Doors.close` accepts any row that
parses. Nothing ties the WATCH row at the foot of the card to the SERVES row at
its head: a card may serve *builds cost less* and ship a signal reading *the
three closing stages started within twelve seconds of each other*.

`docs/HOW-WE-WORK.md` §7 already states the rule the row should carry — *we
think X will change Y, because Z; if we see A, then B*, with Y laddering to an
intent and A designed to discriminate rather than confirm. The board holds
nobody to it.

**Why it costs something.** A receipt goes green when the code works and the
intent fails. That is precisely the silent failure §7 says always earns a
loop: the card reaches Done, the belief becomes an assumed fact, and the next
plan is built on top of it. Worse, it is the *confirming* observation §7 warns
against — the mechanism moving is exactly what every rival explanation also
predicts, so a green receipt teaches nothing that could be carried anywhere
else. #102 is the shape done right, and it took the reading session to get
there: the row it inherited measured wall-clock per asset, the session found
that measure blind to fan-out size, replaced it with the whole-build floor and
per-stage parallelism, and only then said delivered. The board should not need
a session to notice that at reading time.

## What would change it

Four parts, each defending the one after it.

**1. The row carries the thesis.** The grammar keeps its shape and its `what`
becomes the outcome, with the baseline it is read against and the threshold as
`expect`. Two gaps show up at once. A signal's clock is often a count of
events, not a date — *the next twenty builds*, not *next Tuesday* — and `by
<YYYY-MM-DD>` cannot say that; today a session that finds the evidence cannot
exist yet says cannot-tell and lengthens its own cadence, which works but
spends a session to learn what the row could have stated. And the baseline has
no home: #238 and #246 smuggled theirs into prose pointing at a query in the
plan.

**2. The close refuses a receipt where the card serves an outcome.** The
closing session is the one that knows what it built and what it should move,
and it is also the one under the most pressure to write something that will go
green. The refusal belongs there, in `Doors.close`, beside the two it already
makes: a card whose SERVES row names something measurable cannot close on a
WATCH row that only restates the implementation. What exactly a machine can
judge here is the open question — the honest floor may be that the close asks
for the baseline and the outcome as separate fields and refuses when they are
missing, rather than judging the sentence.

**3. The reading session judges the outcome against the intent.** Its brief
carries the card's SERVES row today only as part of the rendered card; it
should carry it as the thing being judged, with the instruction §7 gives:
prefer the observation the rival explanations do not predict, and when the row
measures the mechanism where the card serves an outcome, replace it and say so.
The replacement row from slice 09, item 2 is already the mechanism for this.

**4. The 51 are re-read once more.** The same lane that translated them from
`owner` to `session` should re-read them from receipt to thesis, with the
reasoning per card, and the owner overturns after the fact. Some will not have
an outcome worth measuring — a defect fix whose whole intent is that the code
stops being wrong is honestly a receipt, and saying so per card is part of the
work.

## What to be careful of

- **Not every card carries a bet.** §7's own test: a verified mechanism is
  already closed, and a fix whose failure would be loud needs no loop. Forcing
  an outcome onto those manufactures metrics nobody will read, which is how
  measurement stops being believed.
- **The threshold has to come from data, not from a session's taste.** "Under
  an hour" was the owner's own example of a number nobody set from evidence.
  A row that invents a bar is worse than a receipt, because it looks rigorous.
- **The board must not become the place where a session argues with the
  intent.** The reading says what the evidence shows; whether the intent was
  worth holding stays the owner's.
