# A lane that carries a migration cannot break the shared store before it folds

**Kind:** defect
**Fix:** now
**Found by:** the lane on card #51 (docs/plans/2026-09-05-17-asking-a-colleague-takes-a-minute-not-ten-and-nobody-waits-blind.md), in the review's seams pass

## Observation

`Store()` runs alembic `upgrade head` on every open, against whichever database `NEEDLE_DB` or the data directory names — the one shared store on this machine. On 2026-09-05 at about 13:20Z the card #51 lane ran `uv run needle sessions` from its worktree, whose tree carried an unfolded migration (0010). The shared store went to 0010. From that moment every `needle` command from the main checkout (`~/Work/needle`, at 0009) aborted before its verb ran with `Can't locate revision identified by '0010'`: the card #405 lane on Hello Revenue could not write its watercooler line or close, and said so across sessions. The lane downgraded the store by hand (both new tables were empty) and it went to 0010 again within minutes: `uv --project ~/Work/needle run needle watercooler …`, the very form the card's brief prescribes, run from inside the worktree, imports the worktree's own code — the working directory is first on the import path under `uv run` — so the main checkout's project and venv ran the lane's migrations. The main checkout's command is only the main checkout's when run from outside every worktree. A second downgrade and a private `NEEDLE_DB` copy held until the fold.

## Why it matters

The store is the board's memory for every project and every lane on the machine, and the migrator is whoever opens it. A worktree is exactly the checkout most likely to be ahead of the main one, and its commands are exactly the ones a lane runs all day (`needle card`, `row`, `watercooler`, `sessions`). One such command from any lane with a migration in flight breaks every other lane on the machine, silently until they try to write. The intent is written: the board's state never lives in a project's tree and is one store for all (`docs/INTENT.md`, "the shared memory of a team"); the fold is the one gate by which a lane's change reaches everyone (`CLAUDE.md`, "the trunk is `develop`").

## The fix

A class, not an instance: `Store()` upgrades the database only when the code opening it is the served board or the main checkout; a checkout whose migrations are ahead of the database's head refuses to open it with one sentence ("this checkout carries migration 0010 and the store is at 0009; fold first, or set NEEDLE_DB to a copy") instead of migrating it. The discriminator is the code's own location: `infrastructure.store` knows its file, and a file under `.claude/worktrees/` is a lane's copy whatever project or venv ran it — which is what defeated the `--project` form. A ratchet holds that no code path under `api/` migrates a store from a worktree. Rejected: asking lanes to remember `NEEDLE_DB` — a wish, not a control.
