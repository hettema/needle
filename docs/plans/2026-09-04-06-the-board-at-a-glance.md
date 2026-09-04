# 06 — The board at a glance

**Status:** PENDING
**Written:** 2026-09-04, folding four Backlog suggestions from the owner's first hour with the board into one slice, on his ruling that several cards are often one slice's worth: `docs/slice-suggestions/2026-09-04-an-archived-document-moves-its-card.md`, `docs/slice-suggestions/2026-09-04-defects-are-their-own-rail-in-backlog.md`, `docs/slice-suggestions/2026-09-04-the-collapsed-card-says-whether-it-can-start-now.md`, `docs/slice-suggestions/2026-09-04-the-head-and-the-column-names-stay-on-screen.md`, and the Plan door from `docs/slice-suggestions/2026-09-04-a-plan-door-for-one-card-or-several.md`.
**Effort gate:** high — five items, each specified in its suggestion; the judgment is visual (a pinned head, a defects rail, a pill and two doors on the collapsed face) and the owner judges it by use. Amend the comp in the Rulings; do not rebuild it.
**Sequencing:** after 05 (it touches the same page and rules). The Plan door's "the card follows the plan" rule is this slice's item 5 and the archived-document rule is item 1; they are one mechanism, the corpus watcher acting on a document event.

## Intent

The owner reads the board without opening cards: each closed card says whether it can start and lets him start it or plan it from there; defects and ideas are two scans, not one; the head and the column names never leave the screen; and a card's document event — archived, or a plan written for it — moves the card by the machine, with the reason on its history.

### 1. An archived document moves its card
As its suggestion says. Done means: on the corpus's archived effect, a card outside a shipped column with no live lane moves to Executed when it carries DELIVERED and a readable WATCH, otherwise to Decision moment with "its plan was archived, but no session wrote it up on the board"; an audit row names the document; a test archives an Up next card's document and finds it in Decision moment on the next read.

### 2. Defects are their own rail
As its suggestion says. Done means: `**Kind:** defect|idea` on a suggestion document (absent reads idea); a pinned defects rail at the top of Backlog with its count; the attention rail counts unplanned defects and ideas apart; old suggestions get their kind read from their text where the lane can tell, with its table of guesses in the close-out.

### 3. The collapsed card says whether it can start now
As its suggestion says. Done means: one pill on every Planned and Up next card — free, collides with #N, no gate, nowhere to run — computed by the Start door's own function; Start on a free card's collapsed face; "Start anyway" only on the open face; a gateless document's open card shows Start closed with its reason.

### 4. The head and the column names stay on screen
As its suggestion says. Done means: head, attention rail and column headings pinned; each column scrolls on its own; an open card stays in view; on a laptop the head folds to one line after the first scroll; a page test scrolls a column and asserts the heading and the rail are in the viewport.

### 5. The Plan door, and the card follows the plan
As its suggestion says. Done means: Plan on every suggestion card, collapsed and open, opening a plan-writing conversation with the brief the suggestion specifies; "Plan these together" over a selection; when a plan citing a live suggestion lands, the watcher relinks the card (same number, same history), archives the suggestion beside it with "carried by <plan>", and moves the card to Planned by the machine; a plan citing several suggestions relinks the first and marks the others folded into it, grouped under its card until it closes; the attention rail counts suggestions without a plan. **Ruling:** this slice's own five suggestions are the first to be folded this way: this plan cites them, so when it lands the watcher relinks and folds them — the lane verifies that on its own card first.

## Terrain
- `infrastructure/corpus.py` and `board/reconcile.py` (the archived and born effects; add relinked-to-plan and folded-into), `api/loops.py` (where effects become moves), `board/lane.py` (the exit reasons), `board/collision.py` and `api/doors.py` (the Start door's function, to be shared with the pill), `frontend/src/board/` (Board, the column headings, the card faces, the doors row), `frontend/src/components/ui/`.
- The plan shape for the Plan door's brief: `docs/plans/README.md` here; Hello Revenue's `hr-plan-write` skill there — the brief names the project's own skill when its `.claude/skills/` has one.

## Acceptance criteria
1. Archive an Up next card's document with no lane: Decision moment on the next read, reason on the row.
2. A suggestion with `Kind: defect` sits on the defects rail; the rail counts it; the attention rail counts it apart from ideas.
3. Every Planned and Up next card shows its pill; a free card starts from its collapsed face; the gateless open card shows why Start is closed.
4. Scroll a long Backlog: the head, the rail and every column heading stay; Executing does not move.
5. Press Plan on a suggestion: a window opens with the plan-writing brief; when the plan file lands citing the suggestion, the same card is in Planned with the plan as its document and the suggestion archived; a plan citing three suggestions leaves one relinked card and two folded under it.
6. The lane's own plan, which cites five suggestions, relinks and folds them when it lands; the close-out says which card kept the number.

## Rulings
Recorded as the build makes them, each with the alternative rejected.

## Estimate
Execution clock: one lane-day. Gate clock: none; the owner judges by use.
