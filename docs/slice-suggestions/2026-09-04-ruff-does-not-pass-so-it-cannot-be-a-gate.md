# `ruff check` does not pass, so it cannot be a gate

**Found by:** card #27's lane (the colour language), 2026-09-04, in the review's
boundary pass. `uv run ruff check .` reported 27 errors on the lane's base
commit (`16a8023`) and 25 after it — this lane introduced none and incidentally
cleared two.
**Kind:** defect
**Fix:** now

## Observation

`pyproject.toml` configures ruff with a 100-column line limit and the project
depends on it, but the repository has never satisfied it. On `16a8023`:

- 24 × `E501` (line too long) across `board/reconcile.py`, `tests/board/`,
  `tests/api/test_doors.py`, `tests/api/test_reading.py`, `tools/scroll_check.py`
- 3 × `SIM102` (nested `if` that should be one)

The suite does not run ruff, so nothing catches this and nothing ever will: a
session that runs `uv run ruff check` before committing sees a wall of failures
it did not cause, learns the command is noise, and stops running it. That is
the exact shape of a convention eroding — and it means the one mechanical
check on how this code reads is not a check at all.

## Why it matters here

`CLAUDE.md` says a boundary that matters is a ratchet, not a convention. Line
length is a small boundary, but the failure is silent and compounding: every
session adds a little more, no one is told, and the eventual cleanup is large
enough that nobody does it. It also costs each lane real attention — this one
spent several minutes separating its own lint from the repository's before it
could tell whether it had made anything worse.

## The shape of the fix

1. `uv run ruff check .` and `uv run ruff format --check .` clean, in one
   commit that touches nothing but formatting. `--fix` and `format` do almost
   all of it; the `SIM102`s and a handful of long test lines are by hand.
2. A ratchet under `tests/ratchets/` that runs both and fails on either, so
   the suite is where a session finds out — the same place it finds out about
   every other boundary.

Rejected: raising the line limit to whatever the longest current line is. The
limit is not the point; a check that passes is.

## What it is not

Not urgent, and not this lane's to fix: it is entirely outside the change (the
rings rule, owner ruling 2026-09-04). It is cheap — one mechanical commit and
one small test — and it gets cheaper the sooner it is done.
