# A Codex colleague Needle calls has the doctrine, or the call says it did not

**Kind:** defect
**Fix:** now — `docs/INTENT.md` lesson 5 says a door either opens and proves it or says why not, and the machine's card 19 (`omarchy-machine/docs/plans/done/2026-09-05-18-a-colleague-of-any-make-reads-the-same-house-rules-before-it-gets-hands.md`) says a colleague of any make reads the same record before it gets hands; a Codex worker Needle launches can start with no instructions at all and exit 0, so the fix is in `runtime/codex.py`'s launch path — read the worker's stderr for Codex's own `Failed to read global AGENTS.md instructions` warning, or its rollout's first messages for the block, and refuse or mark the call — which holds every worker Needle ever launches rather than one call
**Found by:** the lane on card #60 (docs/plans/done/2026-09-05-every-session-of-any-make-follows-the-doctrine-at-least-as-well-as-hello-revenues-did.md), in the review's boundaries pass, from the owner's question on 2026-09-07 whether Codex has the doctrine loaded

## Observation

Read live on 2026-09-07. `~/.codex/AGENTS.md` resolves to Needle's
`docs/HOW-WE-WORK.md`, byte for byte, and Codex 0.153.4 loads it inside a
repository and outside one, with and without `--skip-git-repo-check`. But
two `codex exec` sessions launched by Claude sessions after the link existed
— one from `/home/dennis` on 2026-09-05 20:43, one from a session scratchpad
under `/tmp` on 2026-09-06 00:09, both without a `git` entry in their
record — started with no instructions block in any message. And when the
link cannot be followed (a scratch home whose `AGENTS.md` points into an
unreadable directory), Codex prints
`warning: Failed to read global AGENTS.md instructions … Permission denied`
to stderr and runs anyway, answering "NO INSTRUCTIONS", exit 0. The chain
from Codex's file to the one text crosses three repositories, so a caller
whose filesystem view excludes any of them gets a colleague with no doctrine,
and nothing but stderr says so. The exact sandbox of the two sessions is
inferred, not read; the class is reproduced.

## Why it matters

Needle calls Codex workers (`runtime/codex.py`, card 57) and Claude sessions
call `codex exec` from scratchpads. Either way the answer comes back in the
worker's voice with no sign that it never read the doctrine — which is the
silent failure the one text's head exists to end.

## Fix

In `runtime/codex.py`, the launch reads the worker's stderr for the warning
and its rollout for the block, and a call whose worker has no instructions is
refused or its answer marked, in the call's record. The machine's own reader
(`machine codex-entrances`) is the machine's half and is filed there.
