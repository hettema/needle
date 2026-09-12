# Work that starts without you never goes live without you

**Found by:** the owner, from the board's Idea door on 2026-09-12 (conversation 943300ef), asking whether he could turn Hello Revenue's auto-fix on and go to bed
**Kind:** defect
**Fix:** now — the intent is written (HOW-WE-WORK §1: a decision is his when acting would create external exposure beyond a bound he has already authorised, and the bound he authorised covers a close he set in motion by clicking Start), the fix stays inside its ring (the brief `board/brief.py` writes for a session the board starts, and what the board carries to his desk when the stable branch lags), and it removes the class — every project whose close reaches outside its own repository — not Hello Revenue's one path.

## Observation

The auto-fix switch is the owner's standing ruling about what enters *execution* without him. On Hello Revenue it also decides, today, what reaches *customers* without him, and nothing on the board says so.

A session the board starts writes a plan, the board opens Start itself, and the work that follows "runs as any lane: a worktree, the review rings, a fold on green, a close the board refuses without a review record" (`board/brief.py:436`). Closing as any lane is where it leaves the repository. Hello Revenue's close archives the plan *before* it folds, and its archive gate refuses while `origin/main` lags `origin/develop` on production paths. Hello Revenue's own execute skill gives the documented way past that refusal: "the order inverts for that one close: fold with `--main`, archive, fold again." `needle fold --main` pushes the same commit to `origin/main` (`runtime/git.py::fold`), and Railway deploys `main` on push.

So the first close of a night folds to the shared branch and leaves the stable branch behind; the second close on that board finds the gate refusing, promotes the stable branch to get past it, and carries both sessions' code — and anything else sitting on the shared branch — to customers, with nobody awake. Neither the switch nor the board's head mentions the stable branch anywhere.

## Evidence

- `board/brief.py:436`, the brief for a session the board starts: the work that follows runs as any lane and closes as any lane. Nothing in `api/dial.py` or `board/brief.py` contains "stable", "origin/main" or "promote" (read 2026-09-12).
- `runtime/git.py::fold` — with `promote_main`, pushes HEAD to `origin/main` after the trunk push; `STABLE = "main"` at `:20`. The flag is the calling session's choice; no check refuses it to a session the board started.
- Hello Revenue `scripts/archive_docs.py:171` `_refuse_unsynced_main` — the archive refuses, moving nothing, while production paths on `origin/develop` have not reached `origin/main`. It stands aside only while `docs/board/MAIN-HOLD.md` exists; that file does not exist on Hello Revenue today (read 2026-09-12).
- Hello Revenue `.claude/skills/hr-plan-execute/SKILL.md`, the record step: "**If it refuses because main lags** … the order inverts for that one close: fold with `--main`, archive, fold again." The fold step: "Railway deploys `main`, a develop-only fold deploys nothing", with three stop-and-ask exceptions the session judges for itself — a destructive change to stored data, a staged go-live, a standing hold.
- Hello Revenue `.github/workflows/gate.yml:3` — the independent check is advisory: "a red run alarms; Railway still deploys main on push." Nothing blocks a bad push.
- `needle dial` and `needle fixes <slug>` on the served board, read 2026-09-12: the switch, the number, what is live, and each session's fold. Neither names the stable branch, so the board cannot say what turning the switch on admits.
- `origin/main` and `origin/develop` on Hello Revenue were the same commit at the time of reading, so the first close of a night is the one that opens the gap.

## Why it matters

He ruled once that a verified defect may be planned and started without him. He never ruled that work he did not start may ship to the people who pay him. Composing the two turns one standing ruling into a second one he was never asked for, on the night he is least able to read what happened.

The three exceptions the close names are judgments an unattended session makes against a checklist at three in the morning, and the failure is silent and outward-facing — HOW-WE-WORK §5 puts that class behind a mechanism, not a convention. The board is the half that knows the work was nobody's click, and it is the half that says nothing.

The class is not Hello Revenue's. Every project on the board whose close reaches outside its own repository has it: a site that deploys from a branch, a public repository whose stable branch is what the world reads — Needle's own included.

## What would fix it

A session the board started never promotes the stable branch. Its brief says so, and the board carries the fact to his desk instead: when the work has landed on the shared branch and the stable branch lags, the card says the work is finished and his to release, with what is waiting behind it. Where a project's close would wedge on that — Hello Revenue's archive refusing while the stable branch lags — the brief says to leave the plan unarchived and say so on the card, which is the honest half-state, rather than reaching for the release to get past a refusal.

Two things this does not decide. Whether he later widens the ruling — "yes, ship at night, probe it, roll back if red" — stays his to grant, and the fix leaves that a setting he can reach rather than a rewrite. And Hello Revenue's standing hold is the same lever by hand today: writing that file before a night makes that night safe without any of the above, which is what he should do tonight if he wants the switch on before this lands.

The check: with the switch on and nobody awake, a session the board started that finishes its work leaves the stable branch exactly where it found it, and the card reads as his to release. A test board case where the stable branch lags the shared one proves the card says so and no release happens.
