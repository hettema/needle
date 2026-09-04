# The skipper sees the price before the berth

**Status:** PENDING
**Written:** 2026-09-02
**Effort gate:** high — the price rule has three inputs and the form shows none of them until the end.
**Sequencing:** independent of every open card.

## Intent

A skipper knows what a night costs before choosing where to lie. Today the price appears on the confirmation, after the berth is chosen.

## Terrain

`office/pricing.py` and the booking form's last step.

## Done means

The map shows the night's price on every free berth; the confirmation repeats it.
