# 05 — The board is cleaned by evidence

**Status:** PENDING
**Written:** 2026-09-04, from the owner's intent stated the same afternoon on seeing Hello Revenue's whole board for the first time: "get the board squeaky clean, not by just discarding stuff but by being smart about it. Find things we can guarantee are done or no longer relevant first, then iterate smartly so we can make informed decisions as quickly and efficiently as possible." Prioritising what remains is the round after, and not this slice.
**Effort gate:** high — the mechanics (evidence classes, a triage view, batched acceptance) are specified below; the judgment is in the verdict each open card gets, which the lane writes with its evidence and the owner accepts or overturns. Nothing is discarded by the machine.
**Sequencing:** after 04. Uses the doubt marks, the signal grammar and the batched owner questions.

## Intent

Every open card on the board carries a verdict with its evidence, and the owner clears the board in a few sittings by accepting verdicts in batches, overturning the few he disagrees with, and reading only the evidence, never the whole card. What is provably done or no longer relevant leaves first; what remains open is open on purpose, with a written reason, and ready for the prioritisation round.

### 1. Evidence classes, one per open card

Every card outside Done and Not now gets exactly one evidence class, computed where the corpus and the machine can say and judged by the lane where they cannot, with the evidence beside it:

| Class | Evidence | Recommended verdict |
|---|---|---|
| **shipped, signal read** | plan archived, DELIVERED written, signal read delivered | Done |
| **shipped, signal owner-only** | plan archived, DELIVERED written, signal is an owner question | stays Executed; the question joins the batch |
| **built under another name** | a suggestion whose subject an archived plan delivered (cited, or the lane finds the delivery in the plan's close-out) | Done, citing the plan |
| **superseded** | the intent was overtaken by a later ruling or plan (cited) | Not now, citing what overtook it |
| **doubted** | a machine placement whose evidence is gone (from slice 04) | the doubt's own fact decides: Decision moment or back where it came from |
| **stale plan** | a plan in Planned or Up next older than a stated age with no lane ever | Decision moment with "still true?" |
| **live and open** | none of the above | stays, with a one-line reason |

Done means: every open card carries a class, an evidence sentence and a recommended verdict, written through `needle row` as a RULING-kind row the owner has not yet accepted (the row names the class); the lane's table of every verdict with its evidence is in the close-out; no card is moved by this slice until the owner accepts.

### 2. A triage view

Done means: the page has a triage lens over one project: every open card as one line — number, title, class, evidence, recommended verdict — grouped by class, with **Accept all in this class**, **Accept** and **Overturn** per line; accepting moves the card by the machine with the verdict's reason on its history row and the owner named as the acceptor; overturning keeps the card and records his word; the lens is reachable from the attention rail ("N cards carry a verdict you have not read").

### 3. Hello Revenue's board is triaged

Done means: the lane runs the classification over every open card on Hello Revenue's board (roughly 250 today: 152 Backlog suggestions, 9 Planned, 1 Up next, 13 Decision moment, 66 Executed), reads the corpus for the "built under another name" and "superseded" classes rather than guessing, writes the verdicts, and ends its turn with the counts per class and the ten verdicts it is least sure of, for the owner's first sitting. The lane never moves a Hello Revenue card.

### 4. What stays open is ready for the next round

Done means: every card left open after acceptance carries its "live and open" reason in one line, so the prioritisation round starts from a board where every card has already answered "why are you still here".

## Terrain

- The board's own facts: doubts (`board/lane.py` predicates, slice 04), signals (`board/signals.py`), the audit rows, `document_state` and `document_path` on each card.
- Hello Revenue's corpus for the judgment classes: `docs/plans/done/*.md` close-outs (`## Close-out` stances name what each plan delivered), `docs/slice-suggestions/done/` (suggestions already archived name the plan that carried them), `docs/wiki/` for what superseded what. Read-only.
- `needle row` for writing the verdict rows; a new row kind if RULING does not fit (a verdict is a proposal until accepted — say which in the Rulings).
- The frontend's lens switch (`rank`, `age`, `gate` on the board) is where the triage lens joins.

## Acceptance criteria (behaviours)

1. Every open Hello Revenue card shows a class, evidence and recommended verdict; the attention rail counts the unread ones.
2. Accepting a class moves every card in it by the machine with the reason and the owner's name on each history row; overturning one keeps it and records his word.
3. The lane's close-out lists counts per class and its ten least certain verdicts.
4. No Hello Revenue card is moved by the lane itself.

## Rulings

Recorded as the build made them (Claude Fable 5.1 at high, 2026-09-04), each with the alternative rejected.

1. **A verdict is a VERDICT row, one per card, in a grammar the board parses like WATCH's: `<class> — <evidence> → Done|Not now|Decision moment|Backlog|Planned|Up next|stays`.** RULING did not fit: a RULING row is the owner's word, and a proposal wearing that label would read as his. When he rules, the VERDICT row becomes a RULED row carrying his ruling and the verdict's whole text, so the card says one thing about its fate and the history keeps both. Rejected: a table of verdicts (a second store for what a row already holds, and unreachable through `needle row`); a RULING-kind row (the plan's own suggestion).

