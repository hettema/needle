# 09 — A session reads the signal

**Status:** PENDING
**Written:** 2026-09-04, from the owner's reading of the first triage sitting: 47 shipped Hello Revenue cards carried a signal only he could read, and "many of these plans use me as the gateway whilst you are a better gateway. I believe in giving you the autonomy you need to execute whenever we're aligned on intent. That goes for this as well." — said to the coordinating session; in this plan "you" means any Claude session with the project's tools, and "me" means the owner. Nowhere below does "you" address the executing session. And on one of them: "'builds stay under an hour' is just checking logs for wall-clock time? I don't think under an hour is true, nor am I sure whether it's the right measure because built campaigns have different amounts of assets."
**Effort gate:** high — the mechanics are a fourth reader in the signal grammar and a short reading session launched by the runtime; the judgment is in how each of the 47 signals is re-translated, which the lane writes with its reasoning per card and the owner can overturn.
**Sequencing:** after 06 (it shares the loop and the signal files with 06's live-write item). Before 08.

## Intent

The measure step of every loop is read by the machine or by a session, never by the owner's memory. A signal a session can investigate with the tools it has — the read-only production database, the ledger, deploy logs, the probes, git, the project's own commands — is read by a session at its due time, on its cadence, and the session's finding moves the card. The owner is asked only when the question is one of his own taste or experience, or when a session read the evidence and could not decide, in which case he gets the evidence with the question. A signal that turns out to be the wrong measure is replaced, not pretended.

### 1. A fourth reader: `session`

Done means: the WATCH grammar gains `session <what to check, where> [expect …]` beside url, file, command and owner; at the due time, on the cadence, the loop starts a reading session through the runtime in the project's main checkout — read-only for the repository, with the project's read-only data access as its own rules provide it (Hello Revenue: the read-only database role, the probes, the Railway log rules in its CLAUDE.md), never a lane — with the card, the DELIVERED row and the signal as its brief; the session ends its turn with one of three findings on the card, through `needle reading`: **delivered** with the evidence, **not delivered** with the evidence, or **cannot tell** with what it read and what would decide it; the board moves the card to Done, to Decision moment with the finding, or asks the owner with the session's evidence in the question. The reading session is listed on the card while it runs and never counts as hands on the tree.

### 2. A wrong measure is replaced, not pretended

Done means: a reading session that finds the signal unmeasurable or the wrong measure (a threshold nobody set from data, a measure that ignores size — "under an hour" for builds of different asset counts) does not guess; it writes a **replacement WATCH row** with the measure it can read (for #102: build wall-clock per asset from the ledger, against the 16 Aug baseline, per build), says so in its reading, and the loop reads the new signal from its next cadence; the owner sees the replacement on the card's history and can overturn it. The rings rule applies: a finding about the signal itself is inside the card; a finding about the product is filed as a suggestion with its kind.

### 3. The 47 are re-translated

Done means: every `owner` signal on Hello Revenue's Executed cards is re-read by the lane against one rule — could a session with the project's read-only tools read this? — and rewritten as `session` where yes, kept as `owner` only where the question is the owner's taste or his own experience (a reply "noticeably sooner" to him; a page "judged by eye" is a session's with a screenshot), with the reasoning per card in the close-out's table; the originals stay in each card's history; the first reading round runs on the lane's own cadence so the close-out reports how many of the 47 a session could settle on day one.

### 4. The owner's batch shrinks to what is his

Done means: the attention rail's batched owner list holds only `owner` signals and `cannot tell` findings, each carrying the session's evidence when there is any; the count on the rail is the count of decisions that are actually his.

## Terrain
- `board/signals.py` (grammar, readers), `api/loops.py` (the signal cadence and the moves it makes), `api/doors.py` and `runtime/` (starting a session that is not a lane: the Discuss door is the nearest shape — a conversation that never has hands; this one is windowless and writes back through a verb), `api/cli.py` (a `reading` verb), `board/assemble.py` (the rail's batch).
- Hello Revenue's data access rules: its `CLAUDE.md` § "Reading production data" (the read-only role, never the admin string; the Railway CLI's `head` trap), the probe workflow, the ledger tables named in `docs/wiki/` — the reading session's brief points at these, never restates them.
- The 47 signals as they are: `needle rows hellorevenue` once 08 lands, or the card detail API today.

## Acceptance criteria
1. A card with a `session` signal due now gets a reading session started by the loop, and the card shows it; the session's `delivered` finding moves the card to Done with the evidence on the history row; `not delivered` lands in Decision moment with the finding; `cannot tell` puts the question to the owner with the evidence.
2. A reading session that replaces a measure writes the new WATCH row, and the loop reads it on the next cadence; the owner sees both on the history.
3. Of the 47, the close-out says how many became `session`, how many stayed `owner` and why, and how many the first reading round settled.
4. The owner's batch on the rail counts only what is his.

## Rulings
Recorded as the build makes them, each with the alternative rejected.

## Estimate
Execution clock: one lane-day, half of it the 47 translations and the first reading round. Gate clock: none; the owner overturns after the fact.
