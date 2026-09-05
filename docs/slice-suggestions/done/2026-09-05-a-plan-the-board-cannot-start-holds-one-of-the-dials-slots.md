# A plan the board cannot start holds one of the dial's slots

**Carried by:** docs/plans/done/2026-09-05-as-many-lanes-as-the-machine-can-hold-run-side-by-side-and-the-fold-settles-what-they-share.md (item 3, shape 1: a held plan does not count, and the head says *held*)
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation a2d30083), watching the dial's first night on Hello Revenue: at 02:57 the dial reported four live fix lanes and not one had hands on a tree.
**Kind:** defect
**Fix:** his — the remedy trades planning spend (a Fable session per plan written while its Start is closed) against the rail draining on a night one long lane runs; both shapes below are a few lines in `board/dial.py::LIVE_STAGES` or `api/dial.py::_take_next`, and which one is the owner's call.

## Observation

Plan 11 says a fix lane counts against the number "from its Start to its fold". The build counted from the planning session instead (`board/dial.py::LIVE_STAGES` = planning, planned, started), with its reason on the constant: otherwise a dial at one opens a planning session per defect on the rail before the first lane starts. That reason holds for *planning*. It does not hold for *planned*: a planned card is no process, and when its Start is closed it consumes nothing but the dial's number.

Tonight, 01:20 to 02:57: #361, #379 and #383 planned by 01:41 and could not start, each colliding with the owner's own #350 lane (test files, the telemetry vocabulary, the prompt QA manifest); #384 planned at 02:41 and could not start because the board had parked it (its own defect, filed beside this one). Four of four slots held by cards with closed doors; #385, #386, #391 and eleven more eligible defects waiting "if the number allows"; one fold all night (#377, whose slot #384 took). `needle dial` said *4 live now* the whole time.

## Evidence

- `needle fixes all` at 02:57: four *planned; not folded* lines and the rail's *eligible: the next beat takes it if the number allows* lines beneath them.
- Each planned card's Start door on the served board: "Lane collision — #350's lane is editing … right now" for three, "this card is in Decision moment" for the fourth.
- The dial's history rows on each card: "Start waits: …", once, at the moment the plan landed.

## What would change it

1. **A held plan does not count.** A fix lane at the planned stage whose Start door is closed is not live against the number; the beat takes the next eligible defect. The rail drains around a long lane, at the price of a planning session for every defect that gets planned while its Start is closed — bounded by the planning stage still counting, so at most the number's worth are written at once.
2. **The dial skips a candidate whose plan would collide.** Before planning, read the suggestion's named terrain against every live lane's footprint the way the Start door will, and leave a colliding defect on the rail with the reason on its face. Cheaper, but a suggestion's terrain is prose and the plan's footprint is what the door judges; the skip would be a guess.

Recommended: shape 1, with the number of *held* plans shown on the head beside *live*, so a night like this one reads as "4 held, 0 running" instead of "4 live". The ten-lane reading on card #34 carries a fourteen-day guard for a path that is not running; tonight the path ran one lane in ninety minutes and the guard would not have fired.
