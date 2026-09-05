# A storm warning reaches every skipper in the harbour

**Status:** PENDING — written 2026-09-04, the morning after the gale.
**Written:** 2026-09-04
**Effort gate:** high — one message to a list the office already holds; the judgment is what counts as a boat in the harbour tonight.
**Sequencing:** independent of every open card.

## Intent

Every boat in the harbour hears a gale warning the moment the office does. Last night the office phoned eleven skippers one by one and reached six; the five it did not reach found out from the wind.

## Terrain

The bookings for tonight name every boat and its skipper's phone; `office/messages.py` sends one message at a time.

## The work

1. **Tonight's boats are one list.** The bookings for tonight, read into one list of boats with each skipper's phone. Done means: the list at `office/tonight.py` names every boat with a booking tonight and its skipper's phone; eleven on the fixture.
2. **One click sends the warning.** A Warn button in the office sends one message to every boat on the list. Done means: `office/messages.py` sends to every boat on the list from one click, and a test proves every boat was reached.
3. **The log says who was reached.** Done means: a line per skipper, reached or not, in the office log.
4. **The gale is rehearsed.** Done means: a test sends to eleven boats and finds five unreached in the log.

## Done means

One message to every boat with a booking tonight, from the office in one click, and a line in the log saying who was reached.
