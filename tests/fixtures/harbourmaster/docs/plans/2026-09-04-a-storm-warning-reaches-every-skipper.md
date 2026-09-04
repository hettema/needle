# A storm warning reaches every skipper in the harbour

**Status:** PENDING — written 2026-09-04, the morning after the gale.
**Written:** 2026-09-04
**Effort gate:** high — one message to a list the office already holds; the judgment is what counts as a boat in the harbour tonight.
**Sequencing:** independent of every open card.

## Intent

Every boat in the harbour hears a gale warning the moment the office does. Last night the office phoned eleven skippers one by one and reached six; the five it did not reach found out from the wind.

## Terrain

The bookings for tonight name every boat and its skipper's phone; `office/messages.py` sends one message at a time.

## Done means

One message to every boat with a booking tonight, from the office in one click, and a line in the log saying who was reached.
