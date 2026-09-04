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

Recorded as the build makes them, each with the alternative rejected.

## Estimate

Execution clock: one lane-day, most of it reading the corpus for the judgment classes. Gate clock: the owner's sittings to accept, which is the point.