2. **The board writes the four classes its own facts settle — shipped with the signal read, shipped with a signal only the owner reads, doubted, stale plan — through `needle verdicts SLUG --write`; a session writes the three the corpus decides.** The next cleaning round starts from the machine's read, not from a session re-deriving it. Rejected: the board guessing "built under another name" from titles and stems (a guess in a confident voice, the thing the doubt mechanism exists to refuse).

3. **A plan is stale after 21 days in Planned or Up next with no lane ever.** The 11 Aug oversight read found every plan older than that needing a terrain re-check before execution. Rejected: 30 days (two of the three stale plans on the board would have missed it by a day).

4. **Accepting a verdict that stays on a doubted card re-places the card by the owner's own hand, so the placement becomes his word and is trusted from there; accepting "stays" on a held or trusted card writes no move row.** Seven of Hello Revenue's doubted cards are doubted for a stale link or a lost document, not for missing work; the owner's acceptance is the fact that answers the doubt. Rejected: every accept becoming an owner placement (a held shipped card would stop being re-tested, and the doubt mechanism would go blind exactly where it earns its keep); a doubted card's "stays" leaving it doubted (the owner would accept the same verdict every sitting).

5. **The owner's rulings park; a session's deferrals stay in Backlog.** A suggestion the owner parked, demoted or held back by ruling is superseded by that ruling and goes to Not now with the ruling as its wake; a suggestion a session deferred with a trigger is live and open, in Backlog, with the trigger as its one-line reason. Rejected: every "deferred" head line reading as Not now (Backlog is where a deferred signal lives by the corpus's own convention; the owner's move is the discriminator).

6. **A duplicate or a moot card goes to Not now citing what carries the intent, never to Done.** Done is a closed loop; nothing was delivered under the duplicate's name. Rejected: Done for duplicates (a lie about delivery), Backlog (the board keeps two cards for one intent).

7. **An archived document that names its card links to it, archived.** The corpus read linked live documents only, so a plan written at the close and archived in the same fold left its card doubted "for want of a plan" while naming it from done/. Adjacent to the slice and in its service: a false doubt is a false verdict. The four shipped cards whose plan names no card stay doubted; the close-out names the one-line edit. Rejected: the lane editing Hello Revenue's plans (a lane's git never targets another repository).

8. **Accept all in a class is one request that rules card by card; a refusal stays with its card and the answer names it.** A refused card (a verdict sending a card to Executed with no readable signal) never blocks the class. Rejected: one transaction for the class (one bad verdict would refuse a hundred good ones); the page calling accept per card (a hundred round trips under a lock the loops share).

## Estimate

Execution clock: one lane-day, most of it reading the corpus for the judgment classes. Gate clock: the owner's sittings to accept, which is the point.
