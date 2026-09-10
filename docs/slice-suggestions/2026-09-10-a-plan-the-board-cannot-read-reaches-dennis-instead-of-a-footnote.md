# A plan the board cannot read reaches Dennis instead of a footnote

**Kind:** defect
**Fix:** now — the intent it breaks is written (HOW-WE-WORK §11: every move that is not his is a machine fact with named evidence, or the board lies while he is away; and §10's own failure of 2026-09-04, five live plans the board could not read sat unable to start, unnoticed), the fix stays inside the trunk read that already knows the checkout is on the wrong branch (`runtime/git.py`, `TRUNK` and the "not touched" note), and it removes the class — a project whose plans the board reads from a checkout it refuses to level — by either levelling a clean checkout onto the trunk (nothing is lost on a clean clone) or putting the fact where he looks, on the rail or the card face, never only in a `trunk.note` field
**Found by:** a main-thread session on 2026-09-10, after committing a plan to the machine repo and finding no card

## The intent it breaks

A plan committed to a project's plans folder is a card within seconds, and the board's columns are his rulings or machine facts he can see. On 2026-09-10 a plan committed and pushed at 16:06 was no card at all, and nothing on the board's face said why: the board on the rented machine read the machine repo's plans from a clone that sat on `main`, nine commits behind, and its trunk read had been saying so since at least 16:04 in a field no page shows as a problem. What he loses while it does: a card he cannot start because he cannot see it, and a board that reports "7 live plans" with the number from a branch nobody writes to.

## The evidence

Checked 2026-09-10 16:08–16:11 CEST. `GET /api/projects/omarchy/board` gave `trunk = {"level": false, "behind": 9, "note": "the checkout is on main, not develop; not touched"}` and no card whose title held "AirPods"; `ssh rented 'cd ~/Work/omarchy-machine; git branch -vv'` gave `* main 0bb17ec [origin/main]`, clean but for one untracked directory, while `hellorevenue`, `hr3` and `needle` beside it were on `develop` and level. `git checkout develop && git pull --ff-only` on that clone put it at `057c677`, and within twenty seconds the board read the corpus (`live_plans` 6 → 7) and showed card #58 with its gate. The board's runtime refuses to touch a non-trunk checkout on purpose (`runtime/git.py:322`), which is right for a checkout someone is using and wrong as the only outcome for the board's own reading clone; the local `needle-serve` had stopped at 15:42 for an unrelated reason, so the rented board was the one reading.
