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
summarised by hand. The ratchet checks that a named holder exists, not that it
holds every clause the section states — that is this file's judgment, and the
rule for it is that a stance covers the whole section or it is the weaker
stance: a mechanism that holds one clause is named for that clause, never
stretched over the rest (Sol's review finding, 2026-09-05).*

*Kept beside the doctrine rather than inside it (owner ruling 2026-09-05, row D
of the two-texts table, on the walk's finding): stance lines change every time a
ratchet lands or a debt is paid, and the constitution's commit hook demands a
card for every edit to it — so the register lives where it can change without
that ceremony, and the ratchet keeps it honest.*

## 1. Two kinds of decisions, never conflated
*Convention because:* a decision taken as the colleague's that was the person's is loud — an outcome they did not ask for, seen at the next report; the one mechanised clause is entry into execution, `tests/ratchets/test_start_is_the_owners_click.py`.

## 2. Intent over orders, and the test for a rule
*Convention because:* a rule written as a method is read at the effort gate, where the person reads the plan before Start and says so.

## 3. A session's economics are inverted
*Traced by:* the review's passes, which read for the shortcut and the second way; the deferral markers alone are refused by `tests/ratchets/test_nothing_ships_half_done.py`.

## 4. Only what is written survives
*Traced by:* the commit log, whose bodies the review's first pass quotes, and the plan's rulings, which the close reads.

## 5. Convention is the weakest defence
*Traced by:* this register's print and each project's own ratchets, read at the review's boundaries pass; the one clause held is that every rule here names its holder, by `tests/ratchets/test_every_rule_says_what_holds_it.py`.

## 6. Completeness is a claim only the session can check
*Traced by:* the plan's `Met:` and `Deviated:` lines and the review record, read by the person at the close; the close itself is one act or refused, `api/doors.py::close`.

## 7. We live in iterations, and a loop is a thesis
*Undefended until:* docs/plans/2026-09-05-16-every-loop-a-plan-names-is-watched-until-it-closes.md by 2026-09-19 — every loop a plan names is watched by the board until it closes, and a loop that never closed is shown as a belief.

## 8. Verify, don't assume — and the answer is usually there
*Traced by:* the review record's passes, each re-reading the last pass's claims, and the owner reading the record at the close.

## 9. Raise the standard, not just the output
*Traced by:* the suggestions folder, where a learning about the way we work arrives marked `his`, read on the board's rail.

## 10. The corpus is the way in
*Traced by:* the board's own read of the corpus, which shows a plan or suggestion it cannot parse on its card; two clauses are held — a project needs a plans folder (`api/cli.py::add`) and a suggestion names its kind and fix (`tests/ratchets/test_every_suggestion_names_its_kind_and_fix.py`).

## 11. The board is the team's memory, and one move is the person's
*Traced by:* the card's history, which names the actor and the reason of every move, read by the person; the page shows only held state, `tests/ratchets/test_the_page_shows_only_held_state.py`.

## 12. Execution takes a lane
*Held by:* api/board_cli.py::fold — the trunk moves only by a fast-forward push from a lane's own worktree, so nothing merges by hand and nothing lands red; a lane's isolation and its overlap with another are the board's read of the machine, shown on both cards.

## 13. Nothing is done without a review, and a review is a loop
*Traced by:* the review record itself, pass by pass with what each found, read by the person at the close; that one exists is held by `api/doors.py::close`.

## 14. The close ritual
*Held by:* api/doors.py::close — the close is one act, delivered and watch and review, or it is refused; a folded card nobody closed is moved to the person's attention by the board's lane read, never to shipped.

## The owner's steering
*Convention because:* a wrong form of address is the loudest failure there is — he sees it in the first line and says so.
