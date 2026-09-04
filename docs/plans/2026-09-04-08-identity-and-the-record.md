# 08 — Identity and the record

**Status:** PENDING
**Written:** 2026-09-04, folding the last two open Backlog items on Needle's own board: `docs/slice-suggestions/2026-09-04-a-rename-that-changes-stem-and-title-keeps-the-card.md` (a defect) and items 2 and 3 of `docs/slice-suggestions/2026-09-04-what-the-first-board-held-that-needle-does-not-yet.md` (the close-out check is project-local; the morning note lost its DELIVERED sentences). Item 4 of that list, the bar widget, is Hello Revenue's and the machine's, not Needle's; the API it needs already exists, and the gap list says so.
**Effort gate:** high — the rename item is a defect with a clear test; the close-out grammar item asks where a project-independent check belongs, which the Rulings decide; the record item is a read-only API a project's own tooling can call.
**Sequencing:** after 07. Independent of the page; touches the corpus reconcile, the parsers and the API.

## Intent

A card's identity survives anything a person does to its document, and the board's record is readable by the projects it serves: a plan that changes its name keeps its card and its history; a project's close-out check is one grammar in one place, held for every project on the board; and what sessions wrote on cards can be read back by a project's own tooling, so nothing that used to live in a card file is lost to a note that reads git.

### 1. A rename keeps the card
As its suggestion says. Done means: a document that disappears in the same read as one appears is a rename when git says so or the bodies match closely; the card keeps its number and gains "renamed from <old path>"; no new card is born; a test renames a suggestion changing stem and title and finds one card with the new document and the old history; cards #11 and #18 on Needle's board are merged into one and the other retired, saying so on both.

### 2. The close-out grammar is Needle's, held for every project
From the gap list, item 2. Done means: the close-out stance grammar (one stance per promise, `met — <evidence>` or `deviated — <pointer>`) lives in `board/` beside the plan-header parsers; `needle close` refuses Executed while the archived plan carries an unstanced promise, naming it, for any project; Hello Revenue's `scripts/plan_close_out.py` and its archive gate import or mirror the same grammar so there is one — the plan decides which direction the dependency runs and records it as a ruling; a test closes a card whose plan has an unstanced promise and is refused.

### 3. The record is readable by the projects it serves
From the gap list, item 3. Done means: a read-only API and a `needle` verb give any project's tooling every row ever written on its cards (DELIVERED, WATCH, REVIEW, RULING and the rest) with the card, the time and the writer, as JSON; Hello Revenue's morning note can read its DELIVERED sentences again from it instead of from a card file that no longer exists, and the note's reader docstring that records the loss is updated by this lane with a commit on that repository's develop when its tree is clean, otherwise the exact edit goes in the close-out.

## Terrain
- `board/reconcile.py` (born, archived, renamed effects), `infrastructure/corpus.py` (the watcher's paired events), `runtime/git.py` (a rename detector over the corpus), `board/parse.py` (plan header parsers), `api/app.py` and `api/cli.py` (the rows API and verb), `infrastructure/store.py` (rows and audit).
- Hello Revenue: `scripts/plan_close_out.py`, `scripts/archive_docs.py`, the morning note under `.github/workflows/` and its reader.

## Acceptance criteria
1. Rename a suggestion changing both stem and title: one card, new document, old history, no new card.
2. `needle close` refuses an Executed close whose archived plan has an unstanced promise, naming the promise, on a fixture project.
3. `needle rows <project>` (or the API) returns every row on every card as JSON; the morning note's reader in Hello Revenue reads from it, or its exact edit is in the close-out.
4. Cards #11 and #18 are one card on Needle's board with the merged history.

## Rulings
Recorded as the build makes them, each with the alternative rejected.

## Estimate
Execution clock: half a lane-day. Gate clock: none.
