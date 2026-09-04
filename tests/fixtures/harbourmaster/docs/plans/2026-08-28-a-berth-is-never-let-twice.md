# A berth is never let twice

**Status:** PENDING
**Written:** 2026-08-28
**Effort gate:** xhigh — two bookings a minute apart both succeed today and the fix is a write path with a real invariant, not a check.
**Sequencing:** independent of every open card.

## Intent

Two boats never hold the same berth for the same night. A double-let is a boat turned away at the pontoon at dusk, and the office learns of it from the skipper.

## Terrain

`office/bookings.py::confirm` reads free berths, then writes; nothing holds the berth between.

## Done means

A unique constraint on berth and night; a test races two confirmations and one loses with a sentence.
