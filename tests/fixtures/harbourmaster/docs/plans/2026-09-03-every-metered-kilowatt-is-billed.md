# Every metered kilowatt is billed

**Status:** PENDING — written 2026-09-03 from the owner's read of the meter alerts.
**Written:** 2026-09-03
**Effort gate:** medium — the fix is one parser and two call sites, fully specified; the failure mode is caught by the tests this plan adds and held by a ratchet.
**Sequencing:** independent of every open card.
**Card:** #253 (Up next)

## Intent

Power truth. Every kilowatt a boat draws on the pontoon lands on that boat's invoice the moment the meter reports it, so the season invoice stops understating every boat that plugged in. Today the office has dropped every meter reading since 5 July: the handler reads the reading as a number and the meters send a string.

## Terrain

`office/meters.py::on_reading` does `float(reading.value)` on a value the meter gateway sends as `"12.4 kWh"`. The read sits before the berth lookup, so every reading has raised since the gateway firmware changed on 2026-07-05.

## Done means

A reading in either shape reaches the invoice line for the right berth; the two missed months are re-read from the gateway's log; a ratchet refuses the bare float.
