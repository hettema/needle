# A defect's mark is verified before it routes, and an unmarked one is nobody's yet

**Carries:** docs/slice-suggestions/done/2026-09-05-a-defects-mark-is-verified-before-it-routes-and-an-unmarked-one-is-nobodys-yet.md
**Status:** PENDING
**Written:** 2026-09-05, by the Claude session f4d2a309 that ran the day's measurement and the first Claude-to-Codex call, from the suggestion it filed and Sol's reply (`~/.cache/omarchy/claude-acct/discussion/from-sol-where-the-decision-line-falls.md`), after Dennis ruled the boundary true and ranked this card second in Up next. Written here rather than by a dial planning session because Needle's own defects wait behind #43 and the context that wrote the suggestion was still warm.
**Effort gate:** high — the mechanics are small (one typed state, one reader, one door, one line on the dial) and every path they touch exists; the judgment is in item 3, which must add a second pair of eyes without building a committee, and in item 5, where the owner's answer has to reach the repository through a session's commit because the board never writes the corpus.
**Sequencing:** none as a hold. #57 (Sol callable through Needle) makes item 3's different-make triage a board act instead of a hand relay, and #58 measures whether different make earns its cost; both read this card's rows, neither is needed to ship it. #58 holds on this card, not the other way round.

## Intent

A defect the machine can fix never waits on the owner, and a decision that is the owner's reaches him through a door he can open. Today an unmarked defect reads as his — the safe default, applied once by the session that filed it and never re-read — and a `his` card has no door at all, because `api/doors.py::answer` resumes a live lane's session and a parked suggestion has none. The rail's decision pile therefore drains at zero: eight live `his` defects, the oldest 41 days, and zero `answered` rows in the board's life. Re-read under the rule the owner ruled on 2026-09-05, five of the eight were never his. After this plan: an unmarked defect is nobody's yet and says so; a mark carries the source that selects it; a second session verifies a mark before the dial acts on it; a settled half never waits behind an unsettled one; and a genuine `his` card opens to his sentence from the board.

The rule, in the words the owner ruled true:

> A decision is Dennis's only when the written record does not select among materially different outcomes he owns, or when acting would create external exposure beyond a bound he has already authorised. Applying an existing intent, ruling, precedent or authorised bound is execution, not a new decision. Effect-level reversibility is evidence about how safely to act under uncertainty; it is never the test of who owns the call.

## What the evidence settled

