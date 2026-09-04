# A lane that folded cleanly is reported as having died

**Kind:** defect
**Found by:** the owner, from the board's Idea door on 2026-09-04 (conversation
56f7b05f), reading card #196's open face on the Hello Revenue board and asking
what the lane band was saying.

## Observation

Card #196 sits in **Executed**,
archived, with `EVIDENCE HOLDS · CLOSE-LANDED`. Its lane band, in the red
`--wrong` ground, says:

> Lane ended 11 min ago: **the registry says: starting….** folded, trunk
> synced, main synced.

Every clause after the colon is false, and the three that are true are
appended to it as an afterthought.

The registry says nothing of the kind. `~/.claude-accounts/armana/jobs/9499caf8/state.json`
reads `state: done`, `detail: "Google search aperture shipped; plan, review,
walk archived"`, and its process (3949136) is still in `/proc`. The word
`starting…` is in no record on this machine. The lane did not die: it folded,
levelled the trunk and levelled main, which the same sentence goes on to say.

### The epitaph is written at birth

`runtime/reasons.py:55` is the only producer of `the registry says: …`, and it
copies `Session.detail` verbatim. `api/loops.py:340` records it for any session
whose `pid is None` — and `runtime/registry.py:113` gives `pid is None` to a job
row with no bound process **whether it has died or has not yet started**:

```python
verdict = _BACKGROUND_STATES.get(recorded, SessionState.IDLE) if pid else SessionState.ENDED
```

The two registry files date the window. The job record was created at
`19:00:18.492Z`; the process behind it started at `19:00:18.619Z`. For those
127 ms the row read *ended* with the registry's newborn word in its detail, and
a reconcile landed inside them. Which one is not recoverable — reconciles fire
on the 30 s floor, on every hook (`api/loops.py:210`), on every door, and on
every `needle` command — but that it landed there is not in doubt: `pid` has
been non-null from `19:00:18.619Z` to now, so no later moment could have
produced the string.

`api/loops.py:340` then guards the write with `if session.session_id not in
self._deaths`, so the first answer is the only answer. The session went on to
live, work, fold and sync; the board still shows the noise it made being born,
in the colour it uses for broken things.

### The same fault, said seventeen times

`_parked` (`api/loops.py:117`, `:436`) is the same idea pointed the other way:
a set that exists so the board says *"one automatic retry per run-out, so this
one is yours (Resume)"* once. Card #196's history carries it **17 times**
between `17:29:57Z` and `18:12:24Z`, identical, for one session id
(`f5c5e3c1-7409-4973-8584-6c6031b5781c`) — 13 of them inside a single life of
`needle-serve` (started `17:09Z`, restarted `18:09Z`).

Because `api/board_cli.py:67` builds its own `Loops` and reconciles, every
`needle` invocation arrives with an empty `_parked` and an empty `_deaths`,
reads the same walled lane, finds no memory of having spoken, and writes the
note again into the store every process shares. One process's head is not where
a board with many processes keeps what it knows: held there, a fact it should
state once is stated on every command, and a fact it should revise is frozen at
whatever it first guessed.

### A fold is not a death

`domain/lane.py:34` has one `ENDED`, so `board/lane.py:306` builds one sentence
for a lane that was killed and a lane that finished, leading with the cause of
death and appending the fold; `primitives.css:387` paints both in `--wrong`.
The colour language already rules that red means *"evidence is gone or two
things disagree … a lane that died"* — a lane that folded, levelled the trunk
and levelled main is none of those. (The `starting….` is the same seam: `". ".join`
adds a stop to a detail that already ended in one.)

## What would hold it

1. **A session that was never seen alive has not died.** The discriminator is
   available and honest: a row that has *had* a pid and now has none. A row
   that has never had one is either newborn or was never born — and either way
   the board has no cause of death to report, only "it has not started".
2. **The reason is read at the end, not at first sight.** Recompute when the
   session actually ends; a cache that can never be corrected will eventually
   hold a wrong answer forever, which is what it did here.
3. **Both memories move to the store.** `_deaths` and `_parked` belong where
   `needle serve` and every `needle` command can see each other's knowledge.
   The `_parked` note then lands once per run-out as it says it does.
4. **A lane that folded is reported as having finished, not as having died** —
   its own state, its own sentence leading with the fold, and the red kept for
   a lane that ended without one.
5. A test that a session with no pid *and no pid ever* yields no death reason;
   a test that a folded lane's sentence names no cause of death and carries no
   `--wrong` token; and one that the park note survives a fresh process.

## Not this card

Between `17:29:57Z` and `18:23:00Z` the board wrote those 17 rescue notes on a
card it had **already recorded as folded, synced and archived at `17:26–17:27Z`**.
`api/loops.py:420` decides to rescue from the session's wall alone and never
asks whether the card's work is still open, so a stale handoff kept a finished
lane asking for the owner's hand for 54 minutes — and the hand-move that
followed at `19:00Z` reopened the card into Executing to redo its close. That
is a second defect sharing this evidence and wants its own card.
