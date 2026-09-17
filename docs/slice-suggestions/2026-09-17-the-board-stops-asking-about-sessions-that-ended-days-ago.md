# The board stops asking about sessions that ended days ago

**Kind:** defect
**Fix:** now — the written bound is in the board's own loop (`api/loops.py`): `_endings_to_name` re-asks only "every recorded ending not settled while evidence may still arrive", and `RESCUE_HORIZON_SECONDS = 3600` is the written window in which evidence may arrive; the guard `last.pid is None and death is not None and not young` lets an ended session through on its stale pid whatever the death's age (read from the source, not run), so the board asks the rented machine about deaths from days ago, forty-one times a minute, for two days. Stopping the repeat is execution inside the written hour, removes a class (every ending older than the window) and not an instance, and stays inside the loop it corrects.
**Found by:** the split of #157 (2026-09-17)
**Split from:** docs/slice-suggestions/2026-09-17-the-board-costs-nothing-while-nothing-is-happening.md

## The intent it breaks

The board asks about a session's death only while evidence may still arrive, and today it asks the rented machine over ssh forty times a minute, day and night, for the cause of deaths from two days ago that it can never settle. While this stands the owner pays most of the board's measured work — a warm laptop and a shorter battery — for questions whose answer the written record already declines to wait for, and once the board moves to the rented machine he pays a rented core for the same questions.

## Evidence

Read on the laptop on 2026-09-17, between 12:57 and 13:10 CEST, with no session working on the laptop (`needle lanes` names none).

- In one 60-second sample the board had 46 distinct children: 41 `ssh rented -- needle cause <id> …` calls, two `git fetch`, two notification prompts. The cause calls name sessions that ended on 15 and 16 September (cards #554, #547, #591, #575) and each answers `"settled": false` ("the cause is not established"), so the same question is asked of the rented machine again on the next pass, and has been for two days.
- `api/loops.py`, `RESCUE_HORIZON_SECONDS = 3600.0`: the written window in which evidence about an ending may still arrive. `_endings_to_name` says it re-asks only "every recorded ending not settled while evidence may still arrive". The guard `last.pid is None and death is not None and not young` does not read the death's age, so an ended session with a stale pid is asked about on every pass for as long as its ending stays unsettled — read from the source on 2026-09-17, not run.
- The board's overall cost is in the document this was split from: 27 % to 66 % of one core in 60-second samples, 23 % of a core on average since the service started; most of the measured children in those samples are the cause calls above.

## Neighbours on this ground

- `docs/slice-suggestions/2026-09-17-the-board-costs-nothing-while-nothing-is-happening.md` — the half the record does not settle: whether the board's thirty-second pass itself should stay, and whether the cost still matters once the board is rented. This suggestion does not touch that pass; it only stops the repeated questions the written hour already excludes.
- Card #83, `docs/plans/2026-09-07-the-work-runs-where-the-horsepower-is-and-the-board-feels-like-it-is-on-your-laptop.md` — "The loop reads every machine on every pass" is that plan's design; asking the rented machine about a death is one of those reads, and its item 3 moves the board to the rented machine.
