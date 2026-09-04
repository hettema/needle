# The waiting list offers every berth that fits

**Status:** PENDING — split 2026-09-01 out of the shipped berth-first plan.
**Written:** 2026-09-01
**Effort gate:** high — the matching rule is specified; the one judgment is what counts as a fit for a catamaran.
**Sequencing:** after #139, the four berth-first rulings.

## Intent

A boat on the waiting list is offered every berth it fits, not only the one it asked for. Today the list matches on the berth number the skipper typed, so a 9-metre boat waiting for C14 is never told that C11 came free on Tuesday, and C11 stays empty while the skipper anchors outside.

## Terrain

`office/waiting_list.py` holds the match; berth dimensions live in `berths.yaml` and are already read by the booking form.

## Done means

A boat on the list is offered the first berth that fits its length, beam and draught; the offer names why it fits; a test walks a 9-metre boat through three vacancies.
