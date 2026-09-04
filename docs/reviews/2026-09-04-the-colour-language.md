# Review — the colour language (card 27)

**Plan:** docs/plans/done/2026-09-04-the-colour-language.md
**Reviewer:** the build session (Claude Opus 5 at high), reviewing its own diff
in passes before the fold. No second session was in the loop. The plan's gate
is the owner's day of use, and that is this card's WATCH signal — this record
cannot replace it.
**Diff range:** 16a8023..HEAD on `worktree-card-27-the-colour-language` (three
code commits: the language itself; what the served board showed and jsdom
could not; the signal that could go unnoticed. The docs commit that follows
carries this record and the archived plan).
**Findings:** 12 — 11 fixed before this record, 1 filed.

## The passes

The review ran as a loop (`CLAUDE.md`): each pass read the work through one
lens, the fixes landed, and the next pass re-read the fixed work.

1. **The feature against the plan's "done means", on a running board.** A
   throwaway store over the synthetic Harbourmaster project, this build's
   `dist`, headless Chromium at 1440×900 through the DevTools protocol
   (`tools/`-shaped, kept in the job's scratch since it is a one-off of the
   scroll check). Item 1: the head is 44 px — one line — with the three words
   in `--attn`, `--wrong` and a quiet `--ink-2` for a count of zero; clicking
   *Your move* took the board from 26 cards to 8 and raised two sub-filters,
   clicking again restored 26. Item 2: every card on the page carried a state
   line with a word and either a door or a hint, and the border took a
   meaning's colour for exactly the live, asking and broken cards and for no
   other. Item 3: the loop glyph measured 14×14 and an owner-only ring came
   back `rgb(214, 160, 74)` — `--attn`. Item 4: the open card's top lands as
   the comp draws it. Item 5: the triage lens read `Up next → Done` in green,
   `→ Not now` in grey, `→ Decision moment` in amber, with *Accept all N* per
   uniform class and *read each* on the doubted one. Findings 1 to 4 came from
   this pass.
2. **The seams.** Concurrency and restart: nothing new is stored, no
   migration, no new process; the state is derived at read time from facts the
   loop already had, and a board read measured 23–28 ms. The truth of what the
   board shows: this is where the pass paid. Rebuilding the head as claims
   meant every count and the cards a click leaves behind now come from one
   function, so they cannot disagree — but the rebuild had silently dropped
   one of the old counts (finding 5), and the filter was showing a column's
   unfiltered count and fold (finding 4). Findings 5 and 6 came from this
   pass.
3. **The boundaries.** `board/` imports domain and `board/` only; no
   `subprocess` anywhere near it; the typed edges regenerated for `board` and
   `lane`; the fixture regenerated from the synthetic project; one design
   system — the `pickable` wrapper had to move into `components/ui` because
   the board may write no class name of its own, and the ratchet said so. No
   deferral marker. The new ratchet, `test_the_colour_language.py`, is the
   one this slice adds. Finding 7 came from this pass.
4. **The rule against itself, and the fixed work re-read.** Every word
   `state_of` can name, listed out of the source, against the words anything
   asserts: six were reachable and unasserted. Writing their tests found the
   defect this record is most glad of (finding 8) and one more (finding 9).
   Findings 8 to 11 came from this pass.
5. **Clean.** The suite re-run whole: 312 backend tests including the
   ratchets, `tsc` clean, 55 page scenarios; the live check re-run against the
   rebuilt board with no findings; the four screenshots re-read. Nothing new.

## Dispositions

1. **The collapsed door's label pushed the state word off the line.** The
   backend's Start label is `Start · fable on alpha`; beside it, at a 288 px
   column, `free to start` rendered as `free to sta…`. Only visible on a laid
   out page — jsdom asserts text, not width. FIXED: the face door is one word,
   `Start`, with the placement in its reason and unchanged on the open face
   (plan ruling 6).
2. **The Plan door said two different things on the two faces.** `state_of`
   hard-coded `Create plan` for the collapsed face while `doors.plan.label`
   said `Plan`. FIXED at the source: `doors_for` names it `Create plan` and
   both faces read the door's own label (ruling 6).
3. **An "open ▸" hint truncated the loop line it sat beside.** `loop open ·
   you read i…` at column width. Every card opens on a click, so the hint said
   nothing the gesture did not. FIXED: a state carrying a loop has no hint
   (ruling 7).
4. **A filtered column counted and offered cards the filter had taken away.**
   Backlog read "9" over an empty column and offered "+ 9 more in Backlog";
   four group headings stood over nothing. FIXED: a filtered column drops
   empty groups and recounts what it shows (ruling 8), with a page scenario.
5. **A signal the board said it would read and has not could go unnoticed.**
   The old `Attention.signals_due` counted shipped cards past their due date
   with nothing delivered; rebuilding the head as claims dropped it and
   nothing replaced it. An owner-only signal past due still reached him
   (`signal asking`), but a `url`, `file`, `command` or `session` signal past
   due said `loop open · 1 Sep passed, unread` on its own card and appeared
   nowhere else — a card going quietly unforgotten, which `docs/INTENT.md`
   says the board must never have. FIXED: `Claim.SIGNAL_OVERDUE`, counted
   under Broken, and the card's own word turns red with it — the card names a
   reader and that reader has not read, which is two things disagreeing.
