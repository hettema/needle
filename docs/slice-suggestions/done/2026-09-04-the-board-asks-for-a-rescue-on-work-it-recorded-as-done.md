# The board asks for a rescue on work it recorded as done

**Carried by:** docs/plans/2026-09-05-a-lane-the-machine-ended-comes-back-by-itself-and-the-boards-word-on-how-it-ended-is-true.md — folded from the board's Idea door on 2026-09-05 (conversation 6b683c8b), which read it beside #31, #32 and #68 as four findings about one loop
**Kind:** defect
**Fix:** now
**Found by:** the owner, from the board's Idea door on 2026-09-04 (conversation
56f7b05f), in the card history read while tracing why card #196's lane band was
reporting a death.

## Observation

Card #196's own history has it finished at `17:26–17:27Z`: `folded 17:26:23Z`,
`synced 17:26:26Z`, `archived 17:26:26Z`, then the session's own
`folded 17:27:17Z` and `synced 17:27:20Z`. The board had already moved it to
Executed and read its close as landed.

From `17:29:57Z` to `18:23:00Z` — 54 minutes after that — the board wrote
**eighteen** rescue notes onto the card. Seventeen are the same sentence:

> Parked: hit a limit again within the hour (You've reached your Fable limit…);
> one automatic retry per run-out, so this one is yours (Resume).

The eighteenth says the move failed on the same limit. The owner was asked,
seventeen times, to put his hand on a card the board itself had recorded as
done. He did, at `19:00Z`: the hand-move opened a session on a closed card,
which ran 2.4 minutes and pushed the card Executed → Executing → Executed.

`_rescue` (`api/loops.py:420`) walks every lane whose state is `MOVING`, and
`MOVING` is set from `winner.wall` alone — the wall detector's handoff file on
the session row. Nothing in that decision asks whether there is any work left
to rescue. The handoff file is never consumed by anything (the sibling
suggestion `2026-09-04-nothing-moves-a-walled-lane.md` is that defect), so the
wall never clears; while the session row and the worktree survive, a finished
lane keeps reading `MOVING` and keeps asking for a hand.

The cost is not the noise. It is that the board spent an hour telling the owner
its most urgent-looking thing was a card that had nothing left to do, and the
one time he acted on it, it reopened a closed card to redo its own close.

## What would hold it

1. **A rescue first asks whether there is work to rescue.** A card whose
   document is archived and whose fold, trunk level and main level are all
   recorded is done; its lane ending is not an emergency, whatever the session
   row still carries. `_rescue` and the park note both skip it.
2. **A wall stops being true.** The handoff that names a lane is cleared when
   it is acted on, and expires when the lane it names is finished. A fact that
   nothing can clear will eventually be a lie that nothing can clear.
3. Between the two, a Resume ask reaches the owner only when resuming would do
   something.
4. A test: a lane whose card is folded, synced and archived yields no rescue
   and no park note, however its session row and handoff file read.

## Not this card

The seventeen repeats of a note that says "once" are a separate fault — a
guard held in one process's head, described in
`2026-09-04-a-lane-that-folded-cleanly-is-reported-as-having-died.md`. Fixing
that would make this defect quieter without making it untrue: the board would
still be asking for a hand on finished work, just once an hour instead of
seventeen times.
