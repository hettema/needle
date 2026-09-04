# 07 — Conversations and lanes that know each other

**Status:** PENDING
**Written:** 2026-09-04, folding two Backlog suggestions and one item of a third into one slice on the owner's ruling that several cards are often one slice's worth: `docs/slice-suggestions/2026-09-04-an-idea-door-in-the-head.md`, `docs/slice-suggestions/2026-09-04-lanes-that-run-together-know-about-each-other.md`, and item 1 of `docs/slice-suggestions/2026-09-04-what-the-first-board-held-that-needle-does-not-yet.md` (Start is the owner's click, held by no ratchet).
**Effort gate:** high — the mechanics are specified in the suggestions; the judgment is where the watercooler lives (a file in the project or the board's store) and what a lane is told about its neighbours, decided in the Rulings.
**Sequencing:** after 06. Item 3 is a ratchet and can land first if the lane prefers.

## Intent

A conversation starts from the board about nothing yet, and what it writes becomes a card. Lanes that run at the same time know about each other before they start, are told when they drift into each other's files while they run, and say what they touched before they fold, so a collision is either refused, seen, or written down — never silent. And no loop can ever start a lane: that is the owner's click, held by a test.

### 1. An idea door in the head
As its suggestion says. Done means: Idea in the head of every project's board opens a conversation in that project's checkout on the rule's slot and model, with the brief the suggestion specifies and an optional first line typed into the door; listed on the attention rail as in discussion; never hands on a tree; a document it writes becomes a card whose history says it was born from a conversation.

### 2. Lanes that run together know about each other
As its suggestion says. Done means: every lane's brief lists the other live lanes on the project with their footprints and one line each; the board recomputes footprints from live worktrees' actual diffs on every read and marks drifted lanes as colliding on both cards and the rail; a watercooler per project that every lane reads at start and before the fold and appends to when it touches a seam, its last line shown on each live card; a fold that rebased over another live lane's edits says so on the card; the two-lane fixture test.

### 3. Start is the owner's click, held by a ratchet
From the gap list. Done means: a ratchet under `tests/ratchets/` proves the runtime's start is reached from the doors module only and never from the loops module, in the shape the gap list describes; the gap list's suggestion gains a line saying which of its four items this closed.

## Terrain
- `api/doors.py` (Discuss's brief and window as the shape for Idea), `runtime/` (windows, start), `board/collision.py` and `runtime/git.py::changed_files` (footprints and live diffs), `board/brief.py` (what a lane is told), `api/loops.py` (the read), `tests/ratchets/test_the_board_never_runs.py` (the ratchet family to extend).
- The machine-level discussion folder is the precedent for a watercooler and not the thing itself: that one is for sessions on this laptop; this one belongs to a project on the board.

## Acceptance criteria
1. Idea opens a window with the brief; a plan the session writes is a card within seconds with the conversation in its history.
2. Two fixture lanes with overlapping actual edits are marked colliding on the next read; each lane's brief names the other; a watercooler line from one appears on the other's card; a fold over the other's edits is named on the card.
3. The ratchet fails on a call to the runtime's start from the loops module.

## Rulings
Recorded as the build makes them, each with the alternative rejected.

## Estimate
Execution clock: one lane-day. Gate clock: none.
