# A screen nobody opens is removed

**Status:** PENDING — from the winter review.
**Written:** 2026-08-26
**Effort gate:** high — four screens have had no visit since June; removing them is deletion, not design.
**Sequencing:** independent of every open card.

## Intent

Every future session reading the office's code sees only screens that are actually opened — nothing dead to extend, fix or learn from.

## Terrain

The visit log names the four; `office/screens/` holds them.

## Done means

The four screens are gone, their routes answer 404, and a test counts the screens against the log.
