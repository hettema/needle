# A gate code arrives before the boat does

**Status:** PENDING — written 2026-09-02.
**Written:** 2026-09-02
**Effort gate:** medium — the code already exists at booking time; the plan moves when it is sent.
**Sequencing:** independent of every open card.
**Card:** #241

## Intent

A skipper who booked from sea finds the gate code waiting on the phone when the boat is tied up. Today the code goes out when the office opens the next morning, so a boat arriving at 21:00 is locked out of the showers until 08:30.

## Terrain

`office/arrivals.py` sends the welcome mail from the morning batch.

## Done means

The code is sent the moment a booking is confirmed; one arrival is tried from a phone.
