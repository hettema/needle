# A defect that fixes itself waits for room on its machine instead of landing on your desk

**Kind:** defect
**Fix:** now — the intent is written (card #148's plan: a card whose machine cannot open now is left out of that beat's choice and read when the machine has room, never handed to the owner for it; `docs/INTENT.md`: one move is his, and a machine's momentary state is no decision of his), the fix stays inside `api/dial.py::_take_next` — the verified defects are asked the same question the unread cards are asked (`_openable`) before `_plan` is called — and it removes the class, every planning start refused for room on every board, not the one card it is seen on
**Found by:** the lane on card #148 (docs/plans/done/2026-09-14-a-card-whose-machine-is-full-never-stops-the-board-reading-the-rest.md), in the independent review

## The intent it breaks

A defect the board has verified and would fix by itself waits for room on its machine and starts when there is some; it never becomes yours because the machine was full at the minute the board looked. Today, when auto-fix takes a verified defect of a project whose own machine is full, the planning start is refused, the fix is recorded as ended before it began with the refusal on the card, and the board never tries that card again: it is yours from then on, for a cause that clears by itself within the hour, and you have to press Start to give it back.

## Evidence

- `api/dial.py::_plan`: when the planning launch is not alive it stages the fix lane `ENDED` with `The dial could not start a planning session: <reason>` and writes the same on the card, then returns. `api/dial.py::_ran` then keeps every card the dial took once out of the beat ("the cards the dial took once already, which are the owner's from here"), so the refusal is final.
- The reason can be the room alone: `runtime/service.py::start_windowless` places through `domain/machine.py::choose_machine`, which refuses a project that is a machine's own record while that machine is full — the same refusal card #148 met on the reading side, where the beat now leaves such a card out and comes back to it (`api/dial.py::_openable`). The verified candidates in `_take_next` are not asked that question before `_plan`.
- Found by the independent review of card #148 (call 135, session 5ca8b465, 2026-09-14), reading `api/dial.py` lines 740-752 against the plan's item 1; traced, not run.

**Searched before filing** (2026-09-14): `docs/slice-suggestions/*.md` for "planning session", "could not start", "machine is full", "room". #148 (`docs/slice-suggestions/done/2026-09-14-a-card-whose-machine-is-full-never-stops-the-board-reading-the-rest.md`) is the reading side of the same rule and is shipped; #122 (`docs/slice-suggestions/2026-09-10-work-placed-on-a-machine-with-room-is-not-held-to-the-laptops-floor.md`) is about which floor a machine's room is measured against, not about what the board does with a refusal. Neither covers a planning start refused for room.

## What done looks like

The beat asks a verified defect's project the same question it asks an unread card's — can this project's machine open a session now, over the rooms read this pass — and a defect whose answer is no waits in its column for the next beat, with one note on its face per spell, exactly as a reading does. A planning start refused for any other cause is still the owner's, as today. Loop: no fix lane on any board is recorded as ended with `it is full` in its reason over a week where the machine had room within the hour.