6. **The state line and the card top could not wrap.** `.state` and
   `.card-top` were `display: flex` with no `flex-wrap`, so the door's answer
   ("Started aaaa0001, fable on alpha, …") would squeeze rather than wrap, and
   a card with a gate, a New mark and two tags would overflow its top line.
   jsdom cannot see either. FIXED.
7. **The board wrote a class name of its own.** The hover wrapper for the
   "plan these together" `+` was `<span className="pickable">` in
   `CardView.tsx`. FIXED: a `Pickable` primitive in `components/ui`;
   `test_one_design_system.py` is what caught it.
8. **A lane that folded cleanly read as broken.** `state_of` painted every
   `LaneState.ENDED` lane red outside the shipped columns. A lane that folded,
   synced the trunk and left its worktree on disk is *finished*, not broken —
   and it would have gone red on every card whose work had just landed, until
   somebody removed the worktree. Nothing on the two live boards was in that
   state when this was found, so it would have shipped and surfaced later, on
   the next card that folded without its worktree being cleaned. FIXED: an
   ended lane is broken only when nothing was folded — the work is what was
   lost, not the ending — and a folded lane falls through to the quiet "lane
   exists" that Start already says.
9. **`lane exists` was unreachable.** The consequence of 8: `StartState.TAKEN`
   could never reach the state line, because the ENDED branch caught it first.
   FIXED with 8, and asserted.
10. **Six words the rule could name, and nothing asserted.** `stopped`,
    `blocked`, `moving`, `lane exists`, `archived` and a gateless planned card
    were reachable from `state_of` with no test naming them. FIXED: four tests
    in `tests/board/test_language.py`, written by listing every `_state(...)`
    literal out of the source and subtracting what the suite already said.
11. **The comp carried six of Hello Revenue's real card titles.**
    `test_the_fixture_project_is_synthetic.py` refused the tree, correctly:
    a project's titles stay in its own repository. FIXED: the six sample
    titles are Harbourmaster's now; every design decision in the comp is
    untouched (ruling 10).
12. **`uv run ruff check` does not pass, and never has.** 27 errors on this
    lane's base commit, 25 after it — none of them this lane's, and two of
    them cleared by it in passing. A check nobody can pass is a check nobody
    runs, and the suite does not run it, so nothing catches the drift. OUTSIDE
    THE CHANGE: filed as
    `docs/slice-suggestions/2026-09-04-ruff-does-not-pass-so-it-cannot-be-a-gate.md`,
    `Kind: defect`, with the before/after counts as its evidence and a
    two-step fix. Not fixed here — a formatting sweep across the repository is
    exactly the scope creep the effort gate warns about.

## What was checked

- **The suite**: 312 backend tests including the ratchets, `npx tsc --noEmit`
  clean, 55 vitest scenarios (18 of them the language table, one card per
  state, rendered from cards the real backend produced).
- **On a throwaway board over the synthetic project, served from this build**:
  headless Chromium at 1440×900 — the head's height and its three words'
  computed colours against `--attn`/`--wrong`/`--ink-2`; every card's
  `data-meaning` against its computed border colour, both ways (a live, asking
  or broken card must take it; anything else must not); the loop glyph's size
  and ring colour; the filter's card counts through a full click cycle; the
  triage lens's `current → target` and which classes have an accept-all.
  Screenshots at rest, filtered, with the archive unfurled, and on the triage
  lens.
- **The rule against its own source**: every `_state(...)` word in
  `board/assemble.py` listed and matched to a test or a fixture case.

## What the build learned the comp got wrong

- **The comp's collapsed door does not fit the board's own door labels.** The
  comp draws "Start"; the board says "Start · fable on alpha", and that is a
  fact worth keeping — on the open face, where there is room. The comp is
  right about the collapsed face and silent about where the placement went.
- **"open ▸" on a shipped card is decoration.** The comp puts it at the right
  of the loop line; at real column width it costs the loop its last four
  words, and it duplicates a gesture the whole card already offers.
- **The comp shows no card that carries suggestions or a watercooler line**,
  both of which the board has today (plans 06 and 07). They stay, quiet,
  between the essence and the state line — the comp's anatomy holds with them
  there, but it did not settle it.
- **The comp settles nothing about a lane that folded.** Its "a lane that
  died" is red; a lane that ended *well* is not drawn. The build had to make
  that call (finding 8) and the rule is now: what was lost, not that it ended.

## Not done, stated

- **The served board needs the main checkout's `frontend/dist` rebuilt and
  `needle-serve.service` restarted after the fold.** No migration, but every
  page surface changed and `CardSummary` lost five fields.
- **The open card below its top is its own design run**, as the owner ruled
  and the plan's item 4 records. What landed there is restyling only: the
  state sentence under the title, one filled door among outlined ones, the row
  labels quiet except the owner's own, the standing mark red only when
  doubted.
- **The owner's day of use is the signal**, and it is this card's WATCH row.
  Nothing in this record substitutes for it: every judgment above is the
  build's own, and the plan's gate says he judges by reading the board.
