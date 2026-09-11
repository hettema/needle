# Work on a card can call a fresh colleague of either kind, not only Codex

**Kind:** defect
**Fix:** now — HOW-WE-WORK §12 is the written intent ("a session that needs a colleague's judgment … calls a colleague of either make warm through Needle's `call`"), and card #58's plan makes the same-make challenge for a Claude hand and the different-make challenge for a Codex hand a team the board assigns; the fix stays inside the call verb (`api/runtime_cli.py::call`, `_call_fresh`) and removes the class: `--fresh` starts a new thread of whichever make is named, so no composition depends on a background session happening to be alive
**Found by:** the lane on card #58 (docs/plans/2026-09-05-the-team-learns-which-mix-of-colleagues-earns-its-place.md), in the independent review

## The intent it breaks

Every card is meant to run with the team the evidence chose, without anyone preparing a colleague by hand. Today a lane driven by Claude that is assigned a same-make challenge, or a lane driven by Codex assigned a different-make one, has to find a Claude colleague already running in the background on some slot, because `needle call --fresh` starts a new thread of Codex's make only; when none is running, the call refuses and the challenge the board assigned does not happen. The owner loses the trial the router counted on, and the reading records an unread round instead of the evidence it was after.

## Evidence

- `api/runtime_cli.py::call` (2026-09-11): `--fresh` is refused unless `who` is `codex` ("--fresh starts a new thread of the other make; call codex --fresh"); a Claude colleague is reached only through `runtime.colleague(ref)`, which answers the most recent background session on a slot or a session by id, and None when none is in any registry — the call then prints "no session … is in any registry on this machine" and exits 1.
- `board/team.py::executable` (card #58) treats both challenges as executable for both hands, because the runtime has a launcher for each make; the independent review of #58 (Codex call 106) showed the gap: "with no local Claude colleague, the router still assigns a Codex hand a different-make challenge; `Runtime.colleague` returns None and the prescribed call refuses". The lane's brief now says what to do when the call refuses (write `**Challenged:** no round — <why>`), which keeps the reading honest and does not make the round happen.

## What would fix it

`needle call <make> --fresh <note>` starts a fresh thread of either make: for Claude, a background session on the slot the rule names (the launch `Runtime.ask` already makes for the focus loop of card #87 is the shape), held to the same `Answer` form, recorded as a call row like any other. A test on the floor calls a fresh Claude colleague from a lane and waits on its answer.
