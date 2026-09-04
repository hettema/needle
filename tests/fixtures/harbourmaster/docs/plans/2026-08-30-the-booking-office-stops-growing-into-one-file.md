# The booking office stops growing into one file

**Status:** PENDING
**Written:** 2026-08-30
**Effort gate:** xhigh — a 4,100-line file is split along seams nobody has named yet.
**Sequencing:** independent of every open card.

## Intent

The file that applies every booking is a set of readable, single-concern modules — not a 4,100-line catch-all like the one that killed the old office.

## Terrain

`office/bookings.py`.

## Done means

No module over 400 lines; every booking path has one test that names its seam.
