# 14 — The board never asks about things that don't matter

**Status:** PENDING
**Written:** 2026-09-05, from the owner at the machine repo's Idea door (conversation 81c7301c), asked whether a Spotify card should carry an owner question: "the board should never ask me about things that don't matter. I guess nailing what doesn't matter is the hard bit but e.g. spotify is something I use. If I'm happy I continue using it. If I'm not I complain in some way and that's the signal … the risk is that I'm starting to treat executed as done which means the times I'm really needed I'll probably be ignoring executed?" And, on being told the rule would reach Needle as a suggestion: "It feels like Needle and HR both need this. Why unplanned backlog items?" The machine's own card for its five finished plans and three unreadable signals is `omarchy-machine` plan 13 (card 16 there); this plan is the board's half.
**Carries:** `docs/slice-suggestions/2026-09-04-the-signal-is-the-cards-thesis-not-its-receipt.md` (the owner's watchdog intent, and the receipt-versus-thesis finding, with its own caution that not every card carries a bet).
**Effort gate:** high — the mechanics are two refusals and a landing place, each with a clear test. The judgment is per card in item 4: which of thirty-odd shipped cards would fail loudly, which are verified, which are receipts, and which are the few silent bets only he can see. That is deciding what matters to him, card by card, and the strongest model does it inside the rulings below.
**Sequencing:** after #42 (plan 16: the grammar this plan layers its rules on — `Loop:` lines, many WATCH rows per card, the close writing them from the plan; both edit `needle close`, `board/signals.py` and the brief, and 16 goes first because its refusals are the door's mechanics and this plan's are the judgment on top; the hold was written as "after 11 and 08" without card numbers until the Idea door of 2026-09-05, conversation 6b683c8b, which the board read as prose). Plan 11 (#34, shipped) changed the same door; plan 08 (#20) shares the parsers as files, not as a hold; plan 15 (#41) adds a call beside this one in `api/loops.py`. Reuses plan 09's reading session and its replacement-row door for item 4; nothing is invented where those exist.

## Intent

INTENT says the board is his watchdog for the intent and that one move is his. `HOW-WE-WORK.md` §7 says which loops earn closing: a bet, not a fact, and a failure that would be silent; the person is asked only for judgments of taste or of their own experience. The board holds nobody to that. Its grammar takes any `owner` row, its close accepts one, and plan 04's translation made `owner` the fallback for every signal no machine could read: 52 of 54. Today Hello Revenue's Executed column holds 34 cards and 27 of them are waiting on him; Needle's holds 11 and 2 are. The column he was meant to watch is the one he has learned to skip, and the day a card there needs him, he will skip that too. He said so himself.

What will be true when this is done: **an owner question on a card exists only for a bet whose failure would be silent and that only he can see.** Everything else the board reads itself, or closes as done because reality is the loop.

## The rule, in four lines

- **Loud failure: Done at once.** He uses the thing, or a session trips on it, or `machine check` says so at the next start. The card's row says what the complaint would look like, so the record shows the loop was judged, not skipped.
- **Verified mechanism: Done as a fact.** A rehearsal on a fixture, a permission the system itself now refuses, a cause read from the evidence. §7 already says a fact is closed.
- **Silent bet a machine or a session can read: a reader, never him.** `url`, `file`, `command`, `session`, run once by hand before the row is written.
- **Silent bet only he can see: the one owner question**, and the row says why the failure would be silent and why nobody but him can see it. Without both, the close refuses.

The test at close time, in his words: would he notice by himself? If yes, the board stays quiet.

### 1. A close can say the loop is reality, and land in Done

Done means: the WATCH grammar gains two forms beside the readers — `loud — <what the complaint looks like>` and `verified — <what verified it>`; `needle close` with either lands the card in Done directly, with the row, the DELIVERED and the REVIEW as any close; the loop never reads a Done card (it does not today; a test says so); the card's face in Done says *reality is the loop* or *verified* where a read card says *loop closed*, so the two are never confused; the attention line counts neither as a signal for him. A `loud` row on a card whose plan's own loop names a silent failure is a lie the machine cannot catch; the brief says so and item 4's re-read is where the human eye goes over it once.

### 2. An owner reader is refused unless the row says why

Done means: an `owner` row carries, after the question, `silent: <why nobody else would notice>` and `only-you: <why no reader on this machine can see it>`; `needle close` and the reading door's replacement row refuse an `owner` row missing either, naming the missing half and asking the close-time question; the brief every closing and reading session receives (`board/brief.py`) teaches the four-line rule and the question, beside the WATCH grammar it already carries; a ratchet holds the grammar's docstring and the brief to the same four lines so they cannot drift apart. The refusal is the whole mechanism: a rule a session is asked to remember is a wish (§5).

### 3. Where the card serves an outcome, the row carries the thesis

From the carried suggestion, parts 1 to 3, unchanged in substance: the `what` is the outcome with its baseline and threshold; a signal's clock may be a count of events (`after <N> <what>`) and not only a date; the close refuses a receipt on a card whose SERVES row names something measurable, at the honest floor the suggestion states — the baseline and the outcome as separate fields, refused when missing, never a judgment of the sentence; the reading session's brief carries the SERVES row as the thing being judged. Done means: a test closes a card serving *builds cost less* on a row reading *the stages start within twelve seconds* and is refused with the SERVES row quoted; a test closes the same card on a row with a baseline and a threshold and passes; a row with `after 20 builds` parses and the reader waits for the count. The suggestion's own caution holds: a card that carries no bet is not forced to invent one, and item 1 is where it goes instead.

### 4. Every shipped card on every board is re-read under the rule

Done means: a session (plan 09's reading session, one per project) reads each card in Executed on Hello Revenue's and Needle's boards — the machine's three are card 16's own work there and are skipped — and for each writes one of: `loud` into Done, `verified` into Done, a machine or session reader where one can read the bet now, or an `owner` row with both halves; the reasoning per card lands in this plan's close-out as one table (card, old row, new row, why), in the shape plan 04's table set; the owner overturns after the fact through the door that exists (`overturn`), never before; a card the session cannot place is left as it was and named in the table, so the count of those is visible. Done means, in numbers: Hello Revenue's Executed column holds owner questions in single digits, each saying why, and none of the 27 is left unjudged.

### 5. The count is the loop

Done means: `needle signals <project|all>` (and the API behind the head) returns, per project, the owner questions open in Executed, the days each has waited, and how many past due have no answer; the head shows the open count where the attention line already counts signals for him. This plan's WATCH row is `session` — *thirty days after the fold, read `needle signals all`: at most three owner questions open on any board at once, none past due unanswered, and at least ten cards closed in the period so a quiet column is not an idle one* — with the two readings named now: a question that sat past due is either a loud one the refusal let through (tighten item 2, with the row as the case) or a real one he did not see (then the question goes where he already looks, and that is the next plan, not this one).

## Terrain
- `board/signals.py` (the grammar: `loud`, `verified`, the two owner halves, `after <N>`), `api/doors.py` (close and the reading door's replacement row), `board/brief.py` (the rule in every closing and reading session's brief), `board/assemble.py` and `frontend/src/board/` (the Done face; the head's count), `api/loops.py` (the count; nothing reads Done, asserted), `api/cli.py` or `api/board_cli.py` (`signals`), `tests/ratchets/` (grammar and brief held to one text).
- Hello Revenue's corpus is read, never written; item 4 writes rows through the board, and the plan's close-out table lives here.
- `docs/HOW-WE-WORK.md` §7 gains the four lines and the close-time question, in the same fold, so the rule has one home and the code cites it.

## Acceptance criteria
1. On a fixture, a close with `loud — …` lands in Done with its rows, the face says *reality is the loop*, and the loop never reads it.
2. A close with an `owner` row missing `silent:` or `only-you:` is refused naming the half; with both it passes.
3. A receipt on a card that serves a measurable outcome is refused with the SERVES row quoted; a row with baseline and threshold passes; `after 20 builds` parses.
4. Hello Revenue's Executed column, read live after item 4: owner questions in single digits, each with both halves, the table in this plan's close-out with every one of the 27 placed or named as unplaced.
5. `needle signals all` returns the counts; the head shows them; the suite and the ratchets are green.

## Rulings
Recorded before the build, from the conversation; each overturnable by the owner on the card.
- **`owner` is not the fallback reader.** Plan 04's R2 made it one; that is where the 27 came from. A signal no reader can read and only he cannot see either is not a loop; it closes as `verified` or `loud`, or the plan lacked a thesis and says so.
- **Loud goes to Done at once, with the row.** Rejected: an Executed card with no reader, waiting a week "in case". A card waiting on nothing is the wallpaper he described.
- **The re-read is a session's, and he overturns after.** Rejected: asking him to judge the 27 himself. That is the very question load this plan removes.
- **What doesn't matter is decided at the close, by one question.** "Would he notice by himself?" Rejected: a list of things that matter, which would be stale by the next card.
- **The rule has one home.** §7 carries it; the grammar, the brief and the ratchet cite it. Rejected: the rule in the brief alone, where the last rule drifted.
