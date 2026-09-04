# 04 — The loops move in

**Status:** PENDING
**Written:** 2026-09-04, the afternoon of the cutover, from three measurements and one ask. Measured at 15:10: of Hello Revenue's 66 Executed cards, 54 carry a WATCH row and 0 are readable by Needle's signal grammar — every one is prose written for a person. The owner's ask, verbatim in substance: the measure step must not depend on his brain; his brain is the last fallback, a "hey Dennis, please look at this". And on the open card: "I only found stop, discuss, open the plan and copy the path", and "those action buttons are better at the top of the card".
**Effort gate:** high — three of the four items are specified by slice 03's grammar and this repo's ratchets; the fourth (translating 54 prose signals into readable ones) is judgment work, bounded by a written rule for what becomes a machine reader and what becomes a question, with the table of decisions in the close-out.
**Sequencing:** after 03. Item 4 edits Hello Revenue's close ritual and waits for that repository's card #387 (retire the first board) to fold first, so two lanes never hold its docs at once.

## Intent

Needle is the home of the loops, and the loops actually live there. A shipped card's signal is read by the machine on its cadence wherever a reader exists, and the owner is asked only where no machine can read, as one batched question with one click each way. Every machine-placed status shows the evidence it rests on, and doubts itself the moment that evidence is gone. And the card's doors are where the owner's hand already is.

### 1. Every machine-placed status names its evidence and doubts itself

From `docs/slice-suggestions/2026-09-04-every-machine-status-names-its-evidence-and-doubts-itself.md` (archive it with this plan). Done means: the predicate behind each machine-placed column is one function in `board/` over the loop's facts; every machine move records which predicate it satisfied; on every read each machine-placed card is re-tested and a card whose evidence is gone carries a doubt mark on the page with the missing fact in words, and counts in the attention rail, independent of any move; the owner's own placements are never doubted; the 0.1 import's placements in machine columns start as "evidence unknown" until the first read confirms or doubts them; a test kills a lane's process and sees the doubt on the next read.

### 2. The doors are at the top, and a window that is open is a door too

Today the doors render below the record, and Watch disappears when a window is already open, with its reason in a tooltip nobody hovers ("A window into this session is already open" was the exact state when the owner looked for it on #387). Done means: the doors row sits directly under the card's title on the open card, before the summary; a live lane whose window is open offers **Focus its window** (the compositor brings the tab forward, through the runtime, proved by the focused window's app-id) in Watch's place; every closed door that the owner would expect on this card (Watch, Answer, Look, Resume) is shown closed with its reason in text, not hidden; the comp for the open card is amended and re-signed in the plan's Rulings, not rebuilt.

### 3. The shipped cards' loops are readable

Done means: each of the 54 prose WATCH rows on Hello Revenue's Executed cards is rewritten in the signal grammar (`<what> — url|file|command|owner <target> [expect …] by YYYY-MM-DD [every Nh]`), through `needle row`, never by editing a card by hand, with the original text kept in the card's history; the rule for the rewrite is written first and applied uniformly: a signal a machine can read (a file in `docs/plans/done/`, a URL, a command in the project's own tooling with a stated expectation) becomes that reader; everything else becomes `owner`, with the question as the `what`. **Ruling:** owner questions are batched — the attention rail says "N shipped cards wait on your reading" and opens one list with one click each way per card, never N separate asks; due dates for translated rows are today plus seven days unless the original names a real event (a build, a deploy, a date), which is kept. The close-out carries the table: card, original text, reader chosen, why.

### 4. Hello Revenue's close ritual writes the grammar

Done means: the `hr-plan-execute` skill's close step and the one line in `CLAUDE.md` that names the WATCH row teach the grammar with one example of each reader kind, so no future close writes prose again; edited with a commit on that repository's `develop` only when its tree is clean and card #387's lane has folded, otherwise the exact edit goes in this plan's close-out for the coordinating session. Needle's own `README.md` shows the same grammar in one place, and `needle close` refuses a WATCH row it cannot parse, saying the grammar.

## What this slice does not do

It does not add readers beyond url, file, command and owner. It does not touch Hello Revenue's plans or suggestions under `docs/`, only the two instruction files in item 4.

## Terrain

- `board/signals.py` (`parse_watch`, `GRAMMAR`, the readers), `api/loops.py` (the signal cadence, the exit and entry rules, `since`), `board/lane.py` (the predicates behind Executing and the exit; `entered_executing_at`), `board/assemble.py` (the attention rail), `frontend/src/board/OpenCard.tsx` (the doors row at the bottom today; `door("watch", …)`), `runtime/` (windows: `needle window`; focusing needs one more verb, proved like a window).
- The measurement script that found 0 of 54, for the close-out to re-run: read every Executed card, count WATCH rows, count those `parse_watch` accepts.
- The Hello Revenue close ritual: `.claude/skills/hr-plan-execute/SKILL.md` and the WATCH line in `CLAUDE.md` in that repository; card #387's lane is rewriting the doors those files name — read its branch or its fold before editing.

## Acceptance criteria (behaviours)

1. Kill a lane's process by hand: the card shows a doubt within one read, with the missing fact in words, and the attention rail counts it; after the loop moves the card the doubt is gone.
2. The open card shows its doors under the title; with a window open, Watch reads "Focus its window" and clicking it brings the tab forward.
3. Re-run the measurement: 54 of 54 WATCH rows on Executed cards parse; the attention rail shows one batched owner question, not dozens.
4. `needle close` with a prose WATCH row is refused with the grammar in the message.
5. Hello Revenue's close instructions carry the grammar, or the exact edit is in the close-out.

## Rulings

Recorded as the build makes them, each with the alternative rejected.

## Estimate

Execution clock: one lane-day, half of it the 54 translations. Gate clock: card #387's fold, for item 4 only.
