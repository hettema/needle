# How we hold it

*Every rule in `docs/HOW-WE-WORK.md` says here what holds it, in three words and
no fourth: **held** by a check that refuses, **traced** by evidence someone reads,
or a **convention** because its failure is loud. A rule held by nothing says so
with the card that will change that and the date by which it must — debt is not
a way of being held, it is the honest word for "not yet", and it is counted
apart. `tests/ratchets/test_every_rule_says_what_holds_it.py` reads this file
against HOW-WE-WORK's section titles both ways, so a section cannot appear in one
and not the other, a held line cannot name a check that does not exist, and a
debt line cannot name a card the corpus does not have or a date that has passed.
What that ratchet prints when it passes is the only map; this file is never
summarised by hand.*

*Kept beside the doctrine rather than inside it (owner ruling 2026-09-05, row D
of the two-texts table, on the walk's finding): stance lines change every time a
ratchet lands or a debt is paid, and the constitution's commit hook demands a
card for every edit to it — so the register lives where it can change without
that ceremony, and the ratchet keeps it honest.*

## 1. Two kinds of decisions, never conflated
*Held by:* tests/ratchets/test_start_is_the_owners_click.py — nothing enters execution but by the person's click or their standing ruling on the dial.

## 2. Intent over orders, and the test for a rule
*Convention because:* a rule written as a method is read at the effort gate, where the person reads the plan before Start and says so.

## 3. A session's economics are inverted
*Held by:* tests/ratchets/test_nothing_ships_half_done.py — a TODO, a "later", a deferral marker fails the suite.

## 4. Only what is written survives
*Traced by:* the commit log, whose bodies the review's first pass quotes, and the plan's rulings, which the close reads.

## 5. Convention is the weakest defence
*Held by:* tests/ratchets/test_every_rule_says_what_holds_it.py — this register: a rule with no stance fails the suite.

## 6. Completeness is a claim only the session can check
*Held by:* api/doors.py::close — a card closes in one act or not at all: what was delivered, the signal that will prove it, the review record.

## 7. We live in iterations, and a loop is a thesis
*Undefended until:* docs/plans/2026-09-05-16-every-loop-a-plan-names-is-watched-until-it-closes.md by 2026-09-19 — every loop a plan names is watched by the board until it closes, and a loop that never closed is shown as a belief.

## 8. Verify, don't assume — and the answer is usually there
*Traced by:* the review record's passes, each re-reading the last pass's claims, and the owner reading the record at the close.

## 9. Raise the standard, not just the output
*Traced by:* the suggestions folder, where a learning about the way we work arrives marked `his`, read on the board's rail.

## 10. The corpus is the way in
*Held by:* api/cli.py::add — a path without a plans folder is not a project the board will take.

## 11. The board is the team's memory, and one move is the person's
*Held by:* tests/ratchets/test_the_page_shows_only_held_state.py — the page shows only what the store holds, and a machine fact outlives its evidence on the page before anything moves.

## 12. Execution takes a lane
*Held by:* api/board_cli.py::fold — the fold is a fast-forward push from the lane's own worktree and nothing else lands on the trunk.

## 13. Nothing is done without a review, and a review is a loop
*Held by:* api/doors.py::close — a code lane is refused its close without a review record that exists.

## 14. The close ritual
*Held by:* api/doors.py::close — the one act, refused without its three parts; a folded card nobody wrote up goes to the person's attention, never to shipped.

## The owner's steering
*Convention because:* a wrong form of address is the loudest failure there is — he sees it in the first line and says so.
