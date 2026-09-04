# The tide table is the harbour's own

**Status:** PENDING
**Written:** 2026-09-04
**Effort gate:** medium — one data source replaces another; the shape is the same.
**Sequencing:** independent of every open card.

## Intent

The tide the office plans by is the one measured at the harbour mouth, not the one published for the estuary twenty miles up. A boat drawing two metres is told when it can actually come in.

## Terrain

`office/tides.py` reads the estuary feed; the harbour gauge publishes a CSV hourly.

## Done means

Arrival windows are computed from the gauge; the estuary feed is gone.
