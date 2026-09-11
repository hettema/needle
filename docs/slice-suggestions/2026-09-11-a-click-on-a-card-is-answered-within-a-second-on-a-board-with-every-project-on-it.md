# A click on a card is answered within a second on a board with every project on it

**Kind:** defect
**Fix:** now — `docs/plans/done/2026-09-10-the-board-asks-another-machine-one-question-a-pass-and-answers-a-click-in-a-second.md` accepts only a click answered within a second while the board reads another machine, and its Loop names the step when a pass holds the lock over a second: find the wait the pass's own numbers point at inside the apply, which removes that wait for every click, not one
**Found by:** the lane on card #123 (docs/plans/done/2026-09-10-the-board-asks-another-machine-one-question-a-pass-and-answers-a-click-in-a-second.md), in the plan's loop, read on the served board right after the fold

## The intent it breaks

A click on any card is answered within a second while the board reads the
rented machine, which is what card #123 promised; on the laptop's board with
every project on it, the pass that applies what the machines answered now
holds the board for two and a half seconds, so a click that lands during it
waits that long — far better than the minutes before, but not the second the
owner was promised.

## Evidence

- `needle beats --count 12` on the served board, 2026-09-11 17:39–17:41Z,
  minutes after the board restarted on card #123's fold (store at 0021):
  the first six passes held the lock 0.77, 0.68, 0.79, 0.74, 0.86 and 0.69 s;
  the next four held it 2.62, 2.66, 2.31 and 2.51 s, one of them an apply of
  a late answer with no collection of its own. The rented machine's
  collection was 28.0 and 30.2 s at first, then 1.4 and 1.2 s.
- On the test floor, thirty lanes on two machines, a pass held the lock
  under a second (`tests/runtime/test_one_question_a_pass.py::test_the_lock_is_held_under_a_second_a_pass_with_thirty_lanes_on_two_machines`),
  and a probe there found the apply's time in the store's own writes
  (a record per lane, a sighting per session), with no process started
  under the lock. What holds the lock for two and a half seconds on the
  laptop's board is not named yet: the apply was not profiled live.
- No click landed during those passes (`no click in the last day`), so the
  wait a click meets is inferred from the lock's hold, not measured.
