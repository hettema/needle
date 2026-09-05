# A Sequencing line that names cards closes Start until they ship

**Found by:** the owner, from Hello Revenue's Idea door on 2026-09-05 (conversation bbd1dd9c), writing a plan that depends on omarchy #17 and Needle #20: "lets make it check if the dependencies in machine and needle are actually executed before it executes (I am not going to remember)".
**Kind:** idea
**Fix:** his

## Observation

A plan's `**Sequencing:**` line is parsed and shown and nothing more. `board/parse.py` stores it on the document (`domain/document.py::sequencing`); no `StartState` reads it, so a card whose plan says "after omarchy #17" opens Start the day it is written, and the lane that launches finds the skill it was going to cite does not exist yet. Hello Revenue's card #411 carries the check as its own first item — read both cards through `needle card`, stop with a WAITS row if either is not Executed or Done — which is a convention the lane has to remember, exactly what the owner said he will not.

## What would hold it

A Sequencing line that names cards in the board's own words — `omarchy #17`, `Needle #20`, `#403` for the same project — is read the way `Hands out:` and `Fix:` are, and Start is closed while any named card is not in Executed or Done, as a sibling of `StartState.COLLIDES`: the pill says "waits on omarchy #17", the open face says which cards and where they stand, and the door opens by itself the day the last one ships. Prose after the card names stays prose. A Sequencing line that names no card changes nothing.

## Why it matters

The board holds "what enters execution is the owner's gesture"; a Start that is open before the work it depends on exists makes that gesture a trap. Cross-project dependencies are now the normal case — the shared skill (omarchy #17), the close reading stances (Needle #20) and Hello Revenue's #411 form one chain across three boards — and the only reader of the order today is a human's memory.

## Context

The first consumer is Hello Revenue's `docs/plans/2026-09-05-a-plan-grammar-change-reaches-hello-revenue-without-a-card.md`, whose item 1 is the lane-side check this would retire.
