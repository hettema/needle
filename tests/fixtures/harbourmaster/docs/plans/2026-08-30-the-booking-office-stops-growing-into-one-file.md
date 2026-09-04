# The booking office stops growing into one file

**Status:** PENDING
**Written:** 2026-08-30
**Effort gate:** xhigh — a 4,100-line file is split along seams nobody has named yet.
**Sequencing:** independent of every open card.

## Intent

The file that applies every booking is a set of readable, single-concern modules — not a 4,100-line catch-all like the one that killed the old office.

## Terrain

`office/bookings.py`.

## Items

### 1. Name the seams
Read every booking path in the file and name the seam each one crosses. Done means: a list of seams, each with the paths that cross it. Hands out: search — every function in `office/bookings.py` and every caller of each, with path and line; verifies the file at each line named before a seam is drawn from it.

### 2. Split along them
Move each path into its module and leave the file under 400 lines. Done means: no module over 400 lines. Hands out: execution — the move of each path into its module, and the suite after each move; verifies the suite's own output by re-running the failing test it names.

## Done means

No module over 400 lines; every booking path has one test that names its seam.
