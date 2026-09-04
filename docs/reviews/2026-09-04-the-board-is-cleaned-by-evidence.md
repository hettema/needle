# Review — the board is cleaned by evidence (slice 05)

**Plan:** docs/plans/done/2026-09-04-05-the-board-is-cleaned-by-evidence.md
**Reviewer:** the build session (Claude Fable 5.1 at high), reviewing its own diff in passes before the fold. No second session was in the loop; the owner's first sitting over the triage lens is the sign-off this record cannot replace.
**Diff range:** e8df0ac..HEAD on `worktree-card-9-05-the-board-is-cleaned-by-evide` (the verdict type and row kind; the grammar and the four machine classes in `board/verdicts.py`; the store's one-act ruling and the shared inner move; the accept, overturn and accept-class doors and routes; `needle verdicts` and the VERDICT check in `needle row`; the relink from archived documents; the triage lens and its four primitives; the tests; the README).
**Findings:** 4 — 3 fixed before this record, 1 no change.

## The passes

The review ran as a loop (CLAUDE.md): each pass one lens, fixes landed, the next pass re-read the fixed work.

1. **The feature against the plan's "done means".** Item 1: every open card can carry one class, an evidence sentence and a recommended verdict as a VERDICT row; `needle verdicts` writes the classes the board's facts settle and a session writes the rest; nothing is moved by a verdict (`tests/board/test_verdicts.py`, `tests/api/test_cli.py`). Item 2: the page has a Triage lens listing every unread verdict grouped by class with Accept all in this class, Accept and Overturn; accepting moves by the machine with the reason on the history row and the owner as actor; overturning keeps the card and records his word; the lens is reached from the attention rail (`tests/api/test_triage.py`, `frontend/tests/board.test.tsx`). Items 3 and 4 are the lane's own work on Hello Revenue's board, recorded in the plan's close-out. Findings 1 and 2 came from this pass.
2. **The seams.** Concurrency: every ruling runs under the loops' lock like any door, and accept-all is one request that rules card by card, so a store refusal on one card stays with that card and the rest land. Failure and restart: a ruling is one transaction (the VERDICT row becomes RULED and the move lands together or not at all); a page whose ruling failed shows the store's words and re-reads. Truth of what the board shows: the count and the list are derived from the rows on every read, never stored, so a verdict written from a terminal is on the rail within the store watcher's beat. Findings 3 and 4 came from this pass.
3. **The boundaries.** Layers: `board/verdicts.py` imports domain and board only; the doors compose. The board never runs. Typed edges regenerated for `row`, `board` and the new `verdict` module; the page's new lines use the generated types. One design system: the four new primitives live in `components/ui` and the lens composes them. No deferral marker. The store's shape is unchanged (no migration: a row kind is a value). The fixture regenerated and compared. Nothing new found; the pass was clean.

## Dispositions

1. **A hand-written verdict on an Executing card that stays would have been read by the exit rule as the owner taking the card out, and by the return rule as where it came from.** The owner's re-placement of a doubted card (accepting "stays") writes a move whose from and to are the same column. FIXED: `owner_moved_out_after` and `came_from` ignore a move that leaves the column it entered (`tests/board/test_lane.py::test_the_owner_keeping_a_card_in_executing_is_neither_an_exit_nor_an_entry`).
2. **The parser refused `superseded → Not now` with "names no class" instead of "carries no evidence".** The head pattern demanded a separator after the class. FIXED: the arrow may follow the class directly, and the row is then refused for what it lacks.
3. **A verdict rewritten between the owner's read of the lens and his click would be accepted as it now reads, not as he saw it.** The door re-reads the card at accept time and says in its answer what it accepted. NO CHANGE: the answer names the verdict acted on, and a session rewriting a card's verdict while the owner sits over the lens is the collision the store's history keeps (the previous text stays on the ROW audit row).
4. **Three of Hello Revenue's shipped cards read doubted for want of a plan they had: the plan sat in done/ naming the card, and the corpus read only links live documents.** Adjacent to this slice and in its service (a false doubt is a false verdict). FIXED: an archived document that names its card links to it, archived (`tests/board/test_reconcile.py::test_an_archived_plan_naming_a_card_links_to_it_archived_and_is_never_born`). Four more shipped cards name no card in their plan and stay doubted; the verdicts say so and the plan's close-out names the one-line edit for the coordinating session.

## What was checked

- **The suite on the fixture floor**: 250 backend tests (the ratchets included), `npx tsc --noEmit` clean, 24 vitest scenarios (one new: the rail chip opens the lens, the groups in class order, Accept, Accept all in this class and Overturn with the word, back to Rank).
- **The grammar against the 194 judgment verdicts written for Hello Revenue** before any was written: each rendered and parsed back to the same verdict, each naming an open card, no arrow inside an evidence sentence.
- **The corpus read for the judgment classes**: every live suggestion cross-referenced against every other document under `docs/` (the mentions read in full for the 40 with a plan behind them), the archived suggestions' status lines, the 2026-08-11 open-plans oversight read, and the code itself for the suggestions the code can answer (the legacy nonce fallback, the trust-signal slot, `submit_hosted_form`'s home, the raw-button regex, the silent-fallback allowlist, the chat route's lookup — each still true on 2026-09-04).
- **Against the real board, after the fold and the restart**: the verdicts written through `needle row` and `needle verdicts --write` from this lane, the attention line's count and the lens read over HTTP; recorded in the plan's close-out.

## What the build learned the plan got wrong

- The plan asked for the verdict "as a RULING-kind row the owner has not yet accepted". A RULING row is the owner's word; a proposal wearing that label would read as his. Ruling 1: a VERDICT row, which becomes RULED the moment he rules.
- The plan's table sends a doubted card to Decision moment "or back where it came from". Seven of Hello Revenue's doubted cards are doubted for a stale link, not for missing work; their verdict is "stays", and accepting it is the owner's re-placement (ruling 4).
- The plan expected the machine classes and the judgment classes to be one table written by the lane. They are two writers: `needle verdicts` for the four the board can say, so the next cleaning round starts from the machine's read, and `needle row` for the rest.

## Not done, stated

- **The served page needs the main checkout's `frontend/dist` rebuilt and the login service restarted after the fold** (dist is git-ignored). This lane does it and records the result in the plan's close-out, because the verdict rows cannot be written before the served code knows the row kind.
- **Four of Hello Revenue's plans name no card** and their shipped cards stay doubted until a `**Card:** #N` line is added on that repository's `develop`; the exact lines are in the close-out. A lane's git never targets another repository.
