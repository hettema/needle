# A gate the board cannot read is a quiet pill, not a count

**Found by:** the session writing Hello Revenue's card #411 on 2026-09-05 (conversation bbd1dd9c), reading `board/assemble.py` to decide whether Hello Revenue's effort-gate ratchet can retire into the board's door.
**Kind:** defect
**Fix:** now

## Observation

A plan whose `**Effort gate:**` line the parser cannot read (missing, or spelled `**Effort gate: xhigh**` with the colon inside the bold) becomes `StartState.NO_GATE`, and `board/assemble.py` renders that as `_state("no gate", Meaning.QUIET, …)`. Quiet is the meaning for a card that is simply waiting. So a card that can never Start looks like a card nobody has started.

## Evidence

Hello Revenue, 2026-09-04: five of eleven live plans spelled the gate in a form the parser skips, their cards showed the quiet pill, and nobody noticed until a session grepped the corpus (`tests/ratchets/test_plan_effort_gate.py`, its founding case). That ratchet exists because the board's own rendering did not surface the fault; it cannot retire while the rendering is unchanged. The machine's `docs/plans/README.md` already says the quiet part out loud: "nothing else does until someone presses Start and nothing happens".

## Why it matters

The board's promise is that the owner sees true state without reading code. A card that cannot Start is a fault in the corpus, the same class as "shipped with no review record", which the head already counts. A plan with no readable gate deserves the same: counted on the head and on the card's own face as a fault, not styled as patience. The three projects' ratchets that hold this locally are the belt this fixes the braces for; Hello Revenue's #411 retires its ratchet only once this has been seen on a real card.

## What would fix it

`no gate` renders with a meaning the head counts (the attention line: "N plans the board cannot read"), and the card's detail names the line it could not read, in the voice the unreadable-`Fix:` verdict already uses. Same for a `Hands out:` role the machine does not have, which `board/handouts.py` says it reports "in the same voice as a plan with no gate is".