- **The default is one line in three places.** `domain/document.py::FixMark`'s docstring, `board/dial.py::why_not_eligible` (`"an unmarked defect reads as his"`) and `docs/HOW-WE-WORK.md` §8 ("an unmarked defect reads as theirs"). Hello Revenue's `tests/ratchets/test_suggestion_fix_mark.py` restates it and is HR's own to change.
- **A `now` mark already keeps its why.** `board/parse.py::fix_of` returns `Fix(mark, why, trigger)`; `why` is the rest of the line. Nothing reads it. Item 2 is a reader, not a new field.
- **The door is closed by one branch.** `board/lane.py` ~811: with no live session, `Answer` is `_closed("No live session to answer.")`. Item 5 opens a different door on that branch, not a different lane.
- **The triage shape exists.** `runtime/launch.py::windowless` starts a session in the project's checkout with no worktree, used for signal readings (plan 09) and dial planning (plan 11). A triage is the same walk with a different brief.
- **The founding sample is in the corpus.** Hello Revenue `59661dcd9`: five marks flipped with their sources cited, two documents split, one new card (#435). Item 6's reader has data on day one.

## Items

### 1. An unmarked defect is nobody's yet

`why_not_eligible` answers `needs triage` for an unmarked defect and the waiting list groups it under that word, apart from `marked his`; the card shows the state on its head. The doctrine sentence in HOW-WE-WORK §8 moves to the new rule through #54's item 5 path — a learning returns on a card, and this is the card — so the text changes in this lane's commit and nowhere else. Done means: an unmarked defect appears in `needle fixes` under `needs triage`, in neither the his pile nor the auto-fix queue, and §8 reads the rule above.

### 2. A mark carries the source that selects it

A reader beside `fix_of` judges the `why`: a `now` names a document, a ruling, a precedent or an authorised bound (a backticked path, a card number, a plan or slice name, or the word `bound` with what it is); a `his` names an unresolved owner outcome or an unbounded exposure, and a why that is only a category word — "product call", "prompt change", "new surface", "UX" — is refused as no reason. Needle's own ratchet (`tests/ratchets/test_every_suggestion_names_its_kind_and_fix.py`) holds both forms on this corpus; other projects learn the line from the briefs, as the ratchet's docstring already says. Done means: fixtures for a `now` with no source, a `his` with only a category word, and both valid forms; the ratchet refuses the two bad ones and names the line.
Hands out: execution — the ratchet suite and the parser tests after each change, every failure verbatim; verifies by re-running the one failing test it names before acting on it.

### 3. A second pair of eyes before the dial acts

Before `_plan` takes a `now` defect, the dial opens a windowless triage reading with a brief that carries the rule, the document, the cited source and nothing else, and asks one question: does the source select the outcome? The reading ends with one row on the card — `TRIAGED now — <source verified>`, `TRIAGED his — <the unresolved outcome>`, or `TRIAGED when — <trigger>` — and the dial acts only on a `now` that carries the row. Independence of context is the requirement; the triager is a different make when #57 makes Sol callable and #58 is measuring, and the same make otherwise. The finder's mark is a proposal; the row is the decision, and both stay on the card. Done means: a `now` defect the dial plans carries a `TRIAGED` row naming what was verified; a triage that disagrees with the mark leaves the row and the dial follows the row, not the line; the dial never plans a `now` without one; a fixture covers agree, downgrade and upgrade.

### 4. A settled half never waits behind an unsettled one

The triage brief names the split: when a document holds an outcome the record already selects beside one it does not, the reading files the settled half as its own suggestion marked `now` with its source, and narrows the original's `his` to what remains, with a `Split:` row on both cards. Done means: the Meta selection split of 2026-09-05 (HR `59661dcd9`, card #435) is reproduced by a fixture from a two-item document, and the founding case is cited in the brief.

### 5. A genuine `his` card has a door

On the branch that closes `Answer` for want of a live session, a card whose document is marked `his` and whose `TRIAGED` row agrees offers `Answer` instead: his sentence lands as an `ANSWERED` row on the card (the door's existing audit kind) and opens a windowless session in the project's checkout whose brief is the row, the document and the rule, and whose one job is to rewrite the mark to `now` citing the row — or to `when` if his answer names a condition — and commit and push, so the dial takes it on the next beat. The board writes the row and starts the session; the session writes the repository. Done means: from the board, the owner answers a parked `his` card with no lane; the row appears; the mark flips in a commit that cites the row; `needle fixes` shows the card as `now` on the next read; the first `answered` row in the board's history exists.

### 6. The loop can be read from one command

`needle fixes` gains the list the loop needs: every decision a `TRIAGED` row moved off the owner's rail, in order, with the source it cited and what has happened to it since (planned, folded, defect filed against, reverted). Done means: the first five and the first ten are readable from one command with their sources and their fate, so the cold audit in the Loop below is an act, not a reconstruction.
Hands out: search — the audit rows, the fix lanes and the corpus documents behind each listed decision, returned as rows for the reader to join; verifies by reading one listed card's history against the row it produced.

## Acceptance criteria

1. An unmarked defect routes to nobody and says `needs triage`; the doctrine's one text says so.
2. A `now` mark with no source and a `his` mark with only a category word are refused by the ratchet on this corpus.
3. No `now` defect enters a dial plan without a `TRIAGED` row; a disagreeing row wins over the line.
4. The owner answers a parked `his` card from the board, a session flips the mark in a commit citing his row, and the dial takes the card — the first `answered` row on record.
5. Backend, ratchet, TypeScript and frontend suites green; `needle fixes` lists every colleague-taken decision with source and fate.

## Loop

We think verifying a mark in a second context before the dial acts, and giving a `his` card a door, will move the owner's decision pile from a stock that grows ~0.2 per fold and drains at zero to one that drains faster than it grows, because five of eight parked decisions were execution mislabelled by the session that found them, and the three that were his had no way to reach him. Fixed now, before any data: the owner audits the first five and the first ten colleague-taken decisions cold, from item 6's list, before seeing their outcomes. The classifier fails if any decision exceeded an authorised exposure bound; chose between materially different owner outcomes with no written source selecting one; was defended as reversible at the code level while its effect was not; if he would have decided differently on more than one of the first ten; or if the set shows a shared direction no individual citation disclosed. On failure the response is not revert — once a customer has seen something there is nothing to revert — it is: stop downgrades in that class, reclassify the open pile, show him the accumulated direction, tighten the rule on the observed mismatch, and resume only after a revised classifier passes a fresh predeclared sample. If after twenty decisions the pile still grows, the rule is wrong, not the owner, and this card reopens.

## Deliberately not

- A router that edits doctrine or rewrites a mark without a row a person can read.
- Two AIs on every card; #58 decides whether different make earns its place, on this card's rows.
- Hello Revenue's own ratchet; HR learns the line from the briefs and changes its ratchet on its own card.
- The quiet-machine rule (#43), which gates this card's lane like every Needle lane.
- Reversibility as the ownership test; it is evidence in the triage brief, and the plan's Rejected section in the suggestion says why.

## Terrain

- `domain/document.py` (`FixMark`, `Fix`), `board/parse.py::fix_of` and a new reader beside it
- `board/dial.py::why_not_eligible`, `api/dial.py::_take_next`, `_plan`, `FixReport`
- `board/lane.py` (the Answer door's closed branch), `api/doors.py::answer`, `domain/audit.py` (`ANSWERED`, a `TRIAGED` and a `SPLIT` row)
- `runtime/launch.py::windowless`, `board/brief.py` (the triage brief)
- `api/board_cli.py::fixes`, `frontend/src/board/` (the `needs triage` state on the head)
- `docs/HOW-WE-WORK.md` §8, `tests/ratchets/test_every_suggestion_names_its_kind_and_fix.py`

## Close-out

Written by the lane: the first `answered` row and the commit it produced; the triage rows on the founding five; the ratchet's two refusals demonstrated; the doctrine sentence before and after; every review pass and correction; full-suite results; and item 6's list as it stood at the close, so the loop's first audit has its sample.
