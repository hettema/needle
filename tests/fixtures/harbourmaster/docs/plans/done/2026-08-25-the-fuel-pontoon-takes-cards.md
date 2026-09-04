# The fuel pontoon takes cards

**Status:** SHIPPED — 2026-09-01; the first card payment is the signal.
**Written:** 2026-08-25
**Effort gate:** high — a terminal and one new invoice line.
**Sequencing:** independent of every open card.

## Intent

A skipper pays for fuel at the pump with a card and the litres land on the same invoice as the berth. Today it is cash and a paper slip.

## Terrain

The pump's terminal, `office/invoices.py`.

## Done means

A card payment at the pump is a line on the boat's invoice.
