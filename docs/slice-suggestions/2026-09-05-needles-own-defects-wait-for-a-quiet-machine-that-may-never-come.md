# Needle's own defects wait for a quiet machine that may never come

**Kind:** idea
**Fix:** his — whether a moment's risk to running work is worth more than Needle's rail draining; decided at the ten-lane look on card #34
**Found by:** the owner, at the close of card #34 (plan 11) on 2026-09-05, asking whether the rule "Needle's own defects run only when no lane is live on any project" means developing Needle is unstable for the other projects on the board.

## Observation

Plan 11 ruled that the dial takes a defect from Needle's own rail only while
no lane has hands on any project, "because a fold on the board restarts the
service under every running lane" (`docs/plans/done/2026-09-04-11-defects-fix-themselves.md`,
Rulings; `board/dial.py::is_quiet`, `api/dial.py::_take_next`). The rule
protects less than its sentence claims, and costs more than it says:

- A fold restarts nothing by itself. It pushes to `origin/develop` and levels
  the main checkout on disk; the running server keeps the code it loaded. The
  restart is a hand's act of about a second, every lane runs in its own
  scope and survives it, streams reconnect, hooks queue and drain, the loops
  resume from the store.
- The one real hazard is a migration: between the level and the restart, a
  `needle` command run from the main checkout migrates the shared store
  under the old server (`memory: needle-machine-facts-slice-11`). Loud in
  the journal, never silent.
- The cost: Hello Revenue's lanes run most of the day, so a quiet machine may
  be rare, and Needle's nine marked defects (#24, #28, #29, #31, #32, #33,
  #35, #37, #40) may wait indefinitely while the dial is on. `needle fixes
  all` says so on every one: "the board's own rail waits until no lane is
  live anywhere".

## What would change it

Two shapes, one line each in the eligibility check, and the choice is the
owner's because it trades a moment's risk to running work against the rail
draining:

1. Relax the rule to "no lane mid-Start or mid-fold on any project" — the two
   moments a restart could actually disturb — and let a Needle fix lane run
   beside working lanes.
2. Drop the rule and let the fold-time order (fold, rebuild, restart, then
   anything else) carry the protection, as it does for every Needle lane a
   person starts today.

Recommended: keep the rule for the first ten fix lanes, which are the loop's
evidence and the case with the fewest eyes on it, and decide at the ten-lane
look on card #34 with one fact in hand — whether Needle's rail moved at all.
If it did not, the rule starved it, and shape 1 is the smaller step.
